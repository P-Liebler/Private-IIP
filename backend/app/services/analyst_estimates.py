from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import AnalystEstimate, Instrument, RawIngestion
from app.schemas.research import EstimateInput
from app.services.fundamentals import digest
from app.services.market_queries import pit_cutoff


class EstimateService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def persist(self, items: list[EstimateInput], raw: RawIngestion) -> int:
        if raw.status != "STORED":
            raise AppError(409, "RAW_NOT_AVAILABLE", "Estimate requires raw evidence")
        inserted = 0
        for item in items:
            if await self.db.get(Instrument, item.instrument_id, with_for_update=True) is None:
                raise AppError(422, "INSTRUMENT_NOT_FOUND", "Unknown estimate instrument")
            key = digest((item.instrument_id, item.estimate_type, item.target_period))
            previous = (
                await self.db.scalars(
                    select(AnalystEstimate)
                    .where(
                        AnalystEstimate.instrument_id == item.instrument_id,
                        AnalystEstimate.estimate_type == item.estimate_type,
                        AnalystEstimate.target_period == item.target_period,
                        AnalystEstimate.source_id == raw.source_id,
                    )
                    .order_by(AnalystEstimate.observed_at.desc(), AnalystEstimate.id.desc())
                    .limit(1)
                )
            ).one_or_none()
            if previous and previous.raw_ingestion_id == raw.id:
                continue
            self.db.add(
                AnalystEstimate(
                    **item.model_dump(),
                    row_key=key,
                    source_id=raw.source_id,
                    raw_ingestion_id=raw.id,
                    known_at=raw.received_at,
                    observed_at=raw.received_at,
                    retrieved_at=raw.received_at,
                    quality={
                        "schema_valid": True,
                        "history": "FIRST_LOCAL_OBSERVATION",
                        "single_source": True,
                    },
                    replaces_version_id=previous.id if previous else None,
                    rule_version="estimate-v1",
                )
            )
            await self.db.flush()
            inserted += 1
        await self.db.commit()
        return inserted

    async def history(
        self, instrument_id: UUID, as_of: datetime | None = None
    ) -> list[AnalystEstimate]:
        cutoff = pit_cutoff(as_of)
        return list(
            (
                await self.db.scalars(
                    select(AnalystEstimate)
                    .where(
                        AnalystEstimate.instrument_id == instrument_id,
                        AnalystEstimate.observed_at <= cutoff,
                        AnalystEstimate.known_at <= cutoff,
                    )
                    .order_by(AnalystEstimate.observed_at.desc())
                )
            ).all()
        )
