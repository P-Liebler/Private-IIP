from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from statistics import stdev

import pytest

from app.core.errors import AppError
from app.risk.exposure import exposures, health
from app.risk.scenarios import SCENARIOS, scenario
from app.risk.statistics import correlations, historical_var, risk_metrics
from app.risk.whatif import hypothetical
from app.schemas.risk import ScenarioInput, WhatIfInput

D = Decimal


def golden_risk():
    holding = {
        "instrument_id": "stock",
        "account_id": "broker",
        "quantity": "10",
        "currency": "USD",
        "price": "120",
        "market_value_native": "1200",
        "market_value_base": "1080",
        "valuation_status": "CURRENT",
        "sector": "Technology",
        "country": "US",
        "industry": "Software",
        "fx": {"status": "AVAILABLE", "rate": ".9"},
    }
    cash = [
        {
            "account_id": "broker",
            "currency": "CHF",
            "amount": "10000",
            "base_amount": "10000",
            "fx": {"status": "AVAILABLE", "rate": "1"},
        },
        {
            "account_id": "broker",
            "currency": "USD",
            "amount": "-1000",
            "base_amount": "-900",
            "fx": {"status": "AVAILABLE", "rate": ".9"},
        },
    ]
    metrics = risk_metrics([], {}, False)
    exposure = exposures([holding], cash, D(10180))
    return {
        "current_valuation": {
            "status": "COMPLETE",
            "base_currency": "CHF",
            "total_value_base": "10180",
            "holdings": [holding],
            "cash": cash,
        },
        "metrics": metrics,
        "exposures": exposure,
        "health": health(exposure, metrics, base_currency="CHF"),
        "correlations": {},
        "position_beta": {},
        "benchmark": None,
        "return_observations": [],
        "asset_returns": {},
    }


def test_volatility_beta_dates_and_missing_gate():
    returns = [
        (str(date(2024, 1, 2) + timedelta(days=i)), D(i % 11 - 5) / 1000) for i in range(252)
    ]
    benchmark = {day: r / 2 for day, r in returns}
    result = risk_metrics(returns, benchmark, True, "2024-01-01")
    assert D(result["annualized_volatility"]) == stdev([r for _, r in returns]) * D(252).sqrt()
    assert abs(D(result["beta"]) - 2) < D("1e-24")
    assert result["beta_observations"] == 252
    missing = risk_metrics(returns, benchmark, False)
    assert missing["annualized_volatility"] is None and missing["maximum_drawdown"] is None
    short = risk_metrics(returns[:19], {}, True)
    assert short["annualized_volatility"] is None and short["beta"] is None
    assert risk_metrics(returns, {day: D(0) for day, _ in returns}, True)["beta"] is None


def test_max_drawdown_initial_peak_and_var_tail_golden():
    result = risk_metrics(
        [("2025-01-02", D("-.1")), ("2025-01-03", D("-.2")), ("2025-01-06", D(".5"))],
        {},
        True,
        "2025-01-01",
    )
    assert D(result["maximum_drawdown"]) == D("-.28")
    assert (result["peak_date"], result["trough_date"]) == ("2025-01-01", "2025-01-03")
    values = [D(i) / 1000 for i in range(-126, 126)]
    var = historical_var(values)
    assert D(var["var"]) == D(".11345")
    assert D(var["cvar"]) == D(".120") and var["tail_sample_size"] == 13
    assert historical_var(values[:251])["var"] is None


def test_correlations_exact_window_constant_and_gap():
    dates = [str(date(2025, 1, 1) + timedelta(days=i)) for i in range(40)]
    left = {day: D(i) / 1000 for i, day in enumerate(dates)}
    right = {day: -v for day, v in left.items()}
    result = correlations({"a": left, "b": right}, 30, dates)
    pair = next(c for c in result["cells"] if c["left"] == "a" and c["right"] == "b")
    assert abs(D(pair["value"]) + 1) < D("1e-25")
    del right[dates[-5]]
    assert all(c["value"] is None for c in correlations({"b": right}, 30, dates)["cells"])
    assert correlations({"a": {d: D(0) for d in dates}}, 30, dates)["cells"][0]["value"] is None


def test_concentration_group_unknown_cash_and_health():
    risk = golden_risk()
    h = risk["current_valuation"]["holdings"][0]
    copy = deepcopy(h)
    copy["account_id"], copy["sector"] = "second", None
    result = exposures([h, copy], risk["current_valuation"]["cash"], D(11260))
    assert D(result["positions"]["stock"]["value_base"]) == 2160
    assert D(result["concentration"]["hhi"]) == (D(2160) / 11260) ** 2
    assert "UNKNOWN" in result["groups"]["sector"]
    assert health(result, risk["metrics"], {"score": "80"}, "CHF")["overall_score"] is None
    unavailable = exposures([{**h, "market_value_base": None}], [], None)
    assert unavailable["concentration"] is None


def test_currency_stress_nets_negative_cash_once():
    risk = golden_risk()
    result = scenario(risk, dict(SCENARIOS[4][2]))
    assert D(result["impact_base"]) == -18
    assert D(result["stressed_value_base"]) == 10162
    assert len(result["position_impacts"]) == 2
    assert scenario(risk, {**SCENARIOS[4][2], "quote_currency": "EUR"})["impact_base"] is None


