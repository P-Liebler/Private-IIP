import asyncio
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.models import ActionCoverageReview, Instrument
from app.schemas.pit import DatasetInput
from app.services.market_calendar import MarketCalendarService
from app.services.pit_datasets import DatasetBuilder


@pytest.mark.parametrize("horizon", [30, 90])
def test_target_exact_session_horizon_independent_returns_and_availability(horizon: int) -> None:
    async def run() -> None:
        calendar = MarketCalendarService()
        signal_day = date(2024, 1, 2)
        end = calendar.horizon("NYSE", signal_day, horizon)
        sessions = calendar.sessions_between("NYSE", calendar.next_session("NYSE", signal_day), end)
        instrument_id, benchmark_id, coverage_id = uuid4(), uuid4(), uuid4()
        observed = calendar.session_close("NYSE", end) + timedelta(seconds=5)
        reviewed = observed + timedelta(seconds=55)

        async def get(model: object, key: object) -> object:
            if model is Instrument:
                return SimpleNamespace(exchange="NYSE", currency="USD")
            if model is ActionCoverageReview:
                return SimpleNamespace(created_at=reviewed)
            raise AssertionError("No extra unpinned target inputs")

        db = SimpleNamespace(get=AsyncMock(side_effect=get))
        builder = DatasetBuilder(db)

        async def prices(iid: UUID, *args: object) -> list[dict]:
            return [
                {
                    "id": str(uuid4()),
                    "date": day.isoformat(),
                    "open": "100",
                    "close": "110" if iid == instrument_id and day == end else "100",
                    "currency": "USD",
                    "known_at": observed.isoformat(),
                    "observed_at": observed.isoformat(),
                }
                for day in sessions
            ]

        builder.features = SimpleNamespace(
            prices=AsyncMock(side_effect=prices),
            actions=AsyncMock(return_value=([], str(coverage_id))),
            total_return=lambda values, _: [Decimal(v["close"]) for v in values],
        )
        config = DatasetInput(
            universe_id=uuid4(),
            benchmark_id=benchmark_id,
            start=signal_day,
            end=end,
            target_horizon=horizon,
            base_currency="USD",
        )
        target = await builder.target(
            instrument_id,
            benchmark_id,
            signal_day,
            calendar.session_close("NYSE", signal_day),
            config,
        )
        assert target["status"] == "AVAILABLE"
        assert target["classification"] == 1
        assert Decimal(target["excess_return"]) == Decimal("0.1")
        assert target["label_end"] == calendar.session_close("NYSE", end).isoformat()
        assert target["label_available_at"] == reviewed.isoformat()
        assert len(target["input_versions"]["price"]) == 2 * horizon
        assert target["volatility_status"] == "AVAILABLE"
        # Exactly one +10% return among N observations: sample std = .1/sqrt(N).
        expected = Decimal("0.1") / Decimal(horizon).sqrt() * Decimal(252).sqrt()
        assert abs(Decimal(target["realized_volatility"]) - expected) < Decimal("1e-24")

    asyncio.run(run())
