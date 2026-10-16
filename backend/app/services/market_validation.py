from __future__ import annotations

import re
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

PARSER_VERSION = "csv-v1"
VALIDATION_VERSION = "market-v1"
RECONCILIATION_VERSION = "close-v1"
CURRENCIES = {"CHF", "EUR", "USD"}
ACTION_TYPES = {"DIVIDEND", "SPLIT", "REVERSE_SPLIT", "TICKER_CHANGE", "DELISTING"}


def number(
    value: str | None,
    *,
    positive: bool = False,
    zero_allowed: bool = False,
    scale: int = 8,
    precision: int = 24,
) -> Decimal | None:
    if value is None or not value.strip():
        return None
    try:
        result = Decimal(value.strip())
    except InvalidOperation:
        raise ValueError("Ungültige Dezimalzahl") from None
    if not result.is_finite() or len(result.as_tuple().digits) > 20:
        raise ValueError("Dezimalzahl ausserhalb des zulässigen Bereichs")
    if (
        max(0, result.adjusted() + 1) > precision - scale
        or result.scaleb(scale) != result.scaleb(scale).to_integral_value()
    ):
        raise ValueError("Dezimalzahl passt nicht in die gespeicherte Genauigkeit")
    if positive and (result < 0 if zero_allowed else result <= 0):
        raise ValueError("Wert muss positiv sein")
    return result


def day(value: str | None) -> date:
    try:
        result = date.fromisoformat(value or "")
    except ValueError:
        raise ValueError("Datum muss ISO-Format YYYY-MM-DD haben") from None
    if result > datetime.now(UTC).date():
        raise ValueError("Datum liegt in der Zukunft")
    return result


def currency(value: str | None) -> str:
    result = (value or "").strip().upper()
    if result not in CURRENCIES:
        raise ValueError("Währung muss CHF, EUR oder USD sein")
    return result


def validate_price(
    row: dict[str, str | None], instrument_currency: str
) -> tuple[dict[str, object], list[str]]:
    trading_date = day(row.get("date"))
    close = number(row.get("close"), positive=True)
    if close is None:
        raise ValueError("Schlusskurs fehlt")
    values = {
        key: number(
            row.get(key),
            positive=True,
            zero_allowed=key == "volume",
            scale=4 if key == "volume" else 8,
            precision=28 if key == "volume" else 24,
        )
        for key in ("open", "high", "low", "volume")
    }
    if values["high"] is not None and any(
        value is not None and value > values["high"]
        for value in (values["open"], close, values["low"])
    ):
        raise ValueError("High liegt unter Open, Low oder Close")
    if values["low"] is not None and any(
        value is not None and value < values["low"]
        for value in (values["open"], close, values["high"])
    ):
        raise ValueError("Low liegt über Open, High oder Close")
    quote = currency(row.get("currency") or instrument_currency)
    if quote != instrument_currency:
        raise ValueError("Kurswährung widerspricht der Instrumentwährung")
    warnings: list[str] = []
    if values["volume"] == 0:
        warnings.append("ZERO_VOLUME")
    if trading_date.weekday() >= 5:
        warnings.append("WEEKEND_DATE")
    if row.get("adjusted_close"):
        adjusted = number(row["adjusted_close"], positive=True)
        if adjusted is None:
            raise ValueError("Adjusted Close ungültig")
        if abs(adjusted / close - 1) > Decimal("0.05"):
            warnings.append("ADJUSTED_CLOSE_DIFFERS; ignored for returns")
    else:
        adjusted = None
    return {
        "trading_date": trading_date,
        "close": close,
        "adjusted_close": adjusted,
        "currency": quote,
        **values,
    }, warnings


def validate_fx(row: dict[str, str | None]) -> dict[str, object]:
    base = currency(row.get("base_currency"))
    quote = currency(row.get("quote_currency"))
    if base == quote:
        raise ValueError("Identische Währungen sind abgeleitet, kein importierter Kurs")
    rate = number(row.get("rate"), positive=True, scale=12, precision=28)
    if rate is None:
        raise ValueError("FX-Kurs fehlt")
    return {
        "rate_date": day(row.get("date")),
        "base_currency": base,
        "quote_currency": quote,
        "rate": rate,
    }


