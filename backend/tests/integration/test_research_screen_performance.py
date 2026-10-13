"""Bounded-query regression on hundreds of isolated nonfinancial test instruments."""

from __future__ import annotations

import asyncio
from time import perf_counter
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, event

from app.db.session import get_engine, get_session_factory
from app.main import create_app
from app.models import AuditEvent, Instrument, User
from app.services.auth import AuthService


@pytest.mark.integration
def test_screener_pagination_on_300_instruments_has_bounded_queries() -> None:
    async def run() -> None:
        prefix = f"Synthetic Screen {uuid4().hex}"
        ids = [uuid4() for _ in range(300)]
        engine = get_engine()
        async with get_session_factory()() as db:
            user = await AuthService(db).create_user(
                "screen_" + uuid4().hex[:12], "test-only-screen-password-2"
            )
            uid = user.id
            db.add_all(
                [
                    Instrument(
                        id=identifier,
                        name=f"{prefix} {index:03}",
                        asset_type="STOCK",
                        currency="CHF",
                        country="CH",
                    )
                    for index, identifier in enumerate(ids)
                ]
            )
            await db.commit()
            statements: list[str] = []

            def record(
                _conn: object,
                _cursor: object,
                statement: str,
                _parameters: object,
                _context: object,
                _many: bool,
            ) -> None:
                if statement.lstrip().upper().startswith("SELECT"):
                    statements.append(statement)

            try:
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=create_app()), base_url="http://test"
                ) as client:
                    await client.post(
                        "/api/v1/auth/login",
                        json={"username": user.username, "password": "test-only-screen-password-2"},
                    )
                    event.listen(engine.sync_engine, "before_cursor_execute", record)
                    started = perf_counter()
                    response = await client.get(
                        "/api/v1/research/instruments",
                        params={"q": prefix, "offset": 25, "limit": 25},
                    )
                    elapsed = perf_counter() - started
                    event.remove(engine.sync_engine, "before_cursor_execute", record)
                    assert response.status_code == 200, response.text
                    rows = response.json()["items"]
                    assert len(rows) == 25 and rows[0]["instrument"]["name"].endswith("025")
                    assert all(
                        row["research"] is None and row["status"] == "INSUFFICIENT_DATA"
                        for row in rows
                    )
                    assert len(statements) <= 6, f"Unexpected N+1: {len(statements)} SELECTs"
                    filtered = await client.get(
                        "/api/v1/research/instruments",
                        params={"q": prefix, "metric": "P/E", "minimum": "0"},
                    )
                    assert filtered.status_code == 200 and filtered.json()["items"] == []
                    print(
                        f"P5 screener 300 instruments: {len(statements)} SELECTs, "
                        f"{elapsed:.3f}s, 25 rows"
                    )
            finally:
                if event.contains(engine.sync_engine, "before_cursor_execute", record):
                    event.remove(engine.sync_engine, "before_cursor_execute", record)
                await db.rollback()
                await db.execute(delete(Instrument).where(Instrument.id.in_(ids)))
                await db.execute(delete(AuditEvent).where(AuditEvent.actor_user_id == uid))
                await db.execute(delete(User).where(User.id == uid))
                await db.commit()
        await engine.dispose()

    asyncio.run(run())
