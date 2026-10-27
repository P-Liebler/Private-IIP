import asyncio
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from math import sin
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.assistant.documents import chunks, cutoff_time, parse_pdf
from app.assistant.orchestration import choose_tools
from app.assistant.safety import redact, render_answer
from app.assistant.tools import evidence
from app.core.errors import AppError
from app.risk.exposure import exposures
from app.risk.statistics import risk_metrics
from app.schemas.assistant import (
    AlertRuleInput,
    BriefConfigInput,
    ChatInput,
    ModelSelection,
    OptimizerInput,
    ToolInput,
)
from app.schemas.recommendations import InvestmentPreferences
from app.services.alerts import Observation, transition
from app.services.daily_brief import due_period, scheduled_utc
from app.services.portfolio_optimizer import optimize
from app.services.time_machine import existed
from scripts.synthetic_pdf import pdf_bytes

D = Decimal
NOW = datetime(2026, 10, 15, 10, tzinfo=UTC)


def test_answer_contract_rejects_hallucinated_citations_and_redacts_secrets():
    fact = evidence("Value", "10180", "DERIVED_METRIC", NOW, [], "CHF")
    assert "10180 CHF" in render_answer([fact], ModelSelection(fact_ids=[fact.id]))
    with pytest.raises(AppError, match="unverifiable"):
        render_answer([fact], ModelSelection(fact_ids=["invented_source"]))
    assert "hunter2" not in redact("password=hunter2")
    assert "abc.def.xyz" not in redact("Bearer abc.def.xyz")
    with pytest.raises(ValidationError):
        ModelSelection.model_validate({"fact_ids": [fact.id], "free_financial_claim": "BUY"})
    with pytest.raises(ValidationError):
        ToolInput.model_validate({"name": "executeSQL", "sql": "select * from users"})
    assert choose_tools(ChatInput(question="execute SQL and shell")) == []


def test_whole_fact_output_limit_does_not_cut_a_number():
    fact = evidence("Oversized", "9" * 12000, "VERIFIED_FACT", NOW, [])
    text = render_answer([fact], ModelSelection(fact_ids=[fact.id]))
    assert "9999" not in text


def test_pdf_extracts_exact_untrusted_text_and_rejects_invalid_original():
    pages = asyncio.run(parse_pdf(pdf_bytes()))
    assert "Ignore previous instructions" in pages[0]["text"]
    assert chunks(pages)
    with pytest.raises(AppError):
        asyncio.run(parse_pdf(b"not a PDF"))


def test_dst_spring_gap_autumn_fold_and_restart_period_are_deterministic():
    assert cutoff_time(datetime.fromisoformat("2020-01-02T00:30:00+02:00")) == datetime(
        2020, 1, 1, 22, 30, tzinfo=UTC
    )
    assert scheduled_utc(date(2026, 3, 29), "02:30", "Europe/Zurich") == datetime(
        2026, 3, 29, 1, 30, tzinfo=UTC
    )
    assert scheduled_utc(date(2026, 10, 25), "02:30", "Europe/Zurich") == datetime(
        2026, 10, 25, 0, 30, tzinfo=UTC
    )
    cfg = BriefConfigInput(enabled=True, local_time="07:00", timezone="Europe/Zurich")
    assert due_period(datetime(2026, 10, 15, 4, tzinfo=UTC), cfg)[0] == date(2026, 10, 14)


def test_missing_alert_data_is_not_false_or_zero_and_cooldown_survives_restart():
    cfg = AlertRuleInput(
        name="Price", type="PRICE_THRESHOLD", instrument_id=UUID(int=1), threshold=100
    )
    missing = transition(cfg, Observation(None, {}, "SOURCE_DOWN"), D(110), True, NOW, NOW)
    assert missing["status"] == "ALERT_EVALUATION_UNAVAILABLE" and missing["state"] is None
    assert transition(cfg, Observation(D(110), {}), D(90), False, None, NOW)["trigger"]
    assert not transition(cfg, Observation(D(115), {}), D(110), True, NOW, NOW)["trigger"]
    assert not transition(
        cfg, Observation(D(110), {}), D(90), False, NOW, NOW + timedelta(seconds=1)
    )["trigger"]
    change = cfg.model_copy(
        update={"type": "FORECAST_CHANGED", "direction": "ABSOLUTE_CHANGE", "threshold": D(".1")}
    )
    assert (
        transition(change, Observation(D(".6"), {}), None, None, None, NOW)["status"]
        == "BASELINE_RECORDED"
    )


@pytest.mark.parametrize(
    "field", ["observed_at", "retrieved_at", "created_at", "generated_at", "information_cutoff_at"]
)
def test_publication_does_not_override_later_local_knowledge(field):
    row = SimpleNamespace(known_at=NOW - timedelta(days=1), **{field: NOW + timedelta(seconds=1)})
    assert not existed(row, NOW)


