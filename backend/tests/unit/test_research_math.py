from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models import FundamentalFact
from app.providers.company_ir import ReportContract, parse_report_csv
from app.providers.news_rss import parse_rss
from app.schemas.research import FactInput
from app.services.fundamental_metrics import FundamentalMetricsService, valuation
from app.services.news import UnavailableSentiment, normalized_url
from app.services.research_scores import calculate_scores


def fact(
    metric: str,
    value: str,
    *,
    year: int = 2025,
    currency: str = "CHF",
    start: date | None = None,
    end: date | None = None,
    kind: str = "ANNUAL",
) -> FundamentalFact:
    instant = metric in {
        "cash",
        "total_assets",
        "total_debt",
        "total_equity",
        "current_assets",
        "current_liabilities",
        "inventory",
        "shares_outstanding",
        "preferred_equity",
        "minority_interest",
    }
    return FundamentalFact(
        id=uuid4(),
        instrument_id=uuid4(),
        source_id=uuid4(),
        raw_ingestion_id=uuid4(),
        metric=metric,
        value=Decimal(value),
        unit="SHARES" if metric == "shares_outstanding" else "MONEY",
        currency=None if metric == "shares_outstanding" else currency,
        period_start=None if instant else start or date(year, 1, 1),
        period_end=end or date(year, 12, 31),
        period_type="INSTANT" if instant else kind,
        known_at=datetime(2026, 3, 1, tzinfo=UTC),
        observed_at=datetime(2026, 3, 1, tzinfo=UTC),
        retrieved_at=datetime(2026, 3, 1, tzinfo=UTC),
        validation_status="VALID",
        evidence={},
    )


def test_metrics_golden_and_negative_income() -> None:
    rows = [
        fact(k, v)
        for k, v in {
            "revenue": "1000",
            "gross_profit": "400",
            "operating_income": "150",
            "net_income": "-50",
            "operating_cash_flow": "200",
            "capex": "50",
            "total_debt": "200",
            "cash": "100",
            "total_equity": "400",
            "total_assets": "800",
            "income_tax": "20",
            "pretax_income": "100",
            "current_assets": "250",
            "current_liabilities": "100",
            "inventory": "50",
        }.items()
    ]
    metrics = FundamentalMetricsService(rows).calculate()
    assert Decimal(metrics["gross_margin"]["value"]) == Decimal("0.4")
    assert Decimal(metrics["operating_margin"]["value"]) == Decimal("0.15")
    assert Decimal(metrics["net_margin"]["value"]) == Decimal("-0.05")
    assert Decimal(metrics["free_cash_flow"]["value"]) == 150
    assert Decimal(metrics["ROE"]["value"]) == Decimal("-0.125")
    assert Decimal(metrics["ROIC"]["value"]) == Decimal("0.24")
    assert Decimal(metrics["debt_to_equity"]["value"]) == Decimal("0.5")
    assert Decimal(metrics["quick_ratio"]["value"]) == 2
    assert metrics["ROIC"]["inputs"]


@pytest.mark.parametrize(
    "rows",
    [
        [fact("revenue", "0"), fact("gross_profit", "1")],
        [fact("gross_profit", "1")],
        [fact("revenue", "10", year=2024), fact("gross_profit", "1")],
        [fact("revenue", "10", currency="EUR"), fact("gross_profit", "1")],
    ],
)
def test_invalid_ratio_never_neutral(rows: list[FundamentalFact]) -> None:
    assert FundamentalMetricsService(rows).calculate()["gross_margin"]["value"] is None


def test_growth_requires_positive_comparable_base() -> None:
    engine = FundamentalMetricsService([fact("revenue", "120"), fact("revenue", "100", year=2024)])
    assert Decimal(engine.growth("revenue", "ANNUAL")["value"]) == Decimal("0.2")
    assert (
        FundamentalMetricsService(
            [fact("revenue", "120"), fact("revenue", "-100", year=2024)]
        ).growth("revenue", "ANNUAL")["value"]
        is None
    )


def test_ttm_excludes_ytd_and_gaps() -> None:
    rows = [
        fact("revenue", "100", start=s, end=e, kind="QUARTER")
        for s, e in [
            (date(2025, 1, 1), date(2025, 3, 31)),
            (date(2025, 4, 1), date(2025, 6, 30)),
            (date(2025, 7, 1), date(2025, 9, 30)),
            (date(2025, 10, 1), date(2025, 12, 31)),
        ]
    ]
    assert Decimal(FundamentalMetricsService(rows).ttm("revenue")["value"]) == 400
    rows[1].period_type = "YTD"
    assert FundamentalMetricsService(rows).ttm("revenue")["value"] is None


