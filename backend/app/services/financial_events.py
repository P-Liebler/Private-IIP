from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.documents import require_data_operator
from app.core.errors import AppError
from app.models import DataSource, FinancialEventVersion, Instrument, User
from app.schemas.assistant import FinancialEventInput
from app.services.fundamentals import digest
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService


class FinancialEventService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db, self.user_id = db, user_id

    async def import_bytes(
        self, source_slug: str, data: bytes, user: User, raw: RawIngestionService | None = None
    ) -> FinancialEventVersion:
        require_data_operator(user)
        source = await SourceService(self.db).get(source_slug)
        SourceGate.require_enabled(source, "CALENDAR_EVENTS")
        raw_service = raw or RawIngestionService(self.db)
        observation = await raw_service.store(
            data=data,
            source_id=source.id,
            source_slug=source.slug,
            resource_type="reviewed_calendar_event",
            content_type="application/json",
            request_metadata={"user_id": str(self.user_id)},
        )
        original = await raw_service.get_verified(observation.id)
        try:
            request = FinancialEventInput.model_validate_json(original)
        except ValueError as error:
            raise AppError(
                422, "EVENT_FORMAT_INVALID", "Event JSON is invalid; original bytes remain archived"
            ) from error
        if request.announced_at and request.announced_at > observation.received_at:
            raise AppError(
                422, "EVENT_AVAILABILITY_INVALID", "Announcement cannot be after first observation"
            )
        if await self.db.get(Instrument, request.instrument_id) is None:
            raise AppError(422, "INSTRUMENT_NOT_FOUND", "Event instrument is unknown")
        if request.replaces_id:
            previous = await self.db.get(FinancialEventVersion, request.replaces_id)
            if (
                not previous
                or previous.user_id != self.user_id
                or previous.instrument_id != request.instrument_id
            ):
                raise AppError(404, "EVENT_NOT_FOUND", "Replaced event not found")
        payload = request.model_dump(mode="json")
        content = digest({"source": str(source.id), "payload": payload})
        existing = await self.db.scalar(
            select(FinancialEventVersion)
            .where(
                FinancialEventVersion.user_id == self.user_id,
                FinancialEventVersion.content_hash == content,
            )
            .limit(1)
        )
        if existing:
            return existing
        row = FinancialEventVersion(
            user_id=self.user_id,
            instrument_id=request.instrument_id,
            source_id=source.id,
            raw_ingestion_id=observation.id,
            replaces_id=request.replaces_id,
            event_type=request.event_type,
            event_at=request.event_at,
            known_at=request.announced_at or observation.received_at,
            observed_at=observation.received_at,
            status=request.status,
            content_hash=content,
            evidence={
                "operator_review_note": request.evidence_note,
                "raw_hash": observation.sha256,
                "source_checked_at": source.checked_at.isoformat() if source.checked_at else None,
                "data_context": "SYNTHETIC_FIXTURE_NOT_REAL_FINANCE"
                if source.slug.startswith("TEST_")
                else "OPERATOR_RECORDED_SCHEDULE",
            },
            created_at=datetime.now(UTC),
        )
        self.db.add(row)
        await self.db.commit()
        return row

    async def available(
        self, cutoff: datetime, instrument_id: UUID | None = None
    ) -> list[FinancialEventVersion]:
        statement = select(FinancialEventVersion).where(
            FinancialEventVersion.user_id == self.user_id,
            FinancialEventVersion.known_at <= cutoff,
            FinancialEventVersion.observed_at <= cutoff,
            FinancialEventVersion.created_at <= cutoff,
        )
        if instrument_id:
            statement = statement.where(FinancialEventVersion.instrument_id == instrument_id)
        rows = list(
            (
                await self.db.scalars(
                    statement.order_by(FinancialEventVersion.created_at.desc()).limit(1000)
                )
            ).all()
        )
        replaced = {r.replaces_id for r in rows if r.replaces_id}
        available = []
        for row in rows:
            if row.id in replaced:
                continue
            source = await self.db.get(DataSource, row.source_id)
            try:
                if not source:
                    continue
                SourceGate.require_enabled(source, "CALENDAR_EVENTS")
                await RawIngestionService(self.db).get_verified(row.raw_ingestion_id)
            except AppError:
                continue
            available.append(row)
        return available
