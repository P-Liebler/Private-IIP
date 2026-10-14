import csv
import hashlib
from io import StringIO
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Instrument, RawIngestion, UniverseDefinition, UniverseMembershipVersion
from app.schemas.pit import MembershipInput
from app.services.fundamentals import digest
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService


class UniverseService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def owned(
        self, universe_id: UUID, user_id: UUID, lock: bool = False
    ) -> UniverseDefinition:
        row = await self.db.get(UniverseDefinition, universe_id, with_for_update=lock)
        if row is None or row.user_id != user_id:
            raise AppError(404, "UNIVERSE_NOT_FOUND", "Universe not found")
        return row

    async def upload(self, universe_id: UUID, user_id: UUID, data: bytes) -> RawIngestion:
        await self.owned(universe_id, user_id)
        source = await SourceService(self.db).get("MANUAL_PIT")
        SourceGate.require_enabled(source, "universe_membership")
        return await RawIngestionService(self.db).store(
            data=data,
            source_id=source.id,
            source_slug=source.slug,
            resource_type="universe_membership",
            content_type="text/csv",
            request_metadata={"user_id": str(user_id), "identifier_value": str(universe_id)},
        )

    async def preview(self, universe_id: UUID, user_id: UUID, raw_id: UUID) -> dict[str, Any]:
        await self.owned(universe_id, user_id)
        raw = await self.db.get(RawIngestion, raw_id)
        if (
            raw is None
            or raw.status != "STORED"
            or raw.resource_type != "universe_membership"
            or raw.request_metadata.get("user_id") != str(user_id)
            or raw.request_metadata.get("identifier_value") != str(universe_id)
        ):
            raise AppError(404, "RAW_NOT_FOUND", "Owned universe upload required")
        data = await RawIngestionService(self.db).get_verified(raw.id)
        result = []
        errors = []
        keys = set()
        try:
            for line, row in enumerate(csv.DictReader(StringIO(data.decode("utf-8-sig"))), 2):
                if line > 1002:
                    raise ValueError("Maximum 1000 membership rows")
                item = MembershipInput.model_validate({k: v for k, v in row.items() if v})
                key = (item.instrument_id, item.valid_from)
                if key in keys:
                    raise ValueError("Duplicate membership interval")
                keys.add(key)
                if await self.db.get(Instrument, item.instrument_id) is None:
                    raise ValueError("Unknown internal instrument ID")
                if item.known_at and item.known_at > raw.received_at:
                    raise ValueError("Future assertion")
                result.append(item.model_dump(mode="json"))
        except (ValueError, UnicodeError, ValidationError) as error:
            errors.append(str(error))
        return {
            "raw_id": str(raw_id),
            "sha256": hashlib.sha256(data).hexdigest(),
            "rows": result,
            "errors": errors,
            "availability": "USER_ASSERTED / LOCAL_FIRST_OBSERVATION",
            "mapping": "Explicit stable internal UUIDs only",
        }

    async def commit(self, universe_id: UUID, user_id: UUID, raw_id: UUID) -> dict[str, int]:
        await self.owned(universe_id, user_id, True)
        source = await SourceService(self.db).get("MANUAL_PIT")
        SourceGate.require_enabled(source, "universe_membership")
        preview = await self.preview(universe_id, user_id, raw_id)
        if preview["errors"] or not preview["rows"]:
            raise AppError(
                422, "MEMBERSHIP_INVALID", "Preview contains invalid or empty membership"
            )
        raw = await self.db.get(RawIngestion, raw_id)
        assert raw
        if raw.source_id != source.id:
            raise AppError(403, "SOURCE_NOT_APPROVED", "Source mismatch")
        count = 0
        for value in preview["rows"]:
            item = MembershipInput.model_validate(value)
            key = digest((item.instrument_id, item.valid_from))
            existing = (
                await self.db.scalars(
                    select(UniverseMembershipVersion).where(
                        UniverseMembershipVersion.universe_id == universe_id,
                        UniverseMembershipVersion.raw_ingestion_id == raw_id,
                        UniverseMembershipVersion.row_key == key,
                    )
                )
            ).first()
            if existing:
                continue
            previous = (
                await self.db.scalars(
                    select(UniverseMembershipVersion)
                    .where(
                        UniverseMembershipVersion.universe_id == universe_id,
                        UniverseMembershipVersion.instrument_id == item.instrument_id,
                        UniverseMembershipVersion.valid_from == item.valid_from,
                    )
                    .order_by(UniverseMembershipVersion.observed_at.desc())
                    .limit(1)
                )
            ).first()
            self.db.add(
                UniverseMembershipVersion(
                    universe_id=universe_id,
                    instrument_id=item.instrument_id,
                    valid_from=item.valid_from,
                    valid_to=item.valid_to,
                    known_at=item.known_at or raw.received_at,
                    observed_at=raw.received_at,
                    source_id=raw.source_id,
                    raw_ingestion_id=raw.id,
                    membership_status=item.membership_status,
                    row_key=key,
                    version=digest(value),
                    replaces_id=previous.id if previous else None,
                    evidence={
                        "level": "USER_ASSERTED" if item.known_at else "LOCAL_FIRST_OBSERVATION"
                    },
                )
            )
            count += 1
        await self.db.commit()
        return {"inserted": count}