def test_beta_sector_gaps_and_volatility_have_no_fake_loss():
    risk = golden_risk()
    assert scenario(risk, SCENARIOS[0][2])["impact_base"] is None
    risk["benchmark"] = {"benchmark_id": "b"}
    result = scenario(
        risk, {**SCENARIOS[0][2], "benchmark_id": "b", "benchmark_mapping_confirmed": True}
    )
    assert result["status"] == "PARTIAL" and result["impact_base"] is None
    risk["position_beta"]["stock"] = {
        "status": "AVAILABLE",
        "beta_status": "AVAILABLE",
        "beta": "1.5",
    }
    assert (
        D(
            scenario(
                risk, {**SCENARIOS[0][2], "benchmark_id": "b", "benchmark_mapping_confirmed": True}
            )["impact_base"]
        )
        == -162
    )
    risk["current_valuation"]["holdings"][0]["sector"] = None
    assert scenario(risk, SCENARIOS[3][2])["status"] == "PARTIAL"
    risk["metrics"]["annualized_volatility"] = ".2"
    stressed = scenario(risk, SCENARIOS[6][2])
    assert stressed["impact_base"] is None and D(stressed["stressed_annualized_volatility"]) == D(
        ".4"
    )


def test_whatif_buy_sell_costs_and_original_immutable():
    risk = golden_risk()
    original = deepcopy(risk)
    quote = risk["current_valuation"]["holdings"][0]
    config = {
        "trades": [{"instrument_id": "stock", "side": "BUY", "amount_base": "100"}],
        "commission_base": "1",
        "spread_bps": "5",
        "slippage_bps": "5",
    }
    result = hypothetical(risk, config, {"stock": quote})
    assert D(result["costs_base"]) == D("1.1")
    assert D(result["current_valuation"]["total_value_base"]) == D("10178.9")
    assert D(result["current_valuation"]["holdings"][0]["market_value_base"]) == 1180
    assert D(result["current_valuation"]["cash_value_base"]) + D(
        result["current_valuation"]["securities_value_base"]
    ) == D(result["current_valuation"]["total_value_base"])
    assert risk == original and result["metrics"]["beta"] is None
    config["trades"] = [{"instrument_id": "stock", "side": "SELL", "sell_fraction": ".1"}]
    sold = hypothetical(risk, config, {"stock": quote})
    assert D(sold["current_valuation"]["holdings"][0]["quantity"]) == 9
    assert D(sold["current_valuation"]["total_value_base"]) == D("10178.892")
    assert risk == original


def test_whatif_matched_json_history_recomputes_beta_without_double_fx():
    risk = golden_risk()
    dates = [str(date(2025, 1, 1) + timedelta(days=i)) for i in range(61)]
    risk["return_observations"] = [{"date": d} for d in dates]
    risk["asset_returns"] = {
        "stock": {d: str(D(i % 5 - 2) / 1000) for i, d in enumerate(dates[1:])},
        "benchmark": {d: str(D(i % 5 - 2) / 2000) for i, d in enumerate(dates[1:])},
    }
    risk["benchmark"] = {"benchmark_id": "b", "instrument_id": "benchmark"}
    risk["cash_fx_returns"] = {"USD": {d: "0" for d in dates[1:]}}
    config = {
        "trades": [{"instrument_id": "stock", "side": "BUY", "amount_base": "100"}],
        "commission_base": "1",
        "spread_bps": "5",
        "slippage_bps": "5",
    }
    result = hypothetical(risk, config, {"stock": risk["current_valuation"]["holdings"][0]})
    assert result["metrics"]["status"] == "AVAILABLE"
    expected_beta = D(2) * D(1180) / D("10178.9")
    assert abs(D(result["metrics"]["beta"]) - expected_beta) < D("1e-24")
    assert abs(D(result["position_beta"]["stock"]["beta"]) - 2) < D("1e-24")
    assert result["correlations"]["30"]["cells"][0]["status"] == "AVAILABLE"
    invalid = risk_metrics([(d, D("-1.1")) for d in dates[1:]], {}, True)
    assert invalid["annualized_volatility"] is None and invalid["maximum_drawdown"] is None


def test_whatif_insufficient_cash_missing_quotes_and_validation():
    risk = golden_risk()
    config = {
        "trades": [{"instrument_id": "stock", "side": "BUY", "amount_base": "10001"}],
        "commission_base": "1",
        "spread_bps": "5",
        "slippage_bps": "5",
    }
    with pytest.raises(AppError, match="cash"):
        hypothetical(risk, config, {"stock": risk["current_valuation"]["holdings"][0]})
    with pytest.raises(AppError):
        hypothetical(risk, config, {})
    with pytest.raises(ValueError):
        ScenarioInput(risk_snapshot_id="00000000-0000-0000-0000-000000000001")
    with pytest.raises(ValueError):
        WhatIfInput(
            risk_snapshot_id="00000000-0000-0000-0000-000000000001",
            trades=[
                {
                    "instrument_id": "00000000-0000-0000-0000-000000000002",
                    "side": "SELL",
                    "sell_fraction": "1.1",
                }
            ],
        )
