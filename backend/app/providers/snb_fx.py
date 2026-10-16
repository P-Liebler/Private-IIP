from __future__ import annotations

import calendar
import csv
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.providers.http import fetch_response
from app.services.fundamentals import digest
from app.services.provider_canonical import (
    conditional_headers,
    no_new_data,
    persist_macro,
    save_sync,
    sync_state,
)
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService

CONTRACTS = {
    "SNB_rate": ("snboffzisa", "D0(LZ)", "PERCENT", {"Date", "D0", "Value"}),
    "EUR_CHF": ("devkum", "D0(M1),D1(EUR1)", "RATE", {"Date", "D0", "D1", "Value"}),
    "USD_CHF": ("devkum", "D0(M1),D1(USD1)", "RATE", {"Date", "D0", "D1", "Value"}),
}
PARSER = "snb-monthly-csv-v1"


def parse_snb_csv(data: bytes, series: str, observed: datetime) -> list[dict[str, Any]]:
    try:
        cube, _, unit, expected = CONTRACTS[series]
        rows = [
            r
            for r in csv.reader(StringIO(data.decode("utf-8-sig")), delimiter=";", strict=True)
            if r
        ]
        if len(rows) < 3 or rows[0] != ["CubeId", cube] or rows[1][0] != "PublishingDate":
            raise ValueError("SNB metadata mismatch")
        # Current cube publication is not the historical release of each value.
        datetime.strptime(rows[1][1], "%Y-%m-%d %H:%M")
        fields = rows[2]
        if set(fields) != expected or len(fields) != len(expected) or len(rows) > 2003:
            raise ValueError("SNB schema mismatch")
        result, seen = [], set()
        for values in rows[3:]:
            if len(values) != len(fields):
                raise ValueError("SNB row mismatch")
            row = dict(zip(fields, values, strict=True))
            if row["D0"] != ("LZ" if series == "SNB_rate" else "M1"):
                raise ValueError("Wrong SNB dimension")
            if series != "SNB_rate" and row["D1"] != ("EUR1" if series == "EUR_CHF" else "USD1"):
                raise ValueError("Wrong SNB currency")
            month = datetime.strptime(row["Date"], "%Y-%m").date()
            day = month.replace(day=calendar.monthrange(month.year, month.month)[1])
            if day in seen or day > observed.date():
                raise ValueError("Duplicate/future SNB observation")
            seen.add(day)
            if row["Value"] in {"", "-"}:
                continue
            value = Decimal(row["Value"])
            if not value.is_finite() or (unit == "RATE" and value <= 0):
                raise ValueError("Invalid SNB value")
            result.append(
                {
                    "series": series,
                    "observation_date": day,
                    "value": str(value),
                    "unit": unit,
                    "known_at": observed,
                    "frequency": "M",
                    "provider_series": f"SNB:{cube}:{series}",
                    "release_date": None,
                    "revision_type": "RECONSTRUCTED_HISTORY",
                }
            )
        return result
    except (ValueError, KeyError, IndexError, UnicodeError, csv.Error, InvalidOperation) as error:
        raise AppError(
            502, "SOURCE_RESPONSE_INVALID", "SNB response violates verified monthly contract"
        ) from error


class SnbFxCollector:
    """Monthly reference FX and SNB policy rate; never daily valuation FX."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        client: httpx.AsyncClient | None = None,
        raw_service: RawIngestionService | None = None,
    ) -> None:
        self.db, self.client = db, client
        self.raw_service = raw_service or RawIngestionService(db)

    async def collect(self, start: date, end: date, series: str = "SNB_rate") -> dict[str, Any]:
        if (
            series not in CONTRACTS
            or start > end
            or (end - start).days > 366
            or end > datetime.now(UTC).date()
        ):
            raise AppError(
                422, "DATE_RANGE_INVALID", "SNB requires a supported series and bounded past range"
            )
        source = await SourceService(self.db).get("SNB")
        SourceGate.require_enabled(source, "macro")
        cube, selection, _, _ = CONTRACTS[series]
        path = f"/api/cube/{cube}/data/csv/en"
        params = {
            "dimSel": selection,
            "fromDate": start.strftime("%Y-%m"),
            "toDate": end.strftime("%Y-%m"),
        }
        key = digest((path, params, PARSER))
        state = await sync_state(self.db, source, key)
        raw = await fetch_response(
            self.db,
            self.raw_service,
            source,
            use="macro",
            url="https://data.snb.ch" + path,
            allowed_host="data.snb.ch",
            resource="snb_macro",
            client=self.client,
            params=params,
            headers=conditional_headers(state),
            content_types=("text/csv", "application/csv", "application/octet-stream"),
            metadata={
                "range_start": start.isoformat(),
                "range_end": end.isoformat(),
                "series": series,
                "parser_version": PARSER,
                "request_key": key,
            },
        )
        if raw.http_status in {204, 304} or (state and state.content_hash == raw.sha256):
            return await no_new_data(self.db, source, state, raw)
        observations = parse_snb_csv(
            await self.raw_service.get_verified(raw.id), series, raw.received_at
        )
        observations = [r for r in observations if start <= r["observation_date"] <= end]
        result = await persist_macro(self.db, raw, observations, PARSER)
        await save_sync(self.db, source, key, raw, PARSER, result)
        return result
