from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from io import StringIO
from typing import cast

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.services.market_import import MarketImportService, ParsedRow
from app.services.market_validation import validate_fx
from app.services.provider_rate_limit import check_provider_rate
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService

ECB_ORIGIN = "https://data-api.ecb.europa.eu"
ECB_PATH = "/service/data/EXR/D.CHF+USD.EUR.SP00.A"


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
    def __init__(
        self,
        db: AsyncSession,
        *,
        client: httpx.AsyncClient | None = None,
        raw_service: RawIngestionService | None = None,
    ) -> None:
        self.db = db
        self.client = client
        self.raw_service = raw_service or RawIngestionService(db)

    async def collect(self, start: date, end: date) -> dict[str, object]:
        if start > end or (end - start).days > 31 or end > datetime.now(UTC).date():
            raise AppError(422, "DATE_RANGE_INVALID", "ECB range must be at most 32 past days")
        source = await SourceService(self.db).get("ECB")
        SourceGate.require_enabled(source, "fx_rates")
        await check_provider_rate(source)
        requested = datetime.now(UTC)
        metadata: dict[str, str | int] = {"endpoint": ECB_PATH, "method": "GET"}
        own_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=10.0)
        try:
            try:
                response = await client.get(
                    ECB_ORIGIN + ECB_PATH,
                    params={
                        "startPeriod": start.isoformat(),
                        "endPeriod": end.isoformat(),
                        "format": "csvdata",
                    },
                    headers={"Accept": "text/csv"},
                )
            except httpx.TimeoutException as error:
                await self.raw_service.record_failure(
                    source_id=source.id,
                    resource_type="ecb_fx",
                    requested_at=requested,
                    error_code="SOURCE_TIMEOUT",
                    request_metadata=metadata,
                )
                source.last_failure = datetime.now(UTC)
                source.failure_count += 1
                await self.db.commit()
                raise AppError(503, "SOURCE_TIMEOUT", "ECB request timed out") from error
            except httpx.RequestError as error:
                await self.raw_service.record_failure(
                    source_id=source.id,
                    resource_type="ecb_fx",
                    requested_at=requested,
                    error_code="SOURCE_UNAVAILABLE",
                    request_metadata=metadata,
                )
                source.last_failure = datetime.now(UTC)
                source.failure_count += 1
                await self.db.commit()
                raise AppError(503, "SOURCE_UNAVAILABLE", "ECB unavailable") from error
            raw = await self.raw_service.store(
                data=response.content,
                source_id=source.id,
                source_slug=source.slug,
                resource_type="ecb_fx",
                requested_at=requested,
                http_status=response.status_code,
                content_type=response.headers.get("Content-Type", "text/csv"),
                request_metadata=metadata,
            )
            if response.status_code == 429:
                raise AppError(429, "SOURCE_RATE_LIMITED", "ECB rate limited the request")
            if response.status_code >= 500:
                raise AppError(503, "SOURCE_UNAVAILABLE", "ECB unavailable")
            if response.status_code not in {200, 204}:
                raise AppError(502, "SOURCE_RESPONSE_INVALID", "ECB rejected the request")
            if response.status_code == 204:
                return {
                    "status": "UNAVAILABLE",
                    "reason": "NO_OBSERVATIONS",
                    "raw_ingestion_id": raw.id,
                }
            observations = parse_ecb_csv(await self.raw_service.get_verified(raw.id))
            if not observations:
                return {
                    "status": "UNAVAILABLE",
                    "reason": "NO_OBSERVATIONS",
                    "raw_ingestion_id": raw.id,
                }
            result = {
                "inserted": 0,
                "corrected": 0,
                "observed_only": 0,
                "unchanged": 0,
                "quarantined": 0,
            }
            service = MarketImportService(self.db, self.raw_service)
            try:
                await self.db.execute(text("LOCK TABLE fx_rates IN SHARE ROW EXCLUSIVE MODE"))
                for line, item in enumerate(observations, 2):
                    row = ParsedRow(line, {}, item, None, [], [])
                    await service._fx(
                        row, raw.id, source.id, source.priority, raw.received_at, "REJECT", result
                    )
                source.last_success = datetime.now(UTC)
                await self.db.commit()
            except Exception:
                await self.db.rollback()
                raise
            return {"status": "AVAILABLE", "raw_ingestion_id": raw.id, **result}
        finally:
            if own_client:
                await client.aclose()
