from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import ValidationRecord
from app.services.fundamentals import digest
from app.services.pit_datasets import code_manifest
from app.services.pit_features import json_value


class ValidationRecords:
    def __init__(self, db: AsyncSession, user_id: UUID):
        self.db, self.user_id = db, user_id

    async def owned(self, identifier: UUID, kind: str | None = None) -> ValidationRecord:
        row = await self.db.get(ValidationRecord, identifier)
        if not row or row.user_id != self.user_id or (kind and row.kind != kind):
            raise AppError(
                404, "VALIDATION_RECORD_NOT_FOUND", "Private validation evidence missing"
            )
        expected = digest(
            {
                "kind": row.kind,
                "request": row.request,
                "result": row.result,
                "parent_id": str(row.parent_id) if row.parent_id else None,
            }
        )
        if expected != row.content_hash:
            raise AppError(409, "VALIDATION_CONTENT_CHANGED", "Archived evidence hash differs")
        return row

    async def list(self, kind: str | None = None, limit: int = 100) -> list[ValidationRecord]:
        query = select(ValidationRecord).where(ValidationRecord.user_id == self.user_id)
        if kind:
            query = query.where(ValidationRecord.kind == kind)
        return list(
            (
                await self.db.scalars(
                    query.order_by(
                        ValidationRecord.created_at.desc(), ValidationRecord.id.desc()
                    ).limit(limit)
                )
            ).all()
        )

    async def append(
        self,
        kind: str,
        request: dict[str, Any],
        result: dict[str, Any],
        *,
        parent_id: UUID | None = None,
        dedup_key: str | None = None,
    ) -> ValidationRecord:
        if parent_id:
            await self.owned(parent_id)
        if dedup_key:
            previous = await self.db.scalar(
                select(ValidationRecord).where(
                    ValidationRecord.user_id == self.user_id,
                    ValidationRecord.kind == kind,
                    ValidationRecord.dedup_key == dedup_key,
                )
            )
            if previous:
                return await self.owned(previous.id, kind)
        request, result = json_value(request), json_value({**result, "code": code_manifest()})
        row = ValidationRecord(
            user_id=self.user_id,
            parent_id=parent_id,
            kind=kind,
            dedup_key=dedup_key,
            request=request,
            result=result,
            content_hash=digest(
                {
                    "kind": kind,
                    "request": request,
                    "result": result,
                    "parent_id": str(parent_id) if parent_id else None,
                }
            ),
        )
        self.db.add(row)
        await self.db.commit()
        return row
