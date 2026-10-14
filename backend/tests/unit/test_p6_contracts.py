from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.backtesting.baselines import no_skill, ranking, train_only_baselines
from app.backtesting.features import ema, technical_features
from app.backtesting.validation import (
    LabelInterval,
    WalkForwardSplitter,
    available,
    validate_execution,
)
from app.services.market_calendar import MarketCalendarService
from app.services.pit_features import FeatureSnapshotService

D = Decimal


@pytest.mark.parametrize("exchange", ["NYSE", "NASDAQ", "SIX"])
def test_offline_calendar_sessions_and_horizons(exchange: str) -> None:
    c = MarketCalendarService()
    day = date(2024, 3, 8)
    assert c.next_session(exchange, day) == date(2024, 3, 11)
    assert not c.is_session(exchange, date(2024, 3, 9))
    for n in (30, 90):
        end = c.horizon(exchange, day, n)
        assert len(c.sessions_between(exchange, c.next_session(exchange, day), end)) == n


def test_us_holiday_early_close_dst_emergency_closure() -> None:
    c = MarketCalendarService()
    assert not c.is_session("NYSE", date(2024, 7, 4))
    assert c.session_close("NYSE", date(2024, 11, 29)).hour == 18
    assert c.session_open("NYSE", date(2024, 3, 8)).hour == 14
    assert c.session_open("NYSE", date(2024, 3, 11)).hour == 13
    assert not c.is_session("NYSE", date(2012, 10, 29))


def test_evidence_is_not_a_backdated_assertion() -> None:
    historical = datetime(2024, 1, 1, tzinfo=UTC)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert not available("STRICT_PIT", historical, historical, now, "USER_ASSERTED")
    assert not available("STRICT_PIT", historical, historical, historical, "UNVERIFIED")
    assert available(
        "STRICT_PIT", historical, historical, historical, "VERIFIED_PUBLIC_TIMESTAMP", historical
    )
    assert not available(
        "STRICT_PIT", historical, historical, historical, "VERIFIED_PUBLIC_TIMESTAMP", now
    )


def test_same_close_rejected_next_open_allowed() -> None:
    cutoff = datetime(2024, 1, 2, 21, tzinfo=UTC)
    signal = cutoff + timedelta(seconds=1)
    open_at = datetime(2024, 1, 3, 14, 30, tzinfo=UTC)
    with pytest.raises(ValueError, match="TIME_REJECTED"):
        validate_execution(signal, cutoff, open_at, cutoff, D(100), True)
    validate_execution(signal, cutoff, open_at, open_at, D(100), True)
    with pytest.raises(ValueError, match="UNAVAILABLE"):
        validate_execution(signal, cutoff, open_at, open_at, None, True)


def test_technical_independent_reference_and_missing_windows() -> None:
    prices = [
        {
            "id": str(i),
            "date": str(i),
            "close": str(i + 1),
            "high": str(i + 2),
            "low": str(i),
            "volume": str(i + 10),
        }
        for i in range(253)
    ]
    x = [D(i + 1) for i in range(253)]
    dates = [str(i) for i in range(253)]
    r = technical_features(prices, x, dates)
    assert D(r["return_1d"]["value"]) == D(253) / 252 - 1
    assert D(r["return_252d"]["value"]) == 252
    assert D(r["SMA20"]["value"]) == D("243.5")
    assert D(r["SMA50"]["value"]) == D("228.5")
    assert D(r["SMA200"]["value"]) == D("153.5")
    assert D(r["RSI"]["value"]) == 100
    assert abs(D(r["MACD"]["value"]) - 7) < D("1e-24")
    assert D(r["ATR"]["value"]) == 2
    assert D(r["max_drawdown"]["value"]) == 0
    assert D(r["volume_change"]["value"]) == D(262) / 261 - 1
    assert ema([D(1), D(2), D(3), D(4)], 3) == [D(2), D(3)]
    assert technical_features(prices[:-1], x[:-1], dates)["SMA20"]["reason"] == "MISSING_SESSION"
    assert technical_features(prices, None, dates)["return_1d"]["missing_flag"]
    assert technical_features(prices[:2], x[:2], ["0", "1"])["SMA20"]["missing_flag"]


def test_split_dividend_no_adjusted_close_double_count() -> None:
    prices = [
        {"close": "100", "date": "2024-01-01", "currency": "USD"},
        {"close": "50", "date": "2024-01-02", "currency": "USD"},
        {"close": "49", "date": "2024-01-03", "currency": "USD"},
    ]
    actions = [
        {"date": "2024-01-02", "type": "SPLIT", "ratio": "2"},
        {"date": "2024-01-03", "type": "DIVIDEND", "cash_amount": "1", "currency": "USD"},
    ]
    assert FeatureSnapshotService.total_return(prices, actions) == [D(100), D(100), D(100)]
    prices[-1]["currency"] = "CHF"
    assert FeatureSnapshotService.total_return(prices, actions) is None


@pytest.mark.parametrize("horizon", [30, 90])
def test_purging_labels_conservative_embargo(horizon: int) -> None:
    c = MarketCalendarService()
    validation = datetime(2025, 1, 2, 21, tzinfo=UTC)
    test = datetime(2025, 6, 2, 21, tzinfo=UTC)
    final = datetime(2026, 1, 2, 21, tzinfo=UTC)
    day = validation.date()
    for _ in range(horizon):
        day = c.previous_session("NYSE", day)
    embargo = c.session_close("NYSE", day)
    rows = [
        LabelInterval(
            "safe",
            embargo - timedelta(days=200),
            embargo - timedelta(days=199),
            embargo - timedelta(days=1),
            embargo - timedelta(days=1),
        ),
        LabelInterval(
            "overlap",
            embargo - timedelta(days=1),
            embargo,
            validation + timedelta(days=1),
            validation + timedelta(days=1),
        ),
    ]
    r = WalkForwardSplitter().split(rows, validation, test, final, embargo, horizon, horizon)
    assert r["training"] == ["safe"] and r["purged"] == ["overlap"]
    with pytest.raises(ValueError):
        WalkForwardSplitter().split(rows, validation, test, final, embargo, horizon - 1, horizon)


def test_baselines_train_only_missing_factor() -> None:
    assert no_skill() == D("0.5")
    cutoff = datetime(2024, 1, 1, tzinfo=UTC)
    rows = [
        {
            "partition": "training",
            "label_available_at": cutoff.isoformat(),
            "label": 1,
            "excess_return": "0.2",
        },
        {
            "partition": "training",
            "label_available_at": cutoff.isoformat(),
            "label": 0,
            "excess_return": "-0.1",
        },
    ]
    r = train_only_baselines(rows, cutoff)
    assert D(r["prevalence"]) == D("0.5") and D(r["historical_mean"]) == D("0.05")
    rows[0]["partition"] = "test"
    with pytest.raises(ValueError, match="LEAKAGE"):
        train_only_baselines(rows, cutoff)
    assert ranking([{"instrument_id": "a", "features": {}}], "MOMENTUM", 5) == []
