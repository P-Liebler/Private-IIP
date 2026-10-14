from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from difflib import SequenceMatcher
from typing import Any, Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import NewsArticle, NewsInstrument, NewsMappingVersion, RawIngestion
from app.services.instruments import InstrumentService
from app.services.market_queries import pit_cutoff


class NewsSentimentProvider(Protocol):
    def analyze(self, title: str, language: str) -> dict[str, object] | None: ...


class UnavailableSentiment:
    def analyze(self, title: str, language: str) -> None:
        return None


class NewsInput(BaseModel):
    title: str = Field(min_length=1, max_length=1000)
    source_url: str = Field(max_length=2000)
    published_at: AwareDatetime | None = None
    language: str = Field(default="und", max_length=12)
    summary: str | None = Field(default=None, max_length=500)
    identifiers: list[str] = Field(default_factory=list, max_length=20)


def normalized_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"https", "http"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Invalid public article URL")
    query = sorted(
        (k, v)
        for k, v in parse_qsl(parsed.query)
        if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}
    )
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            urlencode(query),
            "",
        )
    )


def normalized_title(title: str) -> str:
    return " ".join(re.findall(r"\w+", title.casefold()))


def sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class NewsService:
    def __init__(self, db: AsyncSession, sentiment: NewsSentimentProvider | None = None) -> None:
        self.db, self.sentiment = db, sentiment or UnavailableSentiment()

    async def persist(
        self, items: list[NewsInput], raw: RawIngestion, allow_excerpt: bool = False
    ) -> dict[str, int]:
        if raw.status != "STORED":
            raise AppError(409, "RAW_NOT_AVAILABLE", "News requires stored original bytes")
        inserted, duplicates = 0, 0
        for index, item in enumerate(items):
            row_key = sha(str(index))
            if (
                await self.db.scalars(
                    select(NewsArticle).where(
                        NewsArticle.raw_ingestion_id == raw.id, NewsArticle.row_key == row_key
                    )
                )
            ).one_or_none():
                continue
            url = normalized_url(item.source_url)
            title = normalized_title(item.title)
            url_hash, content_hash = sha(url), sha(title)
            candidates = (
                await self.db.scalars(
                    select(NewsArticle)
                    .where(
                        NewsArticle.duplicate_of_id.is_(None),
                        or_(
                            NewsArticle.url_hash == url_hash,
                            NewsArticle.content_hash == content_hash,
                            NewsArticle.observed_at
                            >= raw.received_at.replace(hour=0, minute=0, second=0, microsecond=0),
                        ),
                    )
                    .order_by(NewsArticle.observed_at)
                    .limit(1000)
                )
            ).all()
            duplicate = next(
                (
                    n
                    for n in candidates
                    if n.url_hash == url_hash
                    or n.content_hash == content_hash
                    or (
                        len(title) >= 25
                        and SequenceMatcher(None, normalized_title(n.title), title).ratio() >= 0.92
                    )
                ),
                None,
            )
            if item.published_at and item.published_at > raw.received_at:
                raise AppError(422, "NEWS_FUTURE_PUBLICATION", "Publication after observation")
            row = NewsArticle(
                title=item.title,
                source_url=url,
                summary=item.summary if allow_excerpt else None,
                language=item.language,
                row_key=row_key,
                url_hash=url_hash,
                content_hash=content_hash,
                duplicate_of_id=duplicate.id if duplicate else None,
                sentiment=self.sentiment.analyze(item.title, item.language),
                published_at=item.published_at,
                discovered_at=raw.received_at,
                source_id=raw.source_id,
                raw_ingestion_id=raw.id,
                known_at=item.published_at or raw.received_at,
                observed_at=raw.received_at,
                retrieved_at=raw.received_at,
            )
            self.db.add(row)
            await self.db.flush()
            linked: dict[UUID, bool] = {}
            for identifier in set(item.identifiers):
                hits = await InstrumentService(self.db).search(identifier)
                exact = [
                    h
                    for h in hits
                    if h.match_type in {"EXACT_TICKER", "EXACT_IDENTIFIER", "EXACT_NAME"}
                ]
                for hit in exact:
                    # Company-name matches stay candidates without external context evidence.
                    confirmed = (
                        len(exact) == 1
                        and hit.match_type != "EXACT_NAME"
                        and hit.resolution_status == "UNIQUE"
                        and hit.current
                    )
                    linked[hit.instrument.id] = linked.get(hit.instrument.id, False) or confirmed
            for instrument_id, confirmed in linked.items():
                self.db.add(
                    NewsMappingVersion(
                        article_id=row.id,
                        instrument_id=instrument_id,
                        mapping_status="CONFIRMED" if confirmed else "CANDIDATE",
                        observed_at=datetime.now(UTC),
                    )
                )
                self.db.add(
                    NewsInstrument(
                        article_id=row.id,
                        instrument_id=instrument_id,
                        relevance_score="1" if confirmed else "0.5",
                        entity_confidence="1" if confirmed else "0.5",
                        mapping_status="CONFIRMED" if confirmed else "CANDIDATE",
                    )
                )
            inserted += 1
            duplicates += duplicate is not None
        await self.db.commit()
        return {"inserted": inserted, "duplicates": duplicates}

    async def list(
        self,
        *,
        as_of: datetime | None = None,
        instrument_id: UUID | None = None,
        source_id: UUID | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        cutoff = pit_cutoff(as_of)
        query = select(NewsArticle).where(
            NewsArticle.known_at <= cutoff, NewsArticle.observed_at <= cutoff
        )
        if instrument_id:
            query = query.where(
                NewsArticle.id.in_(
                    select(NewsInstrument.article_id).where(
                        NewsInstrument.instrument_id == instrument_id,
                        NewsInstrument.mapping_status == "CONFIRMED",
                    )
                )
            )
        if source_id:
            query = query.where(NewsArticle.source_id == source_id)
        if start:
            query = query.where(NewsArticle.known_at >= pit_cutoff(start))
        if end:
            query = query.where(NewsArticle.known_at <= pit_cutoff(end))
        rows = (
            await self.db.scalars(
                query.order_by(NewsArticle.known_at.desc(), NewsArticle.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        links = (
            (
                await self.db.scalars(
                    select(NewsInstrument).where(
                        NewsInstrument.article_id.in_([n.id for n in rows])
                    )
                )
            ).all()
            if rows
            else []
        )
        return [
            {
                **{
                    key: getattr(n, key)
                    for key in (
                        "id",
                        "title",
                        "summary",
                        "source_url",
                        "source_id",
                        "published_at",
                        "discovered_at",
                        "retrieved_at",
                        "raw_ingestion_id",
                        "language",
                        "sentiment",
                        "duplicate_of_id",
                    )
                },
                "associations": [
                    {
                        "instrument_id": link.instrument_id,
                        "mapping_status": link.mapping_status,
                        "entity_confidence": link.entity_confidence,
                    }
                    for link in links
                    if link.article_id == n.id
                ],
            }
            for n in rows
        ]
