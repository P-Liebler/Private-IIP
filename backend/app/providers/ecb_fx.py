from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from io import StringIO
from typing import cast

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import DataSource
from app.services.market_validation import validate_fx
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService

ECB_ORIGIN = "https://data-api.ecb.europa.eu"
ECB_PATH = "/service/data/EXR/D.CHF+USD.EUR.SP00.A"
ECB_INPUT_SCOPE = "fx_inputs=EXR.D.CHF.EUR.SP00.A,EXR.D.USD.EUR.SP00.A"


def parse_ecb_csv(data: bytes) -> list[dict[str, object]]:
    """Parse ECB SDMX CSV 1.0 EXR observations: 1 EUR = OBS_VALUE CURRENCY."""
    try:
        reader = csv.DictReader(StringIO(data.decode("utf-8-sig"), newline=""), strict=True)
        fields = set(reader.fieldnames or [])
        if (
            not {
                "FREQ",
                "CURRENCY",
                "CURRENCY_DENOM",
                "EXR_TYPE",
                "EXR_SUFFIX",
                "TIME_PERIOD",
                "OBS_VALUE",
            }
            <= fields
        ):
            raise ValueError("Missing ECB EXR columns")
        result: list[dict[str, object]] = []
        seen: set[tuple[date, str]] = set()
        for row in reader:
            if (
                row.get("FREQ") != "D"
                or row.get("CURRENCY_DENOM") != "EUR"
                or row.get("EXR_TYPE") != "SP00"
                or row.get("EXR_SUFFIX") != "A"
                or row.get("CURRENCY") not in {"CHF", "USD"}
            ):
                raise ValueError("Unexpected ECB EXR series")
            fx = validate_fx(
                {
                    "date": row.get("TIME_PERIOD"),
                    "base_currency": "EUR",
                    "quote_currency": row.get("CURRENCY"),
                    "rate": row.get("OBS_VALUE"),
                }
            )
            key = (cast(date, fx["rate_date"]), cast(str, fx["quote_currency"]))
            if key in seen:
                raise ValueError("Duplicate ECB observation")
            seen.add(key)
            result.append(fx)
        return result
    except (UnicodeDecodeError, csv.Error, ValueError) as error:
        raise AppError(502, "SOURCE_RESPONSE_INVALID", "ECB EXR CSV is invalid") from error


class EcbFxCollector:
    parser_version = "ecb-exr-csv-v2"

    @staticmethod
    def require_scope(source: DataSource, start: date, end: date) -> None:
        """Every ECB path needs the same explicit two-leg archival contract.

        Old free-text reviews remain evidence; a new append-only review must
        attest this exact request rather than silently broadening that review.
        """
        for use in ("fx_rates", "raw_archive", "derived_analysis"):
            SourceGate.require_enabled(source, use)
        tokens = (source.scope or "").split()
        inputs = [token for token in tokens if token.startswith("fx_inputs=")]
        ranges = [
            token.removeprefix("fx_coverage=")
            for token in tokens
            if token.startswith("fx_coverage=")
        ]
        try:
            if inputs != [ECB_INPUT_SCOPE] or len(ranges) != 1:
                raise ValueError("Explicit ECB input/range contract required")
            first, last = ranges[0].split("|")
            if not date.fromisoformat(first) <= start <= end <= date.fromisoformat(last):
                raise ValueError("ECB request outside the reviewed range")
        except ValueError:
            raise AppError(
                403,
                "SOURCE_NOT_APPROVED",
                "ECB requires reviewed input series, date coverage and archival/analysis rights",
            ) from None

    def __init__(
        self,
        db: AsyncSession,
        *,
        client: httpx.AsyncClient | None = None,
        raw_service: RawIngestionService | None = None,
    ) -> None:
        self.db, self.client = db, client
        self.raw_service = raw_service or RawIngestionService(db)

    async def collect(self, start: date, end: date) -> dict[str, object]:
        from app.providers.http import fetch_response
        from app.services.fundamentals import digest
        from app.services.provider_canonical import (
            conditional_headers,
            no_new_data,
            persist_fx,
            save_sync,
            sync_state,
        )

        if start > end or (end - start).days > 31 or end > datetime.now(UTC).date():
            raise AppError(422, "DATE_RANGE_INVALID", "ECB range must be at most 32 past days")
        source = await SourceService(self.db).get("ECB")
        self.require_scope(source, start, end)
        key = digest((ECB_PATH, start, end, self.parser_version))
        state = await sync_state(self.db, source, key)
        raw = await fetch_response(
            self.db,
            self.raw_service,
            source,
            use="fx_rates",
            url=ECB_ORIGIN + ECB_PATH,
            allowed_host="data-api.ecb.europa.eu",
            resource="ecb_fx",
            client=self.client,
            scope_validator=lambda current: self.require_scope(current, start, end),
            params={
                "startPeriod": start.isoformat(),
                "endPeriod": end.isoformat(),
                "format": "csvdata",
                "includeHistory": "false",
            },
            headers={"Accept": "text/csv", **conditional_headers(state)},
            content_types=("text/csv", "application/vnd.sdmx.data+csv"),
            metadata={
                "range_start": start.isoformat(),
                "range_end": end.isoformat(),
                "parser_version": self.parser_version,
                "request_key": key,
            },
        )
        if raw.http_status in {204, 304}:
            return await no_new_data(self.db, source, state, raw)
        if state and state.content_hash == raw.sha256:
            return await no_new_data(self.db, source, state, raw)
        observations = parse_ecb_csv(await self.raw_service.get_verified(raw.id))
        if any(not start <= cast(date, row["rate_date"]) <= end for row in observations):
            raise AppError(502, "SOURCE_RESPONSE_INVALID", "ECB returned dates outside request")
        result = await persist_fx(self.db, raw, source, observations, self.parser_version)
        await save_sync(self.db, source, key, raw, self.parser_version, result)
        return result
