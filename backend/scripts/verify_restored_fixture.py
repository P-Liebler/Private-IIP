"""Run inside the isolated restore API container against an explicit test fixture."""

from __future__ import annotations

import asyncio
import os
from decimal import Decimal
from uuid import UUID

import httpx
from sqlalchemy import select, text

from app.db.session import get_session_factory
from app.models import Portfolio, Transaction, User
from app.services.raw_ingestion import RawIngestionService


async def main() -> None:
    username = os.environ["RESTORE_TEST_USERNAME"]
    password = os.environ["RESTORE_TEST_PASSWORD"]
    portfolio_id = UUID(os.environ["RESTORE_TEST_PORTFOLIO_ID"])
    raw_id = UUID(os.environ["RESTORE_TEST_RAW_ID"])
    expected = Decimal(os.environ["RESTORE_TEST_VALUE"])
    async with get_session_factory()() as db:
        revision = await db.scalar(text("SELECT version_num FROM alembic_version"))
        assert revision == "0007_snapshot_provenance", "Migration head mismatch"
        user = await db.scalar(select(User).where(User.username == username))
        assert user is not None and user.is_active, "Fixture user missing"
        portfolio = await db.get(Portfolio, portfolio_id)
        assert portfolio is not None and portfolio.user_id == user.id, "Fixture portfolio missing"
        rows = (
            await db.scalars(select(Transaction).where(Transaction.portfolio_id == portfolio_id))
        ).all()
        assert rows, "Fixture transactions missing"
        raw = await RawIngestionService(db).get_verified(raw_id)
        assert raw, "Fixture raw object empty"
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8000", headers={"Origin": "http://restore.local"}
    ) as client:
        login = await client.post(
            "/api/v1/auth/login", json={"username": username, "password": password}
        )
        assert login.status_code == 200, "Restored login failed"
        value = await client.get(f"/api/v1/portfolios/{portfolio_id}/valuation")
        assert value.status_code == 200, "Restored valuation request failed"
        payload = value.json()
        assert payload["status"] == "COMPLETE", "Restored valuation incomplete"
        assert Decimal(payload["total_value_base"]) == expected, "Restored value mismatch"
    print("Isolated restore verified: migration, raw hash, login and portfolio valuation")


if __name__ == "__main__":
    asyncio.run(main())
