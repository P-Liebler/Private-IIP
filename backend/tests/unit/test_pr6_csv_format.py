import asyncio
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.services.portfolio_import import parse_rows, plan_hash
from app.services.transaction_csv_format import (
    TransactionCsvFormat,
    detect_format,
    normalize_cell,
)


def test_bom_and_semicolon_are_detected_without_changing_original():
    original = b"\xef\xbb\xbftype;date;currency;amount\nDEPOSIT;2026-10-23;CHF;1234.50\n"
    config = detect_format(original)
    assert config == TransactionCsvFormat(delimiter=";", date_format="ISO", number_format="POINT")
    assert original.startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize("value", ["01/02/2026", "01.02.2026", "1'234.50", "1234,50"])
def test_ambiguous_formats_require_explicit_selection(value):
    assert detect_format(f"type;date;currency;amount\nDEPOSIT;{value};CHF;1\n".encode()) is None


def test_format_changes_are_bound_to_preview_hash_and_legacy_hash_is_stable():
    import hashlib
    import json

    mapping = {"value": "amount"}
    legacy = hashlib.sha256(
        json.dumps(
            {"mapping": mapping, "resolutions": {}}, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    assert plan_hash(mapping, {}) == legacy
    ch = TransactionCsvFormat(delimiter=";", date_format="DMY", number_format="CH")
    comma = ch.model_copy(update={"number_format": "COMMA"})
    assert plan_hash(mapping, {}, ch) != plan_hash(mapping, {}, comma)
    assert plan_hash(mapping, {}, ch) != legacy


def test_grouping_is_validated_not_silently_removed():
    config = TransactionCsvFormat(delimiter=";", date_format="DMY", number_format="CH")
    assert normalize_cell("amount", "1’234.50", config) == "1234.50"
    with pytest.raises(ValueError):
        normalize_cell("amount", "12'34.50", config)
    with pytest.raises(ValueError):
        normalize_cell("amount", "1.234,50", config)


def test_ch_cash_export_becomes_exact_decimal_and_explicit_date():
    data = b"type;date;currency;amount\nDEPOSIT;01/02/2026;CHF;1'234.50\n"
    config = TransactionCsvFormat(delimiter=";", date_format="DMY", number_format="CH")
    rows = asyncio.run(
        parse_rows(
            data,
            uuid4(),
            {"type": "type", "date": "trade_date", "currency": "currency", "amount": "amount"},
            None,
            "Depot",
            csv_format=config,
        )
    )
    payload = rows[0]["payload"]
    assert payload.amount == Decimal("1234.50")
    assert payload.trade_date == date(2026, 2, 1)
