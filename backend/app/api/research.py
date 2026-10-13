from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_user
from app.core.errors import AppError
from app.db.session import get_session
from app.models import (
    AnalystEstimate,
    DataQuarantine,
    DataSource,
    Filing,
    FundamentalFact,
    Instrument,
    NewsArticle,
    PriceDaily,
    PriceDailyVersion,
    RawIngestion,
    ResearchMetric,
    ResearchSnapshot,
    Watchlist,
    WatchlistItem,
)
from app.providers.sec import SecCollector
from app.schemas.research import (
    EstimateInput,
    ImportCommit,
    WatchlistInput,
    WatchlistItemInput,
    WatchlistUpdate,
)
from app.services.analyst_estimates import EstimateService
from app.services.auth import AuthContext
from app.services.fundamentals import FundamentalService
from app.services.market_queries import pit_cutoff
from app.services.news import NewsInput, NewsService
from app.services.raw_ingestion import RawIngestionService
from app.services.research import ResearchService
from app.services.sources import SourceGate, SourceService

router = APIRouter(prefix="/api/v1", tags=["research"])
DB = Annotated[AsyncSession, Depends(get_session)]
Auth = Annotated[AuthContext, Depends(require_user)]


def view(row: Any) -> dict[str, Any]:
    return {
        column.name: str(value) if isinstance(value, Decimal) else value
        for column in row.__table__.columns
        for value in [getattr(row, column.name)]
    }


@router.get("/instruments/{instrument_id}/financials")
async def financials(
    instrument_id: UUID,
    db: DB,
    _context: Auth,
    as_of: datetime | None = None,
    period: Literal["ANNUAL", "QUARTER", "TTM", "ALL"] = "ALL",
) -> dict[str, Any]:
    result = await ResearchService(db).calculate(instrument_id, as_of)
    return {
        "status": result["status"],
        "as_of": result["as_of"],
        "facts": result["facts"]
        if period == "ALL"
        else [f for f in result["facts"] if f["period_type"] in {period, "INSTANT"}],
        "ttm": result["ttm"],
        "history_contract": result["history_contract"],
    }


@router.get("/instruments/{instrument_id}/metrics")
async def metrics(
    instrument_id: UUID,
    db: DB,
    _context: Auth,
    as_of: datetime | None = None,
    period: Literal["ANNUAL", "QUARTER"] = "ANNUAL",
) -> dict[str, Any]:
    result = await ResearchService(db).calculate(instrument_id, as_of, period)
    return {"as_of": result["as_of"], "metrics": result["metrics"]}


