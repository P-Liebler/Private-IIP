from decimal import Decimal
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ActionCoverageReview,
    CollectorJob,
    CorporateActionVersion,
    DataCoverageSnapshot,
    DataSource,
    FundamentalFact,
    FxRateVersion,
    MacroObservation,
    PriceDailyVersion,
    ProviderSyncState,
    RawIngestion,
    SourceReviewEvidence,
)
from app.services.fundamentals import digest


async def collection_checkpoint(db: AsyncSession) -> dict[str, Any]:
    payload = {}
    for model in (
        DataSource,
        SourceReviewEvidence,
        CollectorJob,
        ProviderSyncState,
        DataCoverageSnapshot,
        PriceDailyVersion,
        FxRateVersion,
        FundamentalFact,
        MacroObservation,
        CorporateActionVersion,
        ActionCoverageReview,
    ):
        rows = (await db.scalars(select(model))).all()
        values = sorted(
            (
                jsonable_encoder(
                    {c.name: getattr(r, c.name) for c in model.__table__.columns},
                    custom_encoder={Decimal: str},
                )
                for r in rows
            ),
            key=digest,
        )
        payload[model.__tablename__] = {"count": len(values), "hash": digest(values)}
    return {"collections_history_hash": digest(payload), "tables": payload}


async def collection_metrics(db: AsyncSession) -> list[str]:
    lines = []
    rows = (
        await db.execute(
            select(
                CollectorJob.status,
                func.count(),
                func.sum(
                    func.extract("epoch", CollectorJob.completed_at - CollectorJob.started_at)
                ),
            ).group_by(CollectorJob.status)
        )
    ).all()
    for status in ("QUEUED", "RUNNING", "SUCCESS", "PARTIAL", "FAILED", "SKIPPED", "CANCELLED"):
        values = next((r for r in rows if r[0] == status), None)
        lines.append(
            f'private_iip_collector_jobs{{status="{status}"}} {values[1] if values else 0}'
        )
        lines.append(
            f'private_iip_collector_duration_seconds_sum{{status="{status}"}} '
            f"{values[2] or 0 if values else 0}"
        )
    for slug in ("SEC_EDGAR", "ECB", "SNB", "OPENFIGI", "COMPANY_IR", "NEWS_RSS", "ALPHAVANTAGE"):
        source = (await db.scalars(select(DataSource).where(DataSource.slug == slug))).first()
        if source:
            requests, limited = (
                await db.execute(
                    select(
                        func.count(RawIngestion.id),
                        func.count(RawIngestion.id).filter(RawIngestion.http_status == 429),
                    ).where(
                        RawIngestion.source_id == source.id, RawIngestion.requested_at.is_not(None)
                    )
                )
            ).one()
            lines.append(f'private_iip_provider_requests_total{{provider="{slug}"}} {requests}')
            lines.append(f'private_iip_provider_rate_limits_total{{provider="{slug}"}} {limited}')
            lines.append(
                f'private_iip_provider_failures_total{{provider="{slug}"}} {source.failure_count}'
            )
            lines.append(f'private_iip_provider_enabled{{provider="{slug}"}} {int(source.enabled)}')
    return lines
