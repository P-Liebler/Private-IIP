from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import (
    CorporateActionVersion,
    DataQuarantine,
    DataSource,
    FxRateVersion,
    Instrument,
    PriceDaily,
    PriceDailyVersion,
    RawIngestion,
)
from app.services.market_calendar import MarketCalendarService

ACCEPTED = {"ACCEPTED", "MANUAL_OVERRIDE"}


def pit_cutoff(as_of: datetime | None) -> datetime:
    if as_of is None:
        return datetime.now(UTC)
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise AppError(422, "AS_OF_TIMEZONE_REQUIRED", "as_of requires an explicit timezone")
    return as_of.astimezone(UTC)


def price_view(row: PriceDailyVersion, source_count: int = 1) -> dict[str, object]:
    return {
        "id": row.id,
        "date": row.trading_date,
        "open": row.open,
        "high": row.high,
        "low": row.low,
        "close": row.close,
        "adjusted_close": row.adjusted_close,
        "volume": row.volume,
        "currency": row.currency,
        "source_id": row.source_id,
        "raw_ingestion_id": row.raw_ingestion_id,
        "observed_at": row.observed_at,
        "known_at": row.known_at,
        "retrieved_at": row.retrieved_at,
        "last_updated": row.known_at,
        "source_count": source_count,
        "validation_status": row.validation_status,
        "replaces_version_id": row.replaces_version_id,
        "quality_score": row.quality_score,
        "quality_label": row.quality_label,
        "quality_components": row.quality_components,
        "warnings": row.warnings,
        "resolution": row.resolution,
    }


class MarketQueryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.max_fx_carry_days = get_settings().fx_max_carry_days

    async def prices(
        self, instrument_id: UUID, start: date, end: date, as_of: datetime | None = None
    ) -> dict[str, object]:
        if start > end or (end - start).days > 3650:
            raise AppError(422, "DATE_RANGE_INVALID", "Select an ordered range of at most 10 years")
        cutoff = pit_cutoff(as_of)
        all_versions = (
            await self.db.scalars(
                select(PriceDailyVersion)
                .where(
                    PriceDailyVersion.instrument_id == instrument_id,
                    PriceDailyVersion.trading_date.between(start, end),
                    PriceDailyVersion.known_at <= cutoff,
                    PriceDailyVersion.trading_date <= cutoff.date(),
                )
                .order_by(
                    PriceDailyVersion.trading_date,
                    PriceDailyVersion.known_at.desc(),
                    PriceDailyVersion.id.desc(),
                )
            )
        ).all()
        counts: dict[date, set[UUID]] = {}
        by_date: dict[date, PriceDailyVersion] = {}
        for row in all_versions:
            counts.setdefault(row.trading_date, set()).add(row.source_id)
            if row.resolution in ACCEPTED:
                by_date.setdefault(row.trading_date, row)
        values = [price_view(row, len(counts[row.trading_date])) for row in by_date.values()]
        instrument = await self.db.get(Instrument, instrument_id)
        calendar = MarketCalendarService()
        calendar_status = "UNAVAILABLE"
        chart_dates = set(by_date)
        if instrument is not None and (instrument.mic or instrument.exchange):
            exchange = instrument.mic or instrument.exchange or ""
            try:
                sessions = calendar.sessions_between(exchange, start, min(end, cutoff.date()))
                chart_dates.update(
                    day for day in sessions if calendar.session_close(exchange, day) <= cutoff
                )
                calendar_status = "AVAILABLE"
            except (AppError, ValueError):
                # Unsupported exchange/range: observed points remain visible, no invented sessions.
                pass
        return {
            "status": "AVAILABLE" if values else "UNAVAILABLE",
            "as_of": cutoff,
            "prices": values,
            "reason": None if values else "NO_VERIFIED_PRICES",
            "calendar_status": calendar_status,
            "calendar_version": calendar.version if calendar_status == "AVAILABLE" else None,
            "chart_series": [
                {"date": day, "value": by_date[day].close if day in by_date else None}
                for day in sorted(chart_dates)
            ],
        }

    async def price_versions(
        self, instrument_id: UUID, trading_date: date
    ) -> list[dict[str, object]]:
        rows = (
            await self.db.scalars(
                select(PriceDailyVersion)
                .where(
                    PriceDailyVersion.instrument_id == instrument_id,
                    PriceDailyVersion.trading_date == trading_date,
                )
                .order_by(PriceDailyVersion.known_at, PriceDailyVersion.id)
            )
        ).all()
        return [price_view(row, len({item.source_id for item in rows})) for row in rows]

    async def actions(
        self, instrument_id: UUID, start: date, end: date, as_of: datetime | None = None
    ) -> dict[str, object]:
        cutoff = pit_cutoff(as_of)
        rows = (
            await self.db.scalars(
                select(CorporateActionVersion)
                .where(
                    CorporateActionVersion.instrument_id == instrument_id,
                    CorporateActionVersion.action_date.between(start, end),
                    CorporateActionVersion.action_date <= cutoff.date(),
                    CorporateActionVersion.known_at <= cutoff,
                )
                .order_by(CorporateActionVersion.known_at.desc(), CorporateActionVersion.id.desc())
            )
        ).all()
        by_key: dict[tuple[date, str], CorporateActionVersion] = {}
        for row in rows:
            by_key.setdefault((row.action_date, row.action_type), row)
        return {
            "status": "AVAILABLE" if by_key else "UNAVAILABLE",
            "reason": None if by_key else "NO_VERIFIED_ACTIONS",
            "as_of": cutoff,
            "actions": [
                {
                    "id": row.id,
                    "date": row.action_date,
                    "type": row.action_type,
                    "value": row.value,
                    "ex_date": row.action_date,
                    "record_date": row.record_date,
                    "payment_date": row.payment_date,
                    "ratio": row.ratio,
                    "cash_amount": row.cash_amount,
                    "currency": row.currency,
                    "new_ticker": row.new_ticker,
                    "source_id": row.source_id,
                    "raw_ingestion_id": row.raw_ingestion_id,
                    "observed_at": row.observed_at,
                    "known_at": row.known_at,
                    "retrieved_at": row.retrieved_at,
                    "validation_status": row.validation_status,
                    "quality_score": row.quality_score,
                    "quality_components": row.quality_components,
                    "replaces_version_id": row.replaces_version_id,
                }
                for row in sorted(
                    by_key.values(), key=lambda item: (item.action_date, item.action_type)
                )
            ],
        }

    async def fx(
        self, base: str, quote: str, on_date: date, as_of: datetime | None = None
    ) -> dict[str, object]:
        base, quote = base.upper(), quote.upper()
        if base not in {"CHF", "EUR", "USD"} or quote not in {"CHF", "EUR", "USD"}:
            raise AppError(422, "FX_CURRENCY_INVALID", "Only CHF, EUR and USD are supported")
        cutoff = pit_cutoff(as_of)
        if on_date > cutoff.date():
            return {
                "status": "UNAVAILABLE",
                "reason": "FUTURE_AT_AS_OF",
                "base_currency": base,
                "quote_currency": quote,
                "date": on_date,
                "requested_date": on_date,
            }
        if base == quote:
            return {
                "status": "AVAILABLE",
                "base_currency": base,
                "quote_currency": quote,
                "date": on_date,
                "rate": Decimal(1),
                "rate_date": on_date,
                "carry_days": 0,
                "age_days": 0,
                "carried_forward": False,
                "derived": "IDENTITY",
                "legs": [],
            }
        direct = await self._leg(base, quote, on_date, cutoff)
        if direct is not None:
            return self._fx_view(
                base, quote, on_date, direct[0], [direct[1]], "DIRECT" if direct[2] else "INVERSE"
            )
        for bridge in ("CHF", "EUR", "USD"):
            if bridge in {base, quote}:
                continue
            first = await self._leg(base, bridge, on_date, cutoff)
            second = await self._leg(bridge, quote, on_date, cutoff)
            if first and second:
                return self._fx_view(
                    base, quote, on_date, first[0] * second[0], [first[1], second[1]], "CROSS"
                )
        return {
            "status": "UNAVAILABLE",
            "reason": "NO_FRESH_FX_RATE",
            "base_currency": base,
            "quote_currency": quote,
            "date": on_date,
            "requested_date": on_date,
            "max_carry_days": self.max_fx_carry_days,
        }

    async def _leg(
        self, base: str, quote: str, on_date: date, cutoff: datetime
    ) -> tuple[Decimal, FxRateVersion, bool] | None:
        options: list[tuple[Decimal, FxRateVersion, bool]] = []
        for direct in (True, False):
            x, y = (base, quote) if direct else (quote, base)
            rows = (
                await self.db.scalars(
                    select(FxRateVersion)
                    .where(
                        FxRateVersion.base_currency == x,
                        FxRateVersion.quote_currency == y,
                        FxRateVersion.rate_date.between(
                            on_date - timedelta(days=self.max_fx_carry_days), on_date
                        ),
                        FxRateVersion.known_at <= cutoff,
                        FxRateVersion.resolution.in_(ACCEPTED),
                    )
                    .order_by(
                        FxRateVersion.rate_date.desc(),
                        FxRateVersion.known_at.desc(),
                        FxRateVersion.id.desc(),
                    )
                    .limit(1)
                )
            ).all()
            if rows:
                row = rows[0]
                options.append((row.rate if direct else Decimal(1) / row.rate, row, direct))
        return (
            max(options, key=lambda option: (option[1].rate_date, option[1].known_at))
            if options
            else None
        )

    @staticmethod
    def _fx_view(
        base: str, quote: str, on_date: date, rate: Decimal, legs: list[FxRateVersion], derived: str
    ) -> dict[str, object]:
        rate_date = min(leg.rate_date for leg in legs)
        return {
            "status": "AVAILABLE",
            "base_currency": base,
            "quote_currency": quote,
            "date": on_date,
            "requested_date": on_date,
            "rate": rate,
            "rate_date": rate_date,
            "carry_days": (on_date - rate_date).days,
            "age_days": (on_date - rate_date).days,
            "carried_forward": on_date != rate_date,
            "validation_status": "WARNING"
            if any(leg.validation_status == "WARNING" for leg in legs)
            else "VALID",
            "quality_score": min(leg.quality_score for leg in legs),
            "source_ids": [leg.source_id for leg in legs],
            "derived": derived,
            "legs": [
                {
                    "id": leg.id,
                    "base_currency": leg.base_currency,
                    "quote_currency": leg.quote_currency,
                    "rate": leg.rate,
                    "rate_date": leg.rate_date,
                    "source_id": leg.source_id,
                    "raw_ingestion_id": leg.raw_ingestion_id,
                    "known_at": leg.known_at,
                    "retrieved_at": leg.retrieved_at,
                }
                for leg in legs
            ],
        }

    async def quality_summary(self) -> dict[str, object]:
        labels = (
            await self.db.execute(
                select(PriceDailyVersion.quality_label, func.count())
                .where(PriceDailyVersion.resolution.in_(ACCEPTED))
                .group_by(PriceDailyVersion.quality_label)
            )
        ).all()
        quarantine = await self.db.scalar(select(func.count()).select_from(DataQuarantine))
        latest = await self.db.scalar(
            select(func.max(PriceDailyVersion.known_at)).where(
                PriceDailyVersion.resolution.in_(ACCEPTED)
            )
        )
        latest_fx = await self.db.scalar(
            select(func.max(FxRateVersion.known_at)).where(FxRateVersion.resolution.in_(ACCEPTED))
        )
        latest_price_date = await self.db.scalar(select(func.max(PriceDaily.trading_date)))
        latest_fx_date = await self.db.scalar(
            select(func.max(FxRateVersion.rate_date)).where(FxRateVersion.resolution.in_(ACCEPTED))
        )
        failed_raw = await self.db.scalar(
            select(func.count()).select_from(RawIngestion).where(RawIngestion.status == "FAILED")
        )
        failed_sources = (
            await self.db.scalars(select(DataSource).where(DataSource.last_failure.is_not(None)))
        ).all()
        disagreements = await self.db.scalar(
            select(func.count())
            .select_from(PriceDailyVersion)
            .where(
                PriceDailyVersion.resolution.in_(
                    {"KEPT_EXISTING", "LOWER_PRIORITY", "QUARANTINED", "MANUAL_OVERRIDE"}
                )
            )
        )
        missing = await self.db.scalar(
            select(func.count())
            .select_from(Instrument)
            .outerjoin(PriceDaily, Instrument.id == PriceDaily.instrument_id)
            .where(PriceDaily.instrument_id.is_(None))
        )
        last_by_instrument = (
            select(PriceDaily.instrument_id, func.max(PriceDaily.trading_date).label("last_date"))
            .group_by(PriceDaily.instrument_id)
            .subquery()
        )
        stale = await self.db.scalar(
            select(func.count())
            .select_from(last_by_instrument)
            .where(last_by_instrument.c.last_date < datetime.now(UTC).date() - timedelta(days=7))
        )
        return {
            "price_quality": {label: count for label, count in labels},
            "quarantined_rows": quarantine or 0,
            "latest_price_known_at": latest,
            "last_successful_price_import": latest,
            "last_successful_fx_import": latest_fx,
            "latest_price_date": latest_price_date,
            "latest_fx_date": latest_fx_date,
            "failed_raw_ingestions": failed_raw or 0,
            "source_failures": [
                {
                    "slug": source.slug,
                    "last_failure": source.last_failure,
                    "failure_count": source.failure_count,
                }
                for source in failed_sources
            ],
            "source_disagreements": disagreements or 0,
            "instruments_with_missing_prices": missing or 0,
            "stale_prices": stale or 0,
            "price_freshness": "UNAVAILABLE"
            if latest_price_date is None
            else "STALE"
            if (datetime.now(UTC).date() - latest_price_date).days > 7
            else "CURRENT",
            "fx_freshness": "UNAVAILABLE"
            if latest_fx_date is None
            else "STALE"
            if (datetime.now(UTC).date() - latest_fx_date).days > 7
            else "CURRENT",
            "status": "AVAILABLE" if labels else "UNAVAILABLE",
        }


def total_return(
    previous_close: Decimal, next_close: Decimal, actions: list[dict[str, object]]
) -> Decimal:
    if previous_close <= 0 or next_close <= 0:
        raise ValueError("Positive closes required")
    shares = Decimal(1)
    cash = Decimal(0)
    for action in sorted(
        actions,
        key=lambda item: (
            str(item["date"]),
            0 if item["type"] in {"SPLIT", "REVERSE_SPLIT"} else 1,
        ),
    ):
        if action["type"] in {"SPLIT", "REVERSE_SPLIT"}:
            shares *= Decimal(str(action["value"]))
        elif action["type"] == "DIVIDEND":
            cash += shares * Decimal(str(action["value"]))
    return ((next_close * shares + cash) / previous_close) - 1
