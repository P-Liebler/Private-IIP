"""Deterministic restore checkpoint for PR2 evidence, including immutable links."""

from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ValidationRecord
from app.services.fundamentals import digest
from app.services.validation_records import ValidationRecords


async def validation_checkpoint(db: AsyncSession) -> dict[str, Any]:
    rows = (await db.scalars(select(ValidationRecord).order_by(ValidationRecord.id))).all()
    payload = []
    for row in rows:
        await ValidationRecords(db, row.user_id).owned(row.id)
        payload.append(
            jsonable_encoder(
                {c.name: getattr(row, c.name) for c in ValidationRecord.__table__.columns}
            )
        )
    return {"validation_history_hash": digest(payload), "records": len(payload)}
