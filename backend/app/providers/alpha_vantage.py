"""Optional raw daily compact contract, no mandatory key or premium history."""

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import DataQuarantine, Instrument, PriceDaily
from app.providers.http import fetch_response
from app.services.market_calendar import MarketCalendarService
from app.services.market_import import MarketImportService, ParsedRow
from app.services.market_validation import validate_price
from app.services.provider_canonical import counters
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService


def parse_daily(data: bytes, symbol: str) -> list[dict[str, str]]:
    try:

        def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate response key")
                result[key] = value
            return result

        document = json.loads(data, object_pairs_hook=unique)
        if "Information" in document or "Note" in document:
            raise AppError(429, "SOURCE_RATE_LIMITED", "Provider entitlement/quota notice")
        if document["Meta Data"]["2. Symbol"] != symbol:
            raise ValueError("Symbol mismatch")
        rows = document["Time Series (Daily)"]
        if not isinstance(rows, dict) or len(rows) > 100:
            raise ValueError("Only compact raw daily contract supported")
        fields = ("1. open", "2. high", "3. low", "4. close", "5. volume")
        if any(
            not isinstance(day, str)
            or not isinstance(row, dict)
            or any(not isinstance(row.get(field), str) for field in fields)
            for day, row in rows.items()
        ):
            raise ValueError("Unexpected daily value type")
        return [
            {
                "date": day,
                "open": row["1. open"],
                "high": row["2. high"],
                "low": row["3. low"],
                "close": row["4. close"],
                "volume": row["5. volume"],
            }
            for day, row in sorted(rows.items())
        ]
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        raise AppError(
            502, "SOURCE_RESPONSE_INVALID", "Invalid raw daily price contract"
        ) from error


class AlphaVantageCollector:
    def __init__(
        self,
        db: AsyncSession,
        *,
        client: httpx.AsyncClient | None = None,
        raw_service: RawIngestionService | None = None,
    ) -> None:
        self.db, self.client = db, client
        self.raw = raw_service or RawIngestionService(db)

    async def collect(self, instrument_id: UUID, start: date, end: date) -> dict[str, Any]:
        source = await SourceService(self.db).get("ALPHAVANTAGE")
        SourceGate.require_enabled(source, "prices")
        instrument = await self.db.get(Instrument, instrument_id)
        if (
            not instrument
            or not instrument.ticker
            or f"instrument={instrument_id}" not in (source.scope or "").split()
        ):
            raise AppError(
                409,
                "IDENTITY_REVIEW_REQUIRED",
                "Explicit instrument/symbol source contract required",
            )
        settings = get_settings()
        calendar = MarketCalendarService()
        calendar.calendar(instrument.exchange or instrument.mic or "")
        if not settings.alpha_vantage_api_key:
            raise AppError(
                409, "SOURCE_KEY_REQUIRED", "Configure the optional personal provider key"
            )
        if start > end or end > datetime.now(UTC).date() or (end - start).days > 1826:
            raise AppError(422, "DATE_RANGE_INVALID", "Bounded past price range required")
        raw = await fetch_response(
            self.db,
            self.raw,
            source,
            use="prices",
            url="https://www.alphavantage.co/query",
            allowed_host="www.alphavantage.co",
            resource="alpha_daily_raw",
            client=self.client,
            instrument_id=instrument_id,
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": instrument.ticker,
                "outputsize": "compact",
                "datatype": "json",
                "apikey": settings.alpha_vantage_api_key.get_secret_value(),
            },
            metadata={
                "identifier_value": instrument.ticker,
                "range_start": start.isoformat(),
                "range_end": end.isoformat(),
                "parser_version": "alpha-raw-daily-v1",
            },
        )
        observations = parse_daily(await self.raw.get_verified(raw.id), instrument.ticker)
        result = counters()
        requested_dates: list[str] = []
        service = MarketImportService(self.db, self.raw, parser_version="alpha-raw-daily-v1")
        await self.db.execute(text("LOCK TABLE price_daily IN SHARE ROW EXCLUSIVE MODE"))
        for line, row in enumerate(observations, 2):
            try:
                day = date.fromisoformat(row["date"])
                if not start <= day <= end:
                    continue
                requested_dates.append(day.isoformat())
                exchange = instrument.exchange or instrument.mic or ""
                if (
                    not calendar.is_session(exchange, day)
                    or calendar.session_close(exchange, day) + timedelta(minutes=90)
                    > raw.received_at
                ):
                    raise ValueError("Market closed or observation not published")
                item, warnings = validate_price(
                    {**row, "currency": instrument.currency}, instrument.currency
                )
                prior = (
                    await self.db.scalars(
                        select(PriceDaily)
                        .where(
                            PriceDaily.instrument_id == instrument_id, PriceDaily.trading_date < day
                        )
                        .order_by(PriceDaily.trading_date.desc())
                        .limit(1)
                    )
                ).first()
                if prior and abs(cast(Decimal, item["close"]) / prior.close - 1) > Decimal("0.35"):
                    raise ValueError("Large session jump needs action/source review")
            except ValueError:
                self.db.add(
                    DataQuarantine(
                        raw_ingestion_id=raw.id,
                        source_id=source.id,
                        instrument_id=instrument_id,
                        row_number=line,
                        data_type="prices",
                        record_key=f"{instrument_id}:{row.get('date')}",
                        reason="INVALID_RAW_OHLCV",
                        severity="ERROR",
                        row_data=row,
                    )
                )
                result["quarantined"] += 1
                continue
            await service._price(
                ParsedRow(
                    line, cast(dict[str, str | None], row), item, instrument_id, [], warnings
                ),
                raw.id,
                source.id,
                source.trust_level,
                source.priority,
                raw.received_at,
                "REJECT",
                None,
                result,
            )
        source.last_success = datetime.now(UTC)
        await self.db.commit()
        return {
            "status": "PARTIAL"
            if result["quarantined"]
            else ("SUCCESS" if requested_dates else "NO_NEW_DATA"),
            "observations": len(requested_dates),
            "actual_range": [min(requested_dates), max(requested_dates)]
            if requested_dates
            else None,
            "raw_ingestion_id": str(raw.id),
            **result,
            "history_contract": "COMPACT_LAST_100; requested gaps require coverage audit",
            "price_type": "RAW_OHLCV",
        }
