from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.storage import ObjectStorage, get_storage
from app.models import RawIngestion

logger = logging.getLogger(__name__)
_METADATA_KEYS = {
    "endpoint",
    "method",
    "identifier_type",
    "identifier_value",
    "filename",
    "user_id",
    "portfolio_id",
    "account_id",
}


def safe_request_metadata(values: dict[str, str | int] | None) -> dict[str, str | int]:
    result: dict[str, str | int] = {}
    for key, value in (values or {}).items():
        if (
            key not in _METADATA_KEYS
            or isinstance(value, bool)
            or not isinstance(value, (str, int))
        ):
            raise ValueError("Unsupported raw request metadata field")
        if isinstance(value, str):
            if (
                len(value) > 300
                or any(ord(character) < 32 for character in value)
                or any(
                    fragment in value.lower()
                    for fragment in (
                        "authorization",
                        "api_key",
                        "apikey",
                        "password",
                        "secret",
                        "token=",
                    )
                )
            ):
                raise ValueError("Sensitive or oversized raw request metadata")
            if key == "endpoint" and (not value.startswith("/") or "?" in value or "#" in value):
                raise ValueError("Endpoint metadata must be a path without query parameters")
            if key == "filename" and ("/" in value or "\\" in value):
                raise ValueError("Filename metadata must not contain a path")
        result[key] = value
    return result


class RawIngestionService:
    def __init__(self, db: AsyncSession, storage: ObjectStorage | None = None) -> None:
        self.db = db
        self.storage = storage or get_storage()

    async def store(
        self,
        *,
        data: bytes,
        source_id: UUID,
        source_slug: str,
        resource_type: str,
        instrument_id: UUID | None = None,
        requested_at: datetime | None = None,
        http_status: int | None = None,
        content_type: str = "application/octet-stream",
        request_metadata: dict[str, str | int] | None = None,
    ) -> RawIngestion:
        metadata = safe_request_metadata(request_metadata)
        if len(data) > 20_000_000:
            raise AppError(413, "RAW_TOO_LARGE", "Raw object exceeds the size limit")
        received_at = datetime.now(UTC)
        raw_id = uuid4()
        suffix = (
            ".csv"
            if content_type.startswith("text/csv")
            else ".json"
            if "json" in content_type
            else ".bin"
        )
        key = f"raw/{source_slug.lower()}/{received_at:%Y/%m/%d}/{raw_id}{suffix}"
        record = RawIngestion(
            id=raw_id,
            source_id=source_id,
            instrument_id=instrument_id,
            resource_type=resource_type,
            requested_at=requested_at,
            received_at=received_at,
            object_path=key,
            sha256=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data),
            http_status=http_status,
            content_type=content_type,
            status="PENDING",
            request_metadata=metadata,
        )
        self.db.add(record)
        try:
            await self.db.commit()  # Durable pending reference exists before uploading.
        except Exception as error:
            await self.db.rollback()
            logger.exception("raw ingestion pending record could not be committed")
            raise AppError(
                503, "RAW_DATABASE_UNAVAILABLE", "Raw ingestion database unavailable"
            ) from error
        try:
            await asyncio.to_thread(self.storage.put, key, data, content_type)
        except Exception as error:
            record.status = "FAILED"
            record.error = f"storage:{type(error).__name__}"
            try:
                await self.db.commit()
            except Exception:
                await self.db.rollback()
                logger.exception("raw upload failure could not be recorded; raw_id=%s", raw_id)
            logger.exception("raw object upload failed; raw_id=%s", raw_id)
            raise AppError(
                503, "RAW_STORAGE_UNAVAILABLE", "Raw object could not be stored"
            ) from error
        record.status = "STORED"
        try:
            await self.db.commit()
        except Exception as error:
            await self.db.rollback()
            # The durable PENDING row contains the object path/hash for reconciliation.
            logger.exception("raw object uploaded but final commit failed; raw_id=%s", raw_id)
            raise AppError(
                503, "RAW_DATABASE_UNAVAILABLE", "Raw ingestion database unavailable"
            ) from error
        return record

    async def get(self, raw_id: UUID) -> RawIngestion:
        record = await self.db.get(RawIngestion, raw_id)
        if record is None:
            raise AppError(404, "RAW_NOT_FOUND", "Raw ingestion not found")
        return record

    async def record_failure(
        self,
        *,
        source_id: UUID,
        resource_type: str,
        requested_at: datetime | None,
        error_code: str,
        request_metadata: dict[str, str | int] | None = None,
    ) -> RawIngestion:
        record = RawIngestion(
            id=uuid4(),
            source_id=source_id,
            resource_type=resource_type,
            requested_at=requested_at,
            received_at=datetime.now(UTC),
            status="FAILED",
            error=error_code[:300],
            request_metadata=safe_request_metadata(request_metadata),
        )
        self.db.add(record)
        await self.db.commit()
        return record

    async def get_verified(self, raw_id: UUID) -> bytes:
        record = await self.get(raw_id)
        if record.status != "STORED" or not record.object_path or not record.sha256:
            raise AppError(409, "RAW_NOT_AVAILABLE", "Raw object is not stored")
        try:
            data = await asyncio.to_thread(self.storage.get, record.object_path)
        except Exception as error:
            logger.exception("raw object read failed; raw_id=%s", raw_id)
            raise AppError(503, "RAW_STORAGE_UNAVAILABLE", "Raw object unavailable") from error
        if hashlib.sha256(data).hexdigest() != record.sha256:
            logger.error("raw integrity mismatch; raw_id=%s", raw_id)
            raise AppError(409, "RAW_INTEGRITY_ERROR", "Raw object integrity check failed")
        return data