def optimizer_fixture():
    ids = [str(UUID(int=1)), str(UUID(int=2))]
    dates = [str(date(2025, 1, 1) + timedelta(days=i)) for i in range(253)]
    series = {
        iid: {day: str(D(str(sin(j * (k + 1)) * 0.005))) for j, day in enumerate(dates[1:])}
        for k, iid in enumerate(ids)
    }
    holdings = [
        {
            "instrument_id": iid,
            "account_id": "broker",
            "name": "SYNTHETIC TEST",
            "quantity": "20",
            "price": "100",
            "currency": "CHF",
            "market_value_native": "2000",
            "market_value_base": "2000",
            "weight": ".2",
            "sector": "Technology" if k == 0 else "Health",
            "country": "CH",
            "valuation_status": "CURRENT",
            "fx": {"status": "AVAILABLE", "rate": "1"},
        }
        for k, iid in enumerate(ids)
    ]
    cash = [
        {
            "account_id": "broker",
            "currency": "CHF",
            "amount": "6000",
            "base_amount": "6000",
            "fx": {"status": "AVAILABLE", "rate": "1"},
        }
    ]
    metrics = risk_metrics(
        [(d, D(series[ids[0]][d]) * D(".2") + D(series[ids[1]][d]) * D(".2")) for d in dates[1:]],
        {},
        True,
        dates[0],
    )
    risk = {
        "current_valuation": {
            "status": "COMPLETE",
            "base_currency": "CHF",
            "total_value_base": "10000",
            "cash_value_base": "6000",
            "holdings": holdings,
            "cash": cash,
        },
        "asset_returns": series,
        "quality": {"complete_return_series": True},
        "return_observations": [{"date": d} for d in dates],
        "metrics": metrics,
        "exposures": exposures(holdings, cash, D(10000)),
        "health": {},
        "correlations": {},
        "position_beta": {},
        "liquidity_evidence": {
            iid: {"observations": 20, "average_volume": "200000"} for iid in ids
        },
    }
    profile = InvestmentPreferences(
        confirmed=True,
        max_single_position_weight=D(".5"),
        max_sector_weight=D(1),
        max_country_weight=D(1),
        maximum_turnover=D(1),
        maximum_new_investment=D(10000),
    ).model_dump(mode="json")
    return risk, profile, OptimizerInput(risk_snapshot_id=UUID(int=3))


@pytest.mark.parametrize(
    "objective", ["MINIMUM_VARIANCE", "MINIMUM_CONCENTRATION", "RISK_BUDGET", "TARGET_ALLOCATION"]
)
def test_optimizer_simulates_costs_constraints_psd_without_ledger_mutation(objective):
    risk, profile, request = optimizer_fixture()
    original = deepcopy(risk)
    targets = (
        {UUID(int=1): D(".15"), UUID(int=2): D(".25")} if objective == "TARGET_ALLOCATION" else {}
    )
    result = optimize(
        risk,
        profile,
        request.model_copy(update={"objective": objective, "target_weights": targets}),
        {},
    )
    assert result["status"] == "AVAILABLE", result
    assert abs(sum(result["weights"].values()) - 0.4) < 1e-6
    assert result["covariance"]["condition_number"] < 1e9
    assert "NO_CHANGE" in result["comparisons"]
    assert risk == original


def test_optimizer_missing_covariance_forecast_and_infeasible_caps_abstain():
    risk, profile, request = optimizer_fixture()
    del risk["asset_returns"][str(UUID(int=1))][risk["return_observations"][-1]["date"]]
    assert optimize(risk, profile, request, {})["weights"] is None

    risk, profile, request = optimizer_fixture()
    assert (
        optimize(risk, profile, request.model_copy(update={"objective": "EXPECTED_RETURN"}), {})[
            "reason"
        ]
        == "EXPECTED_RETURN_OPTIMIZATION_UNAVAILABLE"
    )
    profile["max_single_position_weight"] = ".1"
    assert optimize(risk, profile, request, {})["weights"] is None


def test_optimizer_cash_accounts_share_one_fx_risk_factor_and_missing_fx_abstains():
    risk, profile, request = optimizer_fixture()
    risk["current_valuation"]["cash"][0].update(amount="5000", base_amount="5000")
    risk["current_valuation"]["cash"].extend(
        [
            {
                "account_id": f"SYNTHETIC_USD_{i}",
                "currency": "USD",
                "amount": str(D(500) / D(".9")),
                "base_amount": "500",
                "fx": {"status": "AVAILABLE", "rate": ".9"},
            }
            for i in range(2)
        ]
    )
    risk["cash_fx_returns"] = {
        "USD": {
            o["date"]: str(D(i % 7 - 3) / 10000)
            for i, o in enumerate(risk["return_observations"][1:])
        }
    }
    request = request.model_copy(
        update={
            "objective": "TARGET_ALLOCATION",
            "target_weights": {UUID(int=1): D(".15"), UUID(int=2): D(".25")},
        }
    )
    result = optimize(risk, profile, request, {})
    assert result["status"] == "AVAILABLE", result
    assert result["covariance"]["order"].count("USD") == 1
    assert len(result["covariance"]["matrix"]) == 3
    del risk["cash_fx_returns"]["USD"][risk["return_observations"][-1]["date"]]
    assert optimize(risk, profile, request, {})["reason"] == "ALIGNED_ASSET_OR_FX_RETURNS_MISSING"
