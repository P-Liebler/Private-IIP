import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.risk.exposure import liquidity_score
from app.services.pit_features import FeatureSnapshotService
from app.services.risk_market import RiskMarket


def test_total_returns_raw_split_dividend_and_fx_once(monkeypatch):
    async def run():
        iid = uuid4()
        db = SimpleNamespace(
            get=AsyncMock(return_value=SimpleNamespace(exchange="NYSE", currency="USD"))
        )
        market = RiskMarket(
            db, date(2025, 1, 2), date(2025, 1, 7), datetime(2025, 1, 8, tzinfo=UTC)
        )
        days = [date(2025, 1, d) for d in (2, 3, 6, 7)]
        prices = [
            {
                "id": str(uuid4()),
                "date": day,
                "currency": "USD",
                "close": Decimal(close),
                "adjusted_close": Decimal(999),
            }
            for day, close in zip(days, ("100", "50", "49", "50"), strict=True)
        ]
        actions = [
            {
                "id": str(uuid4()),
                "date": "2025-01-03",
                "type": "SPLIT",
                "ratio": "2",
                "cash_amount": None,
                "currency": "USD",
            },
            {
                "id": str(uuid4()),
                "date": "2025-01-06",
                "type": "DIVIDEND",
                "ratio": None,
                "cash_amount": "1",
                "currency": "USD",
            },
        ]
        monkeypatch.setattr(
            FeatureSnapshotService, "actions", AsyncMock(return_value=(actions, "coverage"))
        )
        market.load = AsyncMock(return_value=prices)

        async def fx(_base, _quote, day):
            return {
                "status": "AVAILABLE",
                "rate": Decimal(".9") if day < date(2025, 1, 6) else Decimal(1),
            }

        market.fx = fx
        result = await market.total_returns(iid, "CHF", days)
        assert result["returns"]["2025-01-03"] == 0
        assert abs(result["returns"]["2025-01-06"] - Decimal(1) / 9) < Decimal("1e-25")
        assert abs(result["returns"]["2025-01-07"] - Decimal(1) / 49) < Decimal("1e-25")
        market.load = AsyncMock(return_value=[p for p in prices if p["date"] != date(2025, 1, 6)])
        result = await market.total_returns(iid, "CHF", days)
        assert set(result["returns"]) == {"2025-01-03"}
        monkeypatch.setattr(FeatureSnapshotService, "actions", AsyncMock(return_value=([], None)))
        assert (await market.total_returns(iid, "CHF", days))["returns"] == {}

    asyncio.run(run())


def test_closed_market_alignment_uses_last_official_close_and_current_fx(monkeypatch):
    async def run():
        iid = uuid4()
        db = SimpleNamespace(
            get=AsyncMock(return_value=SimpleNamespace(exchange="NYSE", currency="USD"))
        )
        market = RiskMarket(
            db, date(2025, 1, 17), date(2025, 1, 21), datetime(2025, 1, 22, tzinfo=UTC)
        )
        monkeypatch.setattr(
            FeatureSnapshotService, "actions", AsyncMock(return_value=([], "coverage"))
        )
        market.load = AsyncMock(
            return_value=[
                {
                    "id": str(uuid4()),
                    "date": date(2025, 1, day),
                    "currency": "USD",
                    "close": Decimal(100),
                }
                for day in (17, 21)
            ]
        )

        async def fx(_base, _quote, day):
            return {"status": "AVAILABLE", "rate": Decimal(1) if day.day == 17 else Decimal("1.01")}

        market.fx = fx
        result = await market.total_returns(iid, "CHF", [date(2025, 1, d) for d in (17, 20, 21)])
        assert result["returns"] == {"2025-01-20": Decimal(".01"), "2025-01-21": Decimal(0)}

    asyncio.run(run())


def test_liquidity_volume_proxy_and_missing_evidence():
    holding = {"instrument_id": "stock", "quantity": "10", "market_value_base": "1000"}
    evidence = {
        "stock": {"average_volume": "1000", "observations": 20, "price_version_ids": ["pinned"]}
    }
    score = liquidity_score([holding], evidence)
    assert Decimal(score["score"]) == 90
    assert "NO_SPREAD" in score["quality"]
    evidence["stock"]["observations"] = 19
    assert liquidity_score([holding], evidence)["score"] is None