def validate_action(row: dict[str, str | None], instrument_currency: str) -> dict[str, object]:
    kind = (row.get("action_type") or "").strip().upper()
    original_kind = kind
    if kind == "SPECIAL_DIVIDEND":
        kind = "DIVIDEND"
    if kind not in ACTION_TYPES:
        raise ValueError("Corporate-Action-Typ ungültig")
    amount_value = row.get("cash_amount") or row.get("value")
    ratio_value = row.get("ratio") or row.get("value")
    numerator = number(row.get("ratio_numerator"), positive=True)
    denominator = number(row.get("ratio_denominator"), positive=True)
    if (numerator is None) != (denominator is None):
        raise ValueError("Split requires both ratio numerator and denominator")
    if numerator is not None and denominator is not None:
        if kind not in {"SPLIT", "REVERSE_SPLIT"}:
            raise ValueError("Ratio components require a split event")
        computed = numerator / denominator
        if ratio_value and number(ratio_value, positive=True) != computed:
            raise ValueError("Conflicting split ratios")
        ratio_value = str(computed)
    value = number(
        amount_value if kind == "DIVIDEND" else ratio_value,
        positive=True,
        zero_allowed=kind == "DIVIDEND",
    )
    quote = (row.get("currency") or "").strip().upper() or None
    ticker = (row.get("new_ticker") or "").strip().upper() or None
    record_date = day(row["record_date"]) if row.get("record_date") else None
    payment_date = day(row["payment_date"]) if row.get("payment_date") else None
    action_date = day(row.get("date"))
    if record_date and record_date < action_date:
        raise ValueError("Record Date liegt vor Ex-Date")
    if payment_date and payment_date < action_date:
        raise ValueError("Payment Date liegt vor Ex-Date")
    if record_date and payment_date and payment_date < record_date:
        raise ValueError("Payment Date liegt vor Record Date")
    if kind == "DIVIDEND":
        if value is None or currency(quote) != instrument_currency or ticker:
            raise ValueError("Dividende erfordert nichtnegativen Betrag in Instrumentwährung")
    elif kind in {"SPLIT", "REVERSE_SPLIT"}:
        if (
            value is None
            or (kind == "SPLIT" and value <= 1)
            or (kind == "REVERSE_SPLIT" and value >= 1)
        ):
            raise ValueError("Split-Faktor muss > 1, Reverse-Split-Faktor zwischen 0 und 1 sein")
        if quote:
            raise ValueError("Split hat keine Währung")
    elif kind == "TICKER_CHANGE":
        if not ticker or not re.fullmatch(r"[A-Z0-9._-]{1,40}", ticker):
            raise ValueError("Tickerwechsel erfordert neuen Ticker")
        if value is not None or quote:
            raise ValueError("Tickerwechsel hat weder Wert noch Währung")
    elif value is not None or quote or ticker:
        raise ValueError("Delisting hat weder Wert, Währung noch neuen Ticker")
    return {
        "action_date": action_date,
        "action_type": kind,
        "value": value,
        "record_date": record_date,
        "payment_date": payment_date,
        "ratio": value if kind in {"SPLIT", "REVERSE_SPLIT"} else None,
        "cash_amount": value if kind == "DIVIDEND" else None,
        "currency": quote,
        "new_ticker": ticker,
        **(
            {
                "event_details": {
                    "classification": original_kind,
                    "ratio_numerator": str(numerator) if numerator is not None else None,
                    "ratio_denominator": str(denominator) if denominator is not None else None,
                    "source_reference": row.get("source_reference"),
                }
            }
            if original_kind == "SPECIAL_DIVIDEND"
            or numerator is not None
            or row.get("source_reference")
            else {}
        ),
    }


def discrepancy(existing: Decimal, incoming: Decimal) -> tuple[str, Decimal]:
    median = (incoming + existing) / 2
    pct = abs(incoming - existing) / median * 100
    if pct < Decimal("0.25"):
        return "CONSISTENT", pct
    if pct < Decimal("0.50"):
        return "NOTICE", pct
    if pct <= Decimal("2"):
        return "REVIEW", pct
    return "SEVERE", pct


def quality_score(
    *,
    trust: str,
    complete_ohlc: bool,
    observed_at: datetime,
    trading_date: date,
    crosscheck: str,
    action_checked: bool,
) -> tuple[float, str, dict[str, float]]:
    components = {
        "source_trust": {"A": 1.0, "B": 0.75, "C": 0.6, "D": 0.5}.get(trust, 0.0),
        "cross_validation": 1.0
        if crosscheck == "CONSISTENT"
        else 0.6
        if crosscheck == "NOTICE"
        else 0.5
        if crosscheck == "NO_REFERENCE"
        else 0.0,
        "freshness": 1.0 if (observed_at.date() - trading_date).days <= 3 else 0.3,
        "schema_quality": 1.0 if complete_ohlc else 0.6,
        "historical_consistency": 1.0 if action_checked else 0.5,
    }
    score = round(
        components["source_trust"] * 0.40
        + components["cross_validation"] * 0.25
        + components["freshness"] * 0.15
        + components["schema_quality"] * 0.10
        + components["historical_consistency"] * 0.10,
        4,
    )
    label = (
        "EXCELLENT"
        if score >= 0.95
        else "HIGH"
        if score >= 0.85
        else "MEDIUM"
        if score >= 0.70
        else "LOW"
        if score >= 0.50
        else "REJECT"
    )
    return score, label, components
