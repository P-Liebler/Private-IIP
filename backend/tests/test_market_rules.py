from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.core.errors import AppError
from app.providers.ecb_fx import parse_ecb_csv
from app.services.market_queries import total_return
from app.services.market_validation import validate_action, validate_fx, validate_price


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"close": "0"}, "positiv"),
        ({"high": "9", "low": "10"}, "High"),
        ({"high": "9", "open": "10"}, "High"),
        ({"low": "11", "close": "10"}, "Low"),
        ({"volume": "-1"}, "positiv"),
        ({"currency": "EUR"}, "Kurswährung"),
        ({"date": "2099-01-01"}, "Zukunft"),
    ],
)
def test_hard_price_gate(overrides: dict[str, str], expected: str) -> None:
    row = {"date": "2024-01-02", "open": "10", "high": "11", "low": "9", "close": "10", "volume": "1", "currency": "USD"}
    row.update(overrides)
    with pytest.raises(ValueError, match=expected):
        validate_price(row, "USD")


def test_adjusted_close_is_only_plausibility_input() -> None:
    row, warnings = validate_price(
        {"date": "2024-01-02", "close": "100", "adjusted_close": "40"}, "USD"
    )
    assert row["close"] == Decimal("100")
    assert row["adjusted_close"] == Decimal("40")
    assert any("ADJUSTED_CLOSE_DIFFERS" in warning for warning in warnings)
    assert total_return(Decimal("100"), Decimal("110"), []) == Decimal("0.1")


@pytest.mark.parametrize(
    ("start", "end", "actions", "expected"),
    [
        ("100", "110", [], "0.1"),
        ("100", "98", [{"date": date(2024, 1, 3), "type": "DIVIDEND", "value": Decimal("2")}], "0"),
        ("100", "50", [{"date": date(2024, 1, 3), "type": "SPLIT", "value": Decimal("2")}], "0"),
        ("100", "49", [{"date": date(2024, 1, 3), "type": "SPLIT", "value": Decimal("2")}, {"date": date(2024, 1, 3), "type": "DIVIDEND", "value": Decimal("1")}], "0"),
        ("100", "200", [{"date": date(2024, 1, 3), "type": "REVERSE_SPLIT", "value": Decimal("0.5")}], "0"),
    ],
)
def test_total_return_golden(start: str, end: str, actions: list[dict[str, object]], expected: str) -> None:
    assert total_return(Decimal(start), Decimal(end), actions) == Decimal(expected)


def test_action_and_fx_validation() -> None:
    split = validate_action({"date": "2024-01-03", "action_type": "SPLIT", "ratio": "2"}, "USD")
    assert split["ratio"] == Decimal(2)
    dividend = validate_action({"date": "2024-01-03", "action_type": "DIVIDEND", "cash_amount": "0", "currency": "USD"}, "USD")
    assert dividend["cash_amount"] == 0
    with pytest.raises(ValueError):
        validate_action({"date": "2024-01-03", "action_type": "DIVIDEND", "cash_amount": "1", "currency": "EUR"}, "USD")
    with pytest.raises(ValueError):
        validate_action({"date": "2024-01-03", "action_type": "REVERSE_SPLIT", "ratio": "2"}, "USD")
    assert validate_fx({"date": "2024-01-02", "base_currency": "USD", "quote_currency": "CHF", "rate": "0.9"})["rate"] == Decimal("0.9")
    with pytest.raises(ValueError):
        validate_fx({"date": "2024-01-02", "base_currency": "USD", "quote_currency": "USD", "rate": "1"})
    with pytest.raises(ValueError):
        validate_fx({"date": "2024-01-02", "base_currency": "USD", "quote_currency": "CHF", "rate": "0"})


def test_ecb_csv_parser_fails_closed() -> None:
    header = b"FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE\n"
    parsed = parse_ecb_csv(header + b"D,CHF,EUR,SP00,A,2024-01-02,0.9\n")
    assert parsed[0]["base_currency"] == "EUR" and parsed[0]["quote_currency"] == "CHF"
    with pytest.raises(AppError) as invalid:
        parse_ecb_csv(header + b"D,CHF,USD,SP00,A,2024-01-02,0.9\n")
    assert invalid.value.code == "SOURCE_RESPONSE_INVALID"
