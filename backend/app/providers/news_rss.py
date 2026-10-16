from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.providers.company_ir import validate_public_endpoint
from app.providers.http import fetch_response
from app.services.news import NewsInput, NewsService
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService


def parse_rss(data: bytes) -> list[NewsInput]:
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("DTD/entities prohibited")
    root = ET.fromstring(data)
    if root.tag != "rss":
        raise ValueError("Only explicit RSS 2.0 supported")
    rows: list[NewsInput] = []
    for node in root.findall("./channel/item")[:1000]:
        title, url = node.findtext("title"), node.findtext("link")
        if not title or not url:
            raise ValueError("RSS item requires headline/link")
        published = (
            parsedate_to_datetime(node.findtext("pubDate", ""))
            if node.findtext("pubDate")
            else None
        )
        rows.append(
            NewsInput(
                title=title,
                source_url=url,
                published_at=published,
                language=root.findtext("./channel/language", "und"),
            )
        )
    return rows


class RssCollector:
    def __init__(
        self,
        db: AsyncSession,
        raw: RawIngestionService | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.db, self.raw, self.client = db, raw or RawIngestionService(db), client

    async def collect(
        self, url: str, approved_host: str, source_slug: str = "NEWS_RSS"
    ) -> dict[str, int]:
        source = await SourceService(self.db).get(source_slug)
        SourceGate.require_enabled(source, "news_feed_archive")
        SourceGate.require_enabled(source, "news")
        if f"host={approved_host}" not in (source.scope or "").split():
            raise AppError(403, "SOURCE_SCOPE_MISMATCH", "RSS host not approved")
        await validate_public_endpoint(url, approved_host)
        raw = await fetch_response(
            self.db,
            self.raw,
            source,
            use="news_feed_archive",
            url=url,
            allowed_host=approved_host,
            resource="news_rss",
            client=self.client,
            content_types=("application/rss+xml", "application/xml", "text/xml"),
        )
        try:
            items = parse_rss(await self.raw.get_verified(raw.id))
            source.last_success = datetime.now(UTC)
            return await NewsService(self.db).persist(items, raw)
        except (ValueError, ET.ParseError):
            await self.db.rollback()
            raise AppError(422, "NEWS_PARSE_FAILED", "Invalid RSS response") from None