@router.get("/instruments/{instrument_id}/financials/versions")
async def fact_versions(
    instrument_id: UUID,
    db: DB,
    _context: Auth,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[dict[str, Any]]:
    return [
        view(row)
        for row in (
            await db.scalars(
                select(FundamentalFact)
                .where(FundamentalFact.instrument_id == instrument_id)
                .order_by(FundamentalFact.observed_at.desc(), FundamentalFact.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
    ]


@router.get("/instruments/{instrument_id}/valuation")
async def valuations(
    instrument_id: UUID, db: DB, _context: Auth, as_of: datetime | None = None
) -> dict[str, Any]:
    result = await ResearchService(db).calculate(instrument_id, as_of)
    return {"as_of": result["as_of"], "valuation": result["valuation"]}


@router.get("/research/instruments/{instrument_id}")
async def detail(
    instrument_id: UUID, db: DB, _context: Auth, as_of: datetime | None = None
) -> dict[str, Any]:
    return await ResearchService(db).calculate(instrument_id, as_of)


@router.get("/research/instruments/{instrument_id}/scores")
async def scores(
    instrument_id: UUID, db: DB, _context: Auth, as_of: datetime | None = None
) -> dict[str, Any]:
    result = await ResearchService(db).calculate(instrument_id, as_of)
    return {"as_of": result["as_of"], "scores": result["scores"]}


@router.post("/research/instruments/{instrument_id}/refresh")
async def refresh(instrument_id: UUID, db: DB, _context: Auth) -> dict[str, Any]:
    return view(await ResearchService(db).materialize(instrument_id))


@router.get("/research/instruments")
async def screener(
    db: DB,
    _context: Auth,
    q: str = "",
    country: str | None = None,
    exchange: str | None = None,
    sector: str | None = None,
    industry: str | None = None,
    asset_type: str | None = None,
    metric: str | None = None,
    minimum: Decimal | None = None,
    maximum: Decimal | None = None,
    sort: Literal["name", "ticker", "metric"] = "name",
    descending: bool = False,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    cutoff = pit_cutoff(as_of)
    ranked = (
        select(
            ResearchSnapshot.id,
            ResearchSnapshot.instrument_id,
            func.row_number()
            .over(
                partition_by=ResearchSnapshot.instrument_id,
                order_by=(ResearchSnapshot.as_of.desc(), ResearchSnapshot.id.desc()),
            )
            .label("rank"),
        )
        .where(ResearchSnapshot.as_of <= cutoff)
        .subquery()
    )
    latest = select(ranked.c.id, ranked.c.instrument_id).where(ranked.c.rank == 1).subquery()
    statement = (
        select(Instrument, ResearchSnapshot.result, ResearchSnapshot.as_of)
        .outerjoin(latest, latest.c.instrument_id == Instrument.id)
        .outerjoin(ResearchSnapshot, ResearchSnapshot.id == latest.c.id)
        .where(Instrument.active.is_(True))
    )
    if q:
        statement = statement.where(
            Instrument.name.ilike(f"%{q[:100]}%") | Instrument.ticker.ilike(f"%{q[:100]}%")
        )
    for column, value in [
        (Instrument.country, country),
        (Instrument.exchange, exchange),
        (Instrument.sector, sector),
        (Instrument.industry, industry),
        (Instrument.asset_type, asset_type),
    ]:
        if value:
            statement = statement.where(column == value)
    sort_column: Any = Instrument.name if sort == "name" else Instrument.ticker
    if metric:
        statement = statement.join(
            ResearchMetric,
            (ResearchMetric.snapshot_id == latest.c.id)
            & (ResearchMetric.metric == metric)
            & (ResearchMetric.status == "AVAILABLE"),
        )
        if minimum is not None:
            statement = statement.where(ResearchMetric.value >= minimum)
        if maximum is not None:
            statement = statement.where(ResearchMetric.value <= maximum)
        if sort == "metric":
            sort_column = ResearchMetric.value
    elif sort == "metric" or minimum is not None or maximum is not None:
        raise AppError(422, "SCREENER_METRIC_REQUIRED", "Metric required for numeric filter/sort")
    rows = (
        await db.execute(
            statement.order_by(
                sort_column.desc().nulls_last() if descending else sort_column.asc().nulls_last(),
                Instrument.id,
            )
            .offset(offset)
            .limit(limit)
        )
    ).all()
    supported = list(
        (
            await db.scalars(
                select(ResearchMetric.metric)
                .where(
                    ResearchMetric.status == "AVAILABLE",
                    ResearchMetric.snapshot_id.in_(select(latest.c.id)),
                )
                .distinct()
                .order_by(ResearchMetric.metric)
            )
        ).all()
    )
    return {
        "items": [
            {
                "instrument": view(instrument),
                "research": result,
                "as_of": observed,
                "status": result["status"] if result else "INSUFFICIENT_DATA",
            }
            for instrument, result, observed in rows
        ],
        "offset": offset,
        "limit": limit,
        "available_filters": supported,
        "as_of": cutoff,
    }


@router.post("/research/imports/upload")
async def upload(request: Request, db: DB, context: Auth) -> dict[str, object]:
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 5_000_000:
            raise AppError(413, "CSV_SIZE_INVALID", "Upload exceeds 5 MB")
    return await FundamentalService(db).upload(
        bytes(data), request.headers.get("X-Filename", "fundamentals.csv"), context.user.id
    )


class PreviewRequest(BaseModel):
    raw_ingestion_id: UUID
    mapping: dict[str, str] = Field(default_factory=dict)


@router.post("/research/imports/preview")
async def preview(payload: PreviewRequest, db: DB, context: Auth) -> dict[str, object]:
    return await FundamentalService(db).preview(
        payload.raw_ingestion_id, payload.mapping, context.user.id
    )


@router.post("/research/imports/commit")
async def commit(payload: ImportCommit, db: DB, context: Auth) -> dict[str, int]:
    service = FundamentalService(db)
    result = await service.commit(payload.raw_ingestion_id, payload.mapping, context.user.id)
    _, inputs, _, _ = await service.parse_csv(
        payload.raw_ingestion_id, payload.mapping, context.user.id
    )
    for instrument_id in sorted({f.instrument_id for f in inputs}, key=str):
        await ResearchService(db).materialize(instrument_id)
    return result


class SecRequest(BaseModel):
    instrument_id: UUID
    cik: str = Field(pattern=r"^\d{1,10}$")


@router.post("/research/collect/sec")
async def collect_sec(payload: SecRequest, db: DB, _context: Auth) -> dict[str, object]:
    result = await SecCollector(db).collect(payload.instrument_id, payload.cik)
    await ResearchService(db).materialize(payload.instrument_id)
    return result


@router.post("/research/filings/{filing_id}/download")
async def download_filing(filing_id: UUID, db: DB, _context: Auth) -> dict[str, Any]:
    return view(await SecCollector(db).download_filing(filing_id))


@router.get("/instruments/{instrument_id}/filings")
async def filing_history(
    instrument_id: UUID, db: DB, _context: Auth, as_of: datetime | None = None
) -> list[dict[str, Any]]:
    cutoff = pit_cutoff(as_of)
    return [
        view(row)
        for row in (
            await db.scalars(
                select(Filing)
                .where(
                    Filing.instrument_id == instrument_id,
                    Filing.known_at <= cutoff,
                    Filing.observed_at <= cutoff,
                )
                .order_by(Filing.known_at.desc())
                .limit(100)
            )
        ).all()
    ]


async def owned_watchlist(
    db: AsyncSession, identifier: UUID, user_id: UUID, lock: bool = False
) -> Watchlist:
    row = await db.get(Watchlist, identifier, with_for_update=lock)
    if row is None or row.user_id != user_id:
        raise AppError(404, "WATCHLIST_NOT_FOUND", "Watchlist not found")
    return row


@router.get("/watchlists")
async def watchlists(db: DB, context: Auth) -> list[dict[str, Any]]:
    return [
        view(row)
        for row in (
            await db.scalars(
                select(Watchlist)
                .where(Watchlist.user_id == context.user.id, Watchlist.archived.is_(False))
                .order_by(Watchlist.name)
            )
        ).all()
    ]


@router.post("/watchlists", status_code=201)
async def create_watchlist(payload: WatchlistInput, db: DB, context: Auth) -> dict[str, Any]:
    row = Watchlist(user_id=context.user.id, **payload.model_dump())
    db.add(row)
    await db.commit()
    return view(row)


@router.patch("/watchlists/{identifier}")
async def update_watchlist(
    identifier: UUID, payload: WatchlistUpdate, db: DB, context: Auth
) -> dict[str, Any]:
    row = await owned_watchlist(db, identifier, context.user.id, True)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key in {"name", "archived"} and value is None:
            raise AppError(422, "WATCHLIST_INVALID", "Name/archive state cannot be null")
        setattr(row, key, value)
    await db.commit()
    return view(row)


@router.get("/watchlists/{identifier}/items")
async def watchlist_items(identifier: UUID, db: DB, context: Auth) -> list[dict[str, Any]]:
    await owned_watchlist(db, identifier, context.user.id)
    rows = (
        await db.execute(
            select(WatchlistItem, Instrument)
            .join(Instrument, WatchlistItem.instrument_id == Instrument.id)
            .where(WatchlistItem.watchlist_id == identifier)
        )
    ).all()
    ids = [instrument.id for _, instrument in rows]
    snapshots = (
        (
            await db.scalars(
                select(ResearchSnapshot)
                .where(ResearchSnapshot.instrument_id.in_(ids))
                .order_by(ResearchSnapshot.as_of.desc())
            )
        ).all()
        if ids
        else []
    )
    latest: dict[UUID, ResearchSnapshot] = {}
    for snapshot in snapshots:
        latest.setdefault(snapshot.instrument_id, snapshot)
    cutoff = pit_cutoff(None)
    prices = (
        list(
            (
                await db.scalars(
                    select(PriceDailyVersion)
                    .join(PriceDaily, PriceDaily.version_id == PriceDailyVersion.id)
                    .where(
                        PriceDaily.instrument_id.in_(ids),
                        PriceDaily.trading_date <= cutoff.date(),
                        PriceDailyVersion.known_at <= cutoff,
                    )
                    .order_by(
                        PriceDailyVersion.instrument_id, PriceDailyVersion.trading_date.desc()
                    )
                    .distinct(PriceDailyVersion.instrument_id)
                )
            ).all()
        )
        if ids
        else []
    )
    price_map = {
        p.instrument_id: {
            "close": str(p.close),
            "date": p.trading_date,
            "currency": p.currency,
            "quality_label": p.quality_label,
            "source_id": str(p.source_id),
            "age_days": (cutoff.date() - p.trading_date).days,
            "freshness": "STALE" if (cutoff.date() - p.trading_date).days > 7 else "CURRENT",
        }
        for p in prices
    }
    return [
        {
            **view(item),
            "instrument": view(instrument),
            "research": latest[instrument.id].result if instrument.id in latest else None,
            "price": price_map.get(instrument.id),
        }
        for item, instrument in rows
    ]


@router.put("/watchlists/{identifier}/items")
async def add_item(
    identifier: UUID, payload: WatchlistItemInput, db: DB, context: Auth
) -> dict[str, Any]:
    row = await owned_watchlist(db, identifier, context.user.id, True)
    if row.archived or await db.get(Instrument, payload.instrument_id) is None:
        raise AppError(422, "WATCHLIST_INVALID", "Archived list or unknown instrument")
    item = (
        await db.scalars(
            select(WatchlistItem).where(
                WatchlistItem.watchlist_id == identifier,
                WatchlistItem.instrument_id == payload.instrument_id,
            )
        )
    ).one_or_none()
    if item is None:
        item = WatchlistItem(watchlist_id=identifier, **payload.model_dump())
        db.add(item)
    else:
        item.notes, item.tags = payload.notes, payload.tags
    await db.commit()
    return view(item)


@router.delete("/watchlists/{identifier}/items/{instrument_id}")
async def remove_item(
    identifier: UUID, instrument_id: UUID, db: DB, context: Auth
) -> dict[str, str]:
    await owned_watchlist(db, identifier, context.user.id, True)
    item = (
        await db.scalars(
            select(WatchlistItem).where(
                WatchlistItem.watchlist_id == identifier,
                WatchlistItem.instrument_id == instrument_id,
            )
        )
    ).one_or_none()
    if item:
        await db.delete(item)
        await db.commit()
    return {"status": "REMOVED"}


@router.get("/news")
async def news(
    db: DB,
    _context: Auth,
    instrument_id: UUID | None = None,
    source_id: UUID | None = None,
    as_of: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[dict[str, Any]]:
    return await NewsService(db).list(
        instrument_id=instrument_id,
        source_id=source_id,
        as_of=as_of,
        start=start,
        end=end,
        offset=offset,
        limit=limit,
    )


@router.get("/instruments/{instrument_id}/news")
async def instrument_news(
    instrument_id: UUID, db: DB, _context: Auth, as_of: datetime | None = None
) -> list[dict[str, Any]]:
    return await NewsService(db).list(instrument_id=instrument_id, as_of=as_of)


@router.get("/instruments/{instrument_id}/estimates")
async def estimates(
    instrument_id: UUID, db: DB, _context: Auth, as_of: datetime | None = None
) -> list[dict[str, Any]]:
    return [view(row) for row in await EstimateService(db).history(instrument_id, as_of)]


@router.post("/research/imports/{kind}")
async def manual_json(
    kind: Literal["news", "estimates"], request: Request, db: DB, context: Auth
) -> dict[str, int]:
    source = await SourceService(db).get("MANUAL_RESEARCH")
    SourceGate.require_enabled(source, kind)
    data = await request.body()
    if len(data) > 1_000_000:
        raise AppError(413, "RESEARCH_TOO_LARGE", "Research upload exceeds 1 MB")
    raw = await RawIngestionService(db).store(
        data=data,
        source_id=source.id,
        source_slug=source.slug,
        resource_type=f"manual_{kind}",
        content_type="application/json",
        request_metadata={"user_id": str(context.user.id)},
    )
    try:
        values = json.loads(data)
        if not isinstance(values, list) or len(values) > 1000:
            raise ValueError("At most 1000 records")
        if kind == "news":
            return await NewsService(db).persist(
                [NewsInput.model_validate(v) for v in values],
                raw,
                "news_excerpts" in source.allowed_uses,
            )
        return {
            "inserted": await EstimateService(db).persist(
                [EstimateInput.model_validate(v) for v in values], raw
            )
        }
    except (ValueError, TypeError):
        await db.rollback()
        raise AppError(422, "RESEARCH_IMPORT_INVALID", "Invalid research import") from None


@router.get("/data-quality/research")
async def quality(db: DB, _context: Auth) -> dict[str, Any]:
    return {
        "last_filing_ingestion": await db.scalar(select(func.max(Filing.observed_at))),
        "failed_ingestions": await db.scalar(
            select(func.count())
            .select_from(RawIngestion)
            .where(
                RawIngestion.resource_type.in_(
                    ["sec_response", "fundamental_csv", "news_rss", "company_ir"]
                ),
                RawIngestion.status == "FAILED",
            )
        ),
        "quarantined_facts": await db.scalar(
            select(func.count())
            .select_from(FundamentalFact)
            .where(FundamentalFact.validation_status == "REJECTED")
        ),
        "rejected_import_rows": await db.scalar(
            select(func.count())
            .select_from(DataQuarantine)
            .where(DataQuarantine.data_type == "fundamental")
        ),
        "restatements": await db.scalar(
            select(func.count())
            .select_from(FundamentalFact)
            .where(FundamentalFact.quality_components["warnings"].contains(["RESTATEMENT"]))
        ),
        "missing_fundamentals": await db.scalar(
            select(func.count())
            .select_from(Instrument)
            .where(
                ~select(FundamentalFact.id)
                .where(
                    FundamentalFact.instrument_id == Instrument.id,
                    FundamentalFact.validation_status != "REJECTED",
                )
                .exists()
            )
        ),
        "last_fact_period": await db.scalar(select(func.max(FundamentalFact.period_end))),
        "news_articles": await db.scalar(select(func.count()).select_from(NewsArticle)),
        "news_duplicates": await db.scalar(
            select(func.count())
            .select_from(NewsArticle)
            .where(NewsArticle.duplicate_of_id.is_not(None))
        ),
        "sources": [
            view(s)
            for s in (
                await db.scalars(
                    select(DataSource).where(
                        DataSource.slug.in_(
                            ["SEC_EDGAR", "COMPANY_IR", "NEWS_RSS", "MANUAL_RESEARCH"]
                        )
                    )
                )
            ).all()
        ],
        "estimate_count": await db.scalar(select(func.count()).select_from(AnalystEstimate)),
    }