def test_valuation_verified_share_basis_ev_and_negative_pe() -> None:
    identifier = str(uuid4())
    day = date(2026, 3, 2)
    shares = fact("shares_outstanding", "10")
    shares.evidence = {"share_class": identifier, "split_basis_date": str(day)}
    rows = [
        shares,
        *[
            fact(k, v)
            for k, v in {
                "revenue": "1000",
                "net_income": "100",
                "free_cash_flow": "80",
                "total_equity": "400",
                "total_debt": "200",
                "cash": "100",
                "preferred_equity": "0",
                "minority_interest": "0",
                "ebitda": "150",
            }.items()
        ],
    ]
    price = {"id": uuid4(), "date": day, "close": "50", "currency": "CHF"}
    result = valuation(rows, price, day, identifier)
    assert Decimal(result["market_cap"]["value"]) == 500
    assert Decimal(result["P/E"]["value"]) == 5
    assert Decimal(result["P/S"]["value"]) == Decimal("0.5")
    assert Decimal(result["P/B"]["value"]) == Decimal("1.25")
    assert Decimal(result["EV/EBITDA"]["value"]) == 4
    assert Decimal(result["FCF Yield"]["value"]) == Decimal("0.16")
    rows[2].value = Decimal(-100)
    assert valuation(rows, price, day, identifier)["P/E"]["value"] is None
    assert valuation(rows[1:], price, day, identifier)["market_cap"]["value"] is None
    assert (
        valuation([f for f in rows if f.metric != "cash"], price, day, identifier)[
            "enterprise_value"
        ]["value"]
        is None
    )


def test_scores_deterministic_missing_critical_and_rule_version() -> None:
    inputs = {
        key: {"value": "0.2", "status": "AVAILABLE", "inputs": []}
        for key in ["ROIC", "fcf_margin", "debt_to_equity"]
    }
    first = calculate_scores(inputs, "2026-03-02")
    assert first == calculate_scores(inputs, "2026-03-02")
    assert first["Quality"]["score"] is not None
    assert first["Value"]["score"] is None
    assert first["Quality"]["method"].startswith("Absolute")
    assert calculate_scores(inputs, "2026-03-02", "v2")["Quality"]["rule_version"] == "v2"
    inputs["ROIC"]["value"] = "1000000"
    assert 0 <= Decimal(calculate_scores(inputs, "2026-03-02")["Quality"]["score"]) <= 100
    del inputs["ROIC"]
    assert calculate_scores(inputs, "2026-03-02")["Quality"]["score"] is None


def test_manual_swiss_reporting_contract_and_hard_validation() -> None:
    identifier = uuid4()
    data = (
        b"metric,value,unit,currency,period_start,period_end,period_type,filing_reference\n"
        b"revenue,1000,MONEY,CHF,2025-01-01,2025-12-31,ANNUAL,SYNTHETIC-CH-REPORT\n"
    )
    parsed = parse_report_csv(
        data,
        ReportContract(
            instrument_id=identifier,
            url="https://example.org/report.csv",
            approved_host="example.org",
        ),
    )
    assert parsed[0].value == 1000 and parsed[0].currency == "CHF" and parsed[0].known_at is None
    with pytest.raises(ValidationError):
        FactInput.model_validate({**parsed[0].model_dump(), "value": "NaN"})
    with pytest.raises(ValidationError):
        FactInput.model_validate({**parsed[0].model_dump(), "unit": "SHARES"})


def test_news_contract_url_and_missing_sentiment() -> None:
    assert (
        normalized_url("https://Example.org/story?utm_source=rss#top")
        == "https://example.org/story"
    )
    assert UnavailableSentiment().analyze("Results", "de") is None
    assert (
        parse_rss(
            b"<rss><channel><item><title>Results</title><link>https://example.org/results</link></item></channel></rss>"
        )[0].title
        == "Results"
    )
    with pytest.raises(ValueError):
        parse_rss(b'<!DOCTYPE rss [<!ENTITY x "a">]><rss/>')


def test_derived_fcf_growth_yield_and_definition_conflict() -> None:
    rows = [
        fact("operating_cash_flow", "150"),
        fact("capex", "50"),
        fact("operating_cash_flow", "125", year=2024),
        fact("capex", "50", year=2024),
        fact("revenue", "1000"),
    ]
    result = FundamentalMetricsService(rows).calculate()
    assert Decimal(result["free_cash_flow"]["value"]) == 100
    assert abs(Decimal(result["fcf_growth_yoy"]["value"]) - Decimal(1) / 3) < Decimal("1e-25")
    assert Decimal(result["fcf_margin"]["value"]) == Decimal("0.1")
    shares = fact("shares_outstanding", "10")
    day = date(2026, 3, 2)
    identifier = str(uuid4())
    shares.evidence = {"share_class": identifier, "split_basis_date": str(day)}
    result = valuation(
        [*rows, shares],
        {"id": uuid4(), "date": day, "close": "50", "currency": "CHF"},
        day,
        identifier,
    )
    assert Decimal(result["FCF Yield"]["value"]) == Decimal("0.2")
    rows.append(fact("free_cash_flow", "999"))
    conflict = FundamentalMetricsService(rows).calculate()
    assert conflict["free_cash_flow"]["value"] is None
    assert conflict["fcf_margin"]["value"] is None
