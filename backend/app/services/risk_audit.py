import hashlib
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.research import view
from app.models import RiskSnapshot, ScenarioRun, WhatIfRun
from app.services.fundamentals import digest
from app.services.pit_evidence import ENTITIES
from app.services.pit_features import json_value
from app.services.raw_ingestion import RawIngestionService


async def history_checkpoint(
    db: AsyncSession, user_id: UUID, portfolio_id: UUID, verify: bool = False
) -> dict[str, Any]:
    data: dict[str, Any] = {}
    risk_hashes = {}
    for key, model in (("risk", RiskSnapshot), ("scenarios", ScenarioRun), ("what_if", WhatIfRun)):
        rows: list[Any] = list(
            (
                await db.scalars(
                    select(model)
                    .where(model.user_id == user_id, model.portfolio_id == portfolio_id)
                    .order_by(model.id)
                )
            ).all()
        )
        data[key] = [json_value(view(row)) for row in rows]
        for row in rows:
            payload = {"configuration": row.configuration, "result": row.result}
            if isinstance(row, RiskSnapshot):
                risk_hashes[row.id] = row.content_hash
                if verify:
                    for kind, expected in row.result.get("market_version_hashes", {}).items():
                        versions = (
                            await db.scalars(
                                select(ENTITIES[kind]).where(
                                    ENTITIES[kind].id.in_([UUID(v) for v in expected])
                                )
                            )
                        ).all()
                        actual = {
                            str(v.id): digest(
                                json_value(
                                    {
                                        column.name: getattr(v, column.name)
                                        for column in v.__table__.columns
                                    }
                                )
                            )
                            for v in versions
                        }
                        assert actual == expected, "Risk pinned canonical versions changed"
                    for raw_id, expected_hash in row.result.get("raw_hashes", {}).items():
                        assert (
                            hashlib.sha256(
                                await RawIngestionService(db).get_verified(UUID(raw_id))
                            ).hexdigest()
                            == expected_hash
                        )
            else:
                assert row.risk_snapshot_id in risk_hashes, "Risk parent missing"
                payload["risk_hash"] = risk_hashes[row.risk_snapshot_id]
            assert digest(payload) == row.content_hash, "Immutable risk/simulation hash mismatch"
    return {
        "risk_history_hash": digest(data),
        "risk_count": len(data["risk"]),
        "scenario_count": len(data["scenarios"]),
        "what_if_count": len(data["what_if"]),
    }
