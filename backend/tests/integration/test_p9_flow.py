import asyncio
import secrets
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.main import create_app
from app.models import (
    AuditEvent,
    CashBalance,
    DatasetVersion,
    Instrument,
    Portfolio,
    PortfolioAccount,
    PortfolioSnapshot,
    PositionSnapshot,
    Prediction,
    ResearchMetric,
    ResearchSnapshot,
    RiskSnapshot,
    SessionRecord,
    Transaction,
    UniverseDefinition,
    User,
    WhatIfRun,
)
from app.models.recommendations import (
    InvestmentProfileVersion,
    Recommendation,
    RecommendationBacktest,
)
from app.services.auth import AuthService


@pytest.mark.integration
def test_owned_profiles_abstentions_replay_immutability_and_no_ledger_mutation():
    async def run():
        users, portfolios = [], []
        iid = uuid4()
        password = secrets.token_urlsafe(32)
        async with get_session_factory()() as db:
            try:
                first = await AuthService(db).create_user("p9_" + uuid4().hex[:12], password)
                other = await AuthService(db).create_user("p9_" + uuid4().hex[:12], password)
                users, usernames = [first.id, other.id], [first.username, other.username]
                db.add(
                    Instrument(
                        id=iid,
                        name="SYNTHETIC P9 missing data",
                        ticker="P9" + uuid4().hex[:8],
                        asset_type="STOCK",
                        currency="CHF",
                    )
                )
                await db.commit()
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=create_app()),
                    base_url="http://testserver",
                    headers={"Origin": get_settings().frontend_origin},
                    timeout=120,
                ) as client:
                    assert (await client.get("/api/v1/investment-profile")).status_code == 401
                    assert (
                        await client.post(
                            "/api/v1/auth/login",
                            json={"username": usernames[0], "password": password},
                        )
                    ).status_code == 200
                    p = (await client.get("/api/v1/investment-profile")).json()
                    assert p["id"] is None and p["status"] == "UNCONFIRMED_DEFAULTS"
                    saved = await client.patch(
                        "/api/v1/investment-profile",
                        json={"preferences": {**p["preferences"], "confirmed": True}},
                    )
                    assert saved.status_code == 200, saved.text
                    profile_id = UUID(saved.json()["id"])
                    assert (
                        await client.patch(
                            "/api/v1/investment-profile", json={"preferences": p["preferences"]}
                        )
                    ).status_code == 409
                    pid = (
                        await client.post(
                            "/api/v1/portfolios",
                            json={"name": "SYNTHETIC P9", "base_currency": "CHF"},
                        )
                    ).json()["id"]
                    portfolios.append(UUID(pid))
                    aid = (
                        await client.post(
                            f"/api/v1/portfolios/{pid}/accounts",
                            json={"name": "Cash", "account_type": "BROKER"},
                        )
                    ).json()["id"]
                    assert (
                        await client.post(
                            f"/api/v1/portfolios/{pid}/transactions",
                            json={
                                "account_id": aid,
                                "type": "DEPOSIT",
                                "trade_date": datetime.now(UTC).date().isoformat(),
                                "amount": "10000",
                                "currency": "CHF",
                            },
                        )
                    ).status_code == 201
                    risk = await client.post(f"/api/v1/portfolios/{pid}/risk", json={"window": 30})
                    assert risk.status_code == 200, risk.text
                    count = await db.scalar(
                        select(func.count())
                        .select_from(Transaction)
                        .where(Transaction.portfolio_id == UUID(pid))
                    )
                    result = await client.post(
                        "/api/v1/recommendations/evaluate",
                        json={
                            "portfolio_id": pid,
                            "risk_snapshot_id": risk.json()["id"],
                            "instrument_ids": [str(iid)],
                            "amount": "100",
                        },
                    )
                    assert result.status_code == 200, result.text
                    row = result.json()[0]
                    rid = UUID(row["id"])
                    assert row["category"] == "INSUFFICIENT_DATA"
                    assert (
                        "NO_VALIDATED_PRODUCTION_FORECAST" in row["eligibility"]["missing_inputs"]
                    )
                    assert row["profile_version_id"] == str(profile_id)
                    assert row["result"]["scoring"]["score"] is None
                    universe = UniverseDefinition(
                        user_id=users[0], name="SYNTHETIC P9 backtest gate", configuration={}
                    )
                    db.add(universe)
                    await db.flush()
                    dataset = DatasetVersion(
                        user_id=users[0],
                        universe_id=universe.id,
                        content_hash=uuid4().hex * 2,
                        configuration={
                            "availability_mode": "STRICT_PIT",
                            "data_context": "SYNTHETIC_SIMULATION_NOT_REAL_ARCHIVE",
                        },
                        manifest={},
                        rows=[],
                        quality={},
                    )
                    db.add(dataset)
                    await db.commit()
                    rejected = await client.post(
                        "/api/v1/recommendations/backtests",
                        json={
                            "portfolio_id": pid,
                            "dataset_id": str(dataset.id),
                            "recommendation_ids": [str(rid)],
                        },
                    )
                    assert rejected.status_code == 200, rejected.text
                    assert (
                        rejected.json()["result"]["status"] == "RECOMMENDATION_BACKTEST_UNAVAILABLE"
                    )
                    assert "REAL_STRICT_PIT_DATA_REQUIRED" in rejected.json()["result"]["reasons"]
                    assert (
                        "HISTORICAL_ELIGIBLE_RECOMMENDATIONS_REQUIRED"
                        in rejected.json()["result"]["reasons"]
                    )
                    promotion = await client.post(
                        "/api/v1/recommendations/strategy-reviews",
                        json={
                            "backtest_id": rejected.json()["id"],
                            "status": "PRODUCTION",
                            "rationale": "Synthetic local test evidence cannot justify "
                            "a real production strategy.",
                        },
                    )
                    assert promotion.status_code in (403, 409)
                    assert (
                        await client.post(f"/api/v1/recommendations/{rid}/replay")
                    ).json() == row["result"]
                    assert (
                        len(
                            (
                                await client.get(
                                    f"/api/v1/recommendations/history?portfolio_id={pid}"
                                )
                            ).json()
                        )
                        == 1
                    )
                    assert (
                        await db.scalar(
                            select(func.count())
                            .select_from(Transaction)
                            .where(Transaction.portfolio_id == UUID(pid))
                        )
                        == count
                    )
                    assert (await client.post("/api/v1/auth/logout")).status_code in (200, 204)
                    await client.post(
                        "/api/v1/auth/login", json={"username": usernames[1], "password": password}
                    )
                    assert (await client.get(f"/api/v1/recommendations/{rid}")).status_code == 404
                    assert (
                        await client.get(f"/api/v1/recommendations/history?portfolio_id={pid}")
                    ).status_code == 404
                    assert (await client.get("/api/v1/investment-profile")).json()["id"] is None
                    for model, identifier in (
                        (Recommendation, rid),
                        (InvestmentProfileVersion, profile_id),
                    ):
                        with pytest.raises(DBAPIError):
                            await db.execute(
                                update(model)
                                .where(model.id == identifier)
                                .values(content_hash="changed")
                                if model is InvestmentProfileVersion
                                else update(model)
                                .where(model.id == identifier)
                                .values(category="HOLD")
                            )
                        await db.rollback()
            finally:
                await db.rollback()
                for model in (
                    Recommendation,
                    RecommendationBacktest,
                    WhatIfRun,
                    RiskSnapshot,
                    PositionSnapshot,
                    PortfolioSnapshot,
                    CashBalance,
                    Transaction,
                    PortfolioAccount,
                ):
                    await db.execute(delete(model).where(model.portfolio_id.in_(portfolios)))
                await db.execute(delete(Portfolio).where(Portfolio.id.in_(portfolios)))
                await db.execute(
                    delete(ResearchMetric).where(
                        ResearchMetric.snapshot_id.in_(
                            select(ResearchSnapshot.id).where(ResearchSnapshot.instrument_id == iid)
                        )
                    )
                )
                await db.execute(
                    delete(ResearchSnapshot).where(ResearchSnapshot.instrument_id == iid)
                )
                await db.execute(delete(Prediction).where(Prediction.instrument_id == iid))
                await db.execute(delete(Instrument).where(Instrument.id == iid))
                await db.execute(
                    delete(InvestmentProfileVersion).where(
                        InvestmentProfileVersion.user_id.in_(users)
                    )
                )
                for model in (AuditEvent, SessionRecord):
                    key = model.actor_user_id if model is AuditEvent else model.user_id
                    await db.execute(delete(model).where(key.in_(users)))
                await db.execute(delete(DatasetVersion).where(DatasetVersion.user_id.in_(users)))
                await db.execute(
                    delete(UniverseDefinition).where(UniverseDefinition.user_id.in_(users))
                )
                await db.execute(delete(User).where(User.id.in_(users)))
                await db.commit()

    async def disposed():
        try:
            await run()
        finally:
            await get_engine().dispose()

    asyncio.run(disposed())
