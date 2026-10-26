"""Explicit, versioned CSV interpretation; original bytes are never rewritten."""

from __future__ import annotations

import csv
import re
from datetime import datetime
from io import StringIO
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.core.errors import AppError


class TransactionCsvFormat(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    delimiter: Literal[",", ";", "\t"]
    date_format: Literal["ISO", "DMY", "MDY"]
    number_format: Literal["POINT", "COMMA", "CH"]


NUMBER_FIELDS = {"quantity", "price", "amount", "fee", "tax", "fx_rate_to_base"}
DATE_FIELDS = {"trade_date", "settlement_date"}


def detect_format(data: bytes) -> TransactionCsvFormat | None:
    """Only auto-select an unambiguous canonical format, otherwise require review."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise AppError(422, "CSV_ENCODING_INVALID", "CSV must be UTF-8") from error
    candidates = []
    for delimiter in (",", ";", "\t"):
        try:
            rows = list(csv.reader(StringIO(text, newline=""), delimiter=delimiter, strict=True))
        except csv.Error:
            continue
        if rows and len(rows[0]) > 1 and all(len(row) == len(rows[0]) for row in rows):
            candidates.append((delimiter, rows))
    if len(candidates) != 1:
        return None
    delimiter, rows = candidates[0]
    # Slash/dot dates, decimal commas and grouping separators need an explicit choice.
    for row in rows[1:]:
        for cell in row:
            value = cell.strip()
            if re.fullmatch(r"\d{1,2}[/.]\d{1,2}[/.]\d{4}", value):
                return None
            if re.fullmatch(r"[+-]?[\d'’.,\s]+", value) and any(c in value for c in ",'’ "):
                return None
    return TransactionCsvFormat(delimiter=delimiter, date_format="ISO", number_format="POINT")


def normalize_cell(field: str, value: str, config: TransactionCsvFormat) -> str:
    if field in DATE_FIELDS:
        pattern = {"ISO": "%Y-%m-%d", "DMY": "%d.%m.%Y", "MDY": "%m/%d/%Y"}[config.date_format]
        if config.date_format == "DMY":
            value = value.replace("/", ".")
        return datetime.strptime(value, pattern).date().isoformat()
    if field not in NUMBER_FIELDS:
        return value
    if config.number_format == "POINT":
        pattern = r"[+-]?\d+(?:\.\d+)?"
    elif config.number_format == "COMMA":
        pattern = r"[+-]?\d+(?:,\d+)?"
    else:
        pattern = r"[+-]?(?:\d+|\d{1,3}(?:['’]\d{3})+)(?:\.\d+)?"
    if not re.fullmatch(pattern, value):
        raise ValueError(f"Invalid {field} for selected number format")
    return value.replace("’", "").replace("'", "").replace(",", ".")
