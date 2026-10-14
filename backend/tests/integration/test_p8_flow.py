import asyncio
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import delete, or_, update
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.main import create_app
from app.models import (
    AuditEvent,
    CashBalance,
    DataQuarantine,
    Instrument,
    InstrumentIdentifier,
    Portfolio,
    PortfolioAccount,
    PortfolioSnapshot,
    PositionSnapshot,
    PriceDaily,
    PriceDailyVersion,
    RawIngestion,
    RiskSnapshot,
    ScenarioRun,
    SessionRecord,
    Transaction,
    User,
    WhatIfRun,
)
from app.services.auth import AuthService
from app.services.market_import import MarketImportService
from app.services.raw_ingestion import RawIngestionService
from tests.integration.test_portfolio_flow import MemoryStorage


@pytest.mark.integration
def test_p8_owned_risk_scenarios_immutable_and_whatif_ledger_unchanged():
    async def run():
        users, portfolios, raw_ids = [], [], []
        instrument_id, ticker = uuid4(), "R" + uuid4().hex[:10].upper()
        password = secrets.token_urlsafe(32)
        day = datetime.now(UTC).date()
        async with get_session_factory()() as db:
            try:
                user = await AuthService(db).create_user("p8_" + uuid4().hex[:12], password)
                other = await AuthService(db).create_user("p8_" + uuid4().hex[:12], password)
                users, usernames = [user.id, other.id], [user.username, other.username]
                db.add(
                    Instrument(
                        id=instrument_id,
                        ticker=ticker,
                        name="SYNTHETIC P8 local golden",
                        asset_type="STOCK",
                        currency="CHF",
                    )
                )
                db.add(
                    InstrumentIdentifier(
                        instrument_id=instrument_id,
                        type="TICKER",
                        value=ticker,
                        market_key="",
                        valid_from=day,
                        observed_at=datetime.now(UTC),
                    )
                )
                await db.commit()
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=create_app()),
                    base_url="http://testserver",
                    headers={"Origin": get_settings().frontend_origin},
                    timeout=120,
                ) as client:
                    assert (await client.get("/api/v1/scenario-definitions")).status_code == 401
                    assert (
                        await client.post(
                            "/api/v1/auth/login",
                            json={"username": usernames[0], "password": password},
                        )
                    ).status_code == 200
                    created = await client.post(
                        "/api/v1/portfolios",
                        json={"name": "P8 synthetic golden", "base_currency": "CHF"},
                    )
                    assert created.status_code == 201, created.text
                    pid = created.json()["id"]
                    portfolios.append(UUID(pid))
                    account = await client.post(
                        f"/api/v1/portfolios/{pid}/accounts",
                        json={"name": "Broker", "account_type": "BROKER"},
                    )
                    aid = account.json()["id"]
                    assert (
                        await client.post(
                            f"/api/v1/portfolios/{pid}/transactions",
                            json={
                                "account_id": aid,
                                "type": "DEPOSIT",
                                "trade_date": str(day - timedelta(days=100)),
                                "amount": "10000",
                                "currency": "CHF",
                            },
                        )
                    ).status_code == 201
                    cash_risk = await client.post(
                        f"/api/v1/portfolios/{pid}/risk", json={"window": 30}
                    )
                    assert cash_risk.status_code == 200, cash_risk.text
                    assert (
                        Decimal(cash_risk.json()["result"]["metrics"]["annualized_volatility"]) == 0
                    )  # Known cash-only constant NAV, not fallback.
                    market = MarketImportService(db, RawIngestionService(db, MemoryStorage()))
                    raw = await market.preview(
                        "prices",
                        f"date,ticker,close,currency\n{day},{ticker},120,CHF\n".encode(),
                        "SYNTHETIC-p8-price.csv",
                    )
                    raw_ids.append(raw["raw_ingestion_id"])
                    assert (await market.commit("prices", raw["raw_ingestion_id"], raw["mapping"]))[
                        "inserted"
                    ] == 1
                    assert (
                        await client.post(
                            f"/api/v1/portfolios/{pid}/transactions",
                            json={
                                "account_id": aid,
                                "instrument_id": str(instrument_id),
                                "type": "BUY",
                                "trade_date": str(day),
                                "quantity": "10",
                                "price": "100",
                                "currency": "CHF",
                            },
                        )
                    ).status_code == 201
                    before = (await client.get(f"/api/v1/portfolios/{pid}/transactions")).json()
                    risk = await client.post(f"/api/v1/portfolios/{pid}/risk", json={"window": 30})
                    assert risk.status_code == 200, risk.text
                    snapshot = risk.json()
                    rid = UUID(snapshot["id"])
                    assert snapshot["result"]["metrics"]["annualized_volatility"] is None
                    assert snapshot["result"]["quality"]["calendar_missing"] == [str(instrument_id)]
                    assert (
                        Decimal(snapshot["result"]["current_valuation"]["total_value_base"])
                        == 10200
                    )
                    assert len((await client.get("/api/v1/scenario-definitions")).json()) == 7
                    shock = await client.post(
                        f"/api/v1/portfolios/{pid}/scenarios",
                        json={
                            "risk_snapshot_id": str(rid),
                            "calculation_type": "DIRECT_POSITION_SHOCK",
                            "shock": "-.1",
                            "instrument_ids": [str(instrument_id)],
                        },
                    )
                    assert shock.status_code == 200, shock.text
                    assert Decimal(shock.json()["result"]["impact_base"]) == -120
                    whatif = await client.post(
                        f"/api/v1/portfolios/{pid}/what-if",
                        json={
                            "risk_snapshot_id": str(rid),
                            "trades": [
                                {
                                    "instrument_id": str(instrument_id),
                                    "side": "BUY",
                                    "amount_base": "100",
                                }
                            ],
                        },
                    )
                    assert whatif.status_code == 200, whatif.text
                    assert Decimal(
                        whatif.json()["result"]["current_valuation"]["total_value_base"]
                    ) == Decimal("10198.9")
                    assert (
                        await client.get(f"/api/v1/portfolios/{pid}/transactions")
                    ).json() == before
                    correction = await market.preview(
                        "prices",
                        f"date,ticker,close,currency\n{day},{ticker},121,CHF\n".encode(),
                        "SYNTHETIC-p8-correction.csv",
                    )
                    raw_ids.append(correction["raw_ingestion_id"])
                    await market.commit(
                        "prices",
                        correction["raw_ingestion_id"],
                        correction["mapping"],
                        conflict_policy="ACCEPT_NEW",
                        decision_note="Explicit synthetic correction for immutable history test",
                    )
                    old = await client.get(f"/api/v1/portfolios/{pid}/risk/{rid}")
                    assert old.json() == snapshot
                    changed = await client.post(
                        f"/api/v1/portfolios/{pid}/risk", json={"window": 30}
                    )
                    assert changed.status_code == 200, changed.text
                    assert (
                        Decimal(changed.json()["result"]["current_valuation"]["total_value_base"])
                        == 10210
                    )
                    assert changed.json()["content_hash"] != snapshot["content_hash"]
                    for path in (
                        "risk",
                        "risk/history",
                        "correlations",
                        "exposures",
                        "simulation-history",
                    ):
                        assert (
                            await client.get(f"/api/v1/portfolios/{pid}/{path}")
                        ).status_code == 200
                    future = await client.post(
                        f"/api/v1/portfolios/{pid}/risk",
                        json={"as_of": (datetime.now(UTC) + timedelta(days=1)).isoformat()},
                    )
                    assert future.status_code == 422
                    async with httpx.AsyncClient(
                        transport=httpx.ASGITransport(app=create_app()),
                        base_url="http://testserver",
                    ) as outsider:
                        assert (
                            await outsider.post(
                                "/api/v1/auth/login",
                                json={"username": usernames[1], "password": password},
                            )
                        ).status_code == 200
                        for path in (
                            "risk",
                            "risk/history",
                            "correlations",
                            "exposures",
                            f"risk/{rid}",
                            "simulation-history",
                        ):
                            assert (
                                await outsider.get(f"/api/v1/portfolios/{pid}/{path}")
                            ).status_code == 404
                        assert (
                            await outsider.post(
                                f"/api/v1/portfolios/{pid}/what-if",
                                json={
                                    "risk_snapshot_id": str(rid),
                                    "trades": [
                                        {
                                            "instrument_id": str(instrument_id),
                                            "side": "SELL",
                                            "sell_fraction": ".1",
                                        }
                                    ],
                                },
                            )
                        ).status_code == 404
                    with pytest.raises(DBAPIError):
                        await db.execute(
                            update(RiskSnapshot).where(RiskSnapshot.id == rid).values(result={})
                        )
                    await db.rollback()
            finally:
                await db.rollback()
                for model in (
                    WhatIfRun,
                    ScenarioRun,
                    RiskSnapshot,
                    CashBalance,
                    PositionSnapshot,
                    PortfolioSnapshot,
                    Transaction,
                    PortfolioAccount,
                ):
                    await db.execute(delete(model).where(model.portfolio_id.in_(portfolios)))
                await db.execute(delete(Portfolio).where(Portfolio.id.in_(portfolios)))
                for model in (PriceDaily, PriceDailyVersion, InstrumentIdentifier):
                    await db.execute(delete(model).where(model.instrument_id == instrument_id))
                await db.execute(delete(Instrument).where(Instrument.id == instrument_id))
                await db.execute(
                    delete(DataQuarantine).where(DataQuarantine.raw_ingestion_id.in_(raw_ids))
                )
                await db.execute(
                    delete(AuditEvent).where(
                        or_(
                            AuditEvent.actor_user_id.in_(users),
                            AuditEvent.resource_id.in_([str(r) for r in raw_ids]),
                        )
                    )
                )
                await db.execute(delete(RawIngestion).where(RawIngestion.id.in_(raw_ids)))
                await db.execute(delete(SessionRecord).where(SessionRecord.user_id.in_(users)))
                await db.execute(delete(User).where(User.id.in_(users)))
                await db.commit()

    async def disposed():
        try:
            await run()
        finally:
            await get_engine().dispose()

    asyncio.run(disposed())
