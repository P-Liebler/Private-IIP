"""Bounded cached adapter over P3 market queries and P6 action/calendar contracts."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FxRateVersion, Instrument, PriceDailyVersion
from app.services.market_calendar import MarketCalendarService
from app.services.market_queries import ACCEPTED, MarketQueryService, price_view
from app.services.pit_features import FeatureSnapshotService, json_value


class RiskMarket:
    def __init__(self, db: AsyncSession, start: date, end: date, cutoff: datetime) -> None:
        self.db, self.start, self.end, self.cutoff = db, start, end, cutoff
        self.base = MarketQueryService(db)
        self.calendar = MarketCalendarService()
        self.price_cache: dict[UUID, list[dict[str, object]]] = {}
        self.blocked_price_dates: dict[UUID, set[date]] = {}
        self.fx_cache: dict[tuple[str, str, date], dict[str, object]] = {}
        self.versions: dict[str, set[str]] = {
            k: set() for k in ("price", "fx", "action", "coverage")
        }

    async def load(self, instrument_id: UUID) -> list[dict[str, object]]:
        if instrument_id not in self.price_cache:
            versions = (
                await self.db.scalars(
                    select(PriceDailyVersion)
                    .where(
                        PriceDailyVersion.instrument_id == instrument_id,
                        PriceDailyVersion.trading_date.between(
                            self.start - timedelta(days=7), self.end
                        ),
                        PriceDailyVersion.known_at <= self.cutoff,
                        PriceDailyVersion.observed_at <= self.cutoff,
                    )
                    .order_by(
                        PriceDailyVersion.trading_date,
                        PriceDailyVersion.known_at.desc(),
                        PriceDailyVersion.id.desc(),
                    )
                )
            ).all()
            newest: dict[date, PriceDailyVersion] = {}
            for version in versions:
                newest.setdefault(version.trading_date, version)
            self.blocked_price_dates[instrument_id] = {
                d
                for d, row in newest.items()
                if row.resolution not in ACCEPTED or row.validation_status == "REJECTED"
            }
            rows = [
                price_view(row)
                for d, row in newest.items()
                if d not in self.blocked_price_dates[instrument_id]
            ]
            self.versions["price"].update(str(row.id) for row in newest.values())
            self.price_cache[instrument_id] = rows
            self.versions["price"].update(str(p["id"]) for p in rows)
        return self.price_cache[instrument_id]

    async def prices(
        self, instrument_id: UUID, start: date, end: date, as_of: datetime | None = None
    ) -> dict[str, object]:
        rows = [p for p in await self.load(instrument_id) if start <= cast(date, p["date"]) <= end]
        if rows and any(
            cast(date, rows[-1]["date"]) <= d <= end
            for d in self.blocked_price_dates.get(instrument_id, set())
        ):
            rows = []
        return {
            "status": "AVAILABLE" if rows else "UNAVAILABLE",
            "prices": rows,
            "as_of": self.cutoff,
        }

    async def fx(
        self, base: str, quote: str, on_date: date, as_of: datetime | None = None
    ) -> dict[str, object]:
        key = base, quote, on_date
        if key not in self.fx_cache:
            response = await self.base.fx(base, quote, on_date, self.cutoff)
            for leg in cast(list[dict[str, Any]], response.get("legs", [])):
                row = await self.db.get(FxRateVersion, leg["id"])
                if row is None or row.known_at > self.cutoff or row.observed_at > self.cutoff:
                    response = {"status": "UNAVAILABLE", "reason": "FX_NOT_AVAILABLE_AT_CUTOFF"}
                    break
                latest = await self.db.scalar(
                    select(FxRateVersion)
                    .where(
                        FxRateVersion.base_currency == row.base_currency,
                        FxRateVersion.quote_currency == row.quote_currency,
                        FxRateVersion.rate_date.between(row.rate_date, on_date),
                        FxRateVersion.known_at <= self.cutoff,
                        FxRateVersion.observed_at <= self.cutoff,
                    )
                    .order_by(
                        FxRateVersion.rate_date.desc(),
                        FxRateVersion.known_at.desc(),
                        FxRateVersion.id.desc(),
                    )
                    .limit(1)
                )
                if latest is None or latest.id != row.id or latest.validation_status == "REJECTED":
                    response = {
                        "status": "UNAVAILABLE",
                        "reason": "FX_NEWER_UNRESOLVED_OBSERVATION",
                    }
                    break
                self.versions["fx"].add(str(row.id))
            self.fx_cache[key] = response
        return self.fx_cache[key]

    async def actions(
        self, instrument_id: UUID, start: date, end: date, as_of: datetime | None = None
    ) -> dict[str, object]:
        return await self.base.actions(instrument_id, start, end, self.cutoff)

    async def total_returns(
        self, instrument_id: UUID, base_currency: str, reference_dates: list[date] | None = None
    ) -> dict[str, Any]:
        instrument = await self.db.get(Instrument, instrument_id)
        if instrument is None or not instrument.exchange:
            return {"status": "CALENDAR_UNAVAILABLE", "returns": {}, "coverage_id": None}
        start = self.start
        aa, proof = await FeatureSnapshotService(self.db).actions(
            instrument_id, start, self.end, self.cutoff, "STRICT_PIT"
        )
        if proof is None:
            return {
                "status": "CORPORATE_ACTION_COVERAGE_UNVERIFIED",
                "returns": {},
                "coverage_id": None,
            }
        self.versions["coverage"].add(proof)
        self.versions["action"].update(a["id"] for a in aa)
        raw = [
            p
            for p in await self.load(instrument_id)
            if start <= cast(date, p["date"]) <= self.end
            and self.calendar.is_session(instrument.exchange, cast(date, p["date"]))
            and self.calendar.session_close(instrument.exchange, cast(date, p["date"]))
            <= self.cutoff
        ]
        prices = json_value(raw)
        levels = FeatureSnapshotService.total_return(prices, aa)
        if levels is None:
            return {"status": "TOTAL_RETURN_UNAVAILABLE", "returns": {}, "coverage_id": proof}
        values = {}
        native_levels = {
            date.fromisoformat(p["date"]): level for p, level in zip(prices, levels, strict=True)
        }
        prior_day, prior_value = None, None
        days = reference_dates if reference_dates is not None else sorted(native_levels)
        for day in days:
            price_day = (
                day
                if self.calendar.is_session(instrument.exchange, day)
                else self.calendar.previous_session(instrument.exchange, day)
            )
            level = native_levels.get(price_day)
            fx = await self.fx(instrument.currency, base_currency, day)
            value = (
                level * cast(Decimal, fx["rate"])
                if level is not None and fx["status"] == "AVAILABLE"
                else None
            )
            required = (
                self.calendar.sessions_between(
                    instrument.exchange, prior_day + timedelta(days=1), day
                )
                if prior_day is not None
                else []
            )
            if (
                value is not None
                and prior_value is not None
                and all(d in native_levels for d in required)
            ):
                values[day.isoformat()] = value / prior_value - 1
            prior_day, prior_value = day, value
        return {
            "status": "AVAILABLE" if values else "INSUFFICIENT_HISTORY",
            "returns": values,
            "coverage_id": proof,
            "exchange": instrument.exchange,
            "price_version_ids": [p["id"] for p in prices],
            "action_version_ids": [a["id"] for a in aa],
            "returns_policy": "P6_RAW_EXPLICIT_ACTIONS_REINVESTED_BASE_FX",
            "local_availability": "KNOWN_AT_AND_OBSERVED_AT_LE_AS_OF",
        }

    async def liquidity(self, instrument: Instrument) -> dict[str, Any]:
        if not instrument.exchange:
            return {"average_volume": None, "observations": 0, "reason": "CALENDAR_UNAVAILABLE"}
        prices = [
            p
            for p in await self.load(instrument.id)
            if self.calendar.is_session(instrument.exchange, cast(date, p["date"]))
            and self.calendar.session_close(instrument.exchange, cast(date, p["date"]))
            <= self.cutoff
        ][-20:]
        expected = (
            self.calendar.sessions_between(
                instrument.exchange,
                cast(date, prices[0]["date"]),
                cast(date, prices[-1]["date"]),
            )
            if prices
            else []
        )
        actions, proof = (
            await FeatureSnapshotService(self.db).actions(
                instrument.id,
                cast(date, prices[0]["date"]),
                cast(date, prices[-1]["date"]),
                self.cutoff,
                "STRICT_PIT",
            )
            if prices
            else ([], None)
        )
        if proof:
            self.versions["coverage"].add(proof)
            self.versions["action"].update(a["id"] for a in actions)
        valid = (
            len(prices) == 20
            and [p["date"] for p in prices] == expected
            and proof is not None
            and not any(a["type"] == "SPLIT" for a in actions)
            and all(p.get("volume") is not None and Decimal(str(p["volume"])) > 0 for p in prices)
        )
        return {
            "average_volume": str(sum((Decimal(str(p["volume"])) for p in prices), Decimal(0)) / 20)
            if valid
            else None,
            "observations": len(prices),
            "price_version_ids": [str(p["id"]) for p in prices],
            "coverage_id": proof,
            "quality": "EXACT_20_CLOSED_SESSIONS_SAME_SHARE_UNIT",
        }
