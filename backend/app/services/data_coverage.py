"""Explain readiness without weakening any P3–P10 gate or inventing availability."""

from collections import Counter
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.backtesting.validation import available
from app.core.errors import AppError
from app.models import (
    ActionCoverageReview,
    CorporateActionVersion,
    DataCoverageSnapshot,
    DataQuarantine,
    FundamentalFact,
    FxRateVersion,
    Instrument,
    UniverseDefinition,
    UniverseMembershipVersion,
)
from app.services.fundamentals import digest
from app.services.market_calendar import MarketCalendarService
from app.services.market_queries import MarketQueryService
from app.services.pit_evidence import EvidenceService
from app.services.pit_features import FeatureSnapshotService, json_value


class DataCoverageService:
    version = "coverage-v1"

    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db, self.user_id = db, user_id

    async def inspect(
        self,
        instrument_id: UUID,
        start: date,
        end: date,
        cutoff: datetime | None = None,
        *,
        save: bool = False,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        cutoff = cutoff or now
        if (
            cutoff.tzinfo is None
            or cutoff > now
            or start > end
            or (end - start).days > 1826
            or end > cutoff.date()
        ):
            raise AppError(
                422, "COVERAGE_RANGE_INVALID", "Select at most five past years and an aware cutoff"
            )
        instrument = await self.db.get(Instrument, instrument_id)
        if instrument is None:
            raise AppError(404, "INSTRUMENT_NOT_FOUND", "Instrument missing")
        calendar = MarketCalendarService()
        sessions: list[date] | None = None
        pending: list[date] = []
        try:
            exchange = instrument.exchange or instrument.mic or ""
            candidates = calendar.sessions_between(exchange, start, end)
            pending = [
                d
                for d in candidates
                if calendar.session_close(exchange, d) + timedelta(minutes=90) > cutoff
            ]
            sessions = [
                d
                for d in candidates
                if d not in pending
                and (not instrument.listed_at or d >= instrument.listed_at)
                and (not instrument.delisted_at or d <= instrument.delisted_at)
            ]
        except (AppError, ValueError):
            exchange = ""
        features = FeatureSnapshotService(self.db)
        prices = (
            await features.prices(instrument_id, start, end, cutoff, "RECONSTRUCTED_HISTORICAL")
            if exchange
            else json_value(
                (await MarketQueryService(self.db).prices(instrument_id, start, end, cutoff))[
                    "prices"
                ]
            )
        )
        # Reconstructed lookup is diagnostic; local views require observation.
        prices = [
            p
            for p in prices
            if datetime.fromisoformat(p["observed_at"]) <= cutoff
            and datetime.fromisoformat(p["known_at"]) <= cutoff
        ]
        dates = {date.fromisoformat(p["date"]) for p in prices}
        valid = set(sessions or []) & dates
        missing = sorted(set(sessions or []) - dates)
        strict = (
            await features.prices(instrument_id, start, end, cutoff, "STRICT_PIT")
            if exchange
            else []
        )
        strict_dates = set()
        evidence = EvidenceService(self.db)
        for p in strict:
            day = date.fromisoformat(p["date"])
            signal_time = calendar.session_close(exchange, day)
            review = await evidence.latest("price", UUID(p["id"]), signal_time)
            if review and available(
                "STRICT_PIT",
                signal_time,
                datetime.fromisoformat(p["known_at"]),
                datetime.fromisoformat(p["observed_at"]),
                review.level,
                review.created_at,
            ):
                strict_dates.add(day)
        actions, proof = await features.actions(instrument_id, start, end, cutoff, "STRICT_PIT")
        reviews = (
            await self.db.scalars(
                select(ActionCoverageReview)
                .where(
                    ActionCoverageReview.instrument_id == instrument_id,
                    ActionCoverageReview.start_date <= start,
                    ActionCoverageReview.end_date >= end,
                    ActionCoverageReview.created_at <= cutoff,
                )
                .order_by(ActionCoverageReview.created_at.desc())
            )
        ).all()
        versions = (
            await self.db.scalars(
                select(CorporateActionVersion)
                .where(
                    CorporateActionVersion.instrument_id == instrument_id,
                    CorporateActionVersion.action_date.between(start, end),
                    CorporateActionVersion.known_at <= cutoff,
                    CorporateActionVersion.observed_at <= cutoff,
                )
                .order_by(CorporateActionVersion.known_at.desc(), CorporateActionVersion.id.desc())
            )
        ).all()
        chosen_actions: dict[tuple[str, date], CorporateActionVersion] = {}
        for action in versions:
            chosen_actions.setdefault((action.action_type, action.action_date), action)
        by_type = dict.fromkeys(
            ("SPLIT", "DIVIDEND", "REVERSE_SPLIT", "TICKER_CHANGE", "DELISTING"), "UNVERIFIED"
        )
        for coverage_review in reviews:
            reviewed = [
                await self.db.get(CorporateActionVersion, UUID(value))
                for value in coverage_review.action_version_ids
            ]
            if any(row is None for row in reviewed):
                continue
            for kind in coverage_review.action_types:
                expected = {row.id for row in chosen_actions.values() if row.action_type == kind}
                pinned = {
                    row.id
                    for row in reviewed
                    if row is not None
                    and row.action_type == kind
                    and start <= row.action_date <= end
                }
                if expected == pinned and not any(
                    row.validation_status == "REJECTED"
                    for row in chosen_actions.values()
                    if row.action_type == kind
                ):
                    by_type[kind] = "VERIFIED"
        known_actions = json_value(
            (await MarketQueryService(self.db).actions(instrument_id, start, end, cutoff))[
                "actions"
            ]
        )
        quarantine = (
            await self.db.scalars(
                select(DataQuarantine).where(
                    DataQuarantine.instrument_id == instrument_id,
                    or_(DataQuarantine.resolved_at.is_(None), DataQuarantine.resolved_at > cutoff),
                    DataQuarantine.detected_at <= cutoff,
                )
            )
        ).all()
        quarantine = [
            r
            for r in quarantine
            if not r.row_data.get("date")
            or start.isoformat() <= str(r.row_data["date"]) <= end.isoformat()
        ]
        facts = (
            await self.db.scalars(
                select(FundamentalFact)
                .where(
                    FundamentalFact.instrument_id == instrument_id,
                    FundamentalFact.observed_at <= cutoff,
                    FundamentalFact.known_at <= cutoff,
                )
                .order_by(FundamentalFact.observed_at.desc())
            )
        ).all()
        accepted = [f for f in facts if f.validation_status != "REJECTED"]
        metrics = sorted({f.metric for f in accepted})
        required = {
            "revenue",
            "net_income",
            "eps_diluted",
            "operating_income",
            "total_assets",
            "total_liabilities",
            "operating_cash_flow",
            "capex",
        }
        members = (
            await self.db.scalars(
                select(UniverseMembershipVersion)
                .join(
                    UniverseDefinition,
                    UniverseDefinition.id == UniverseMembershipVersion.universe_id,
                )
                .where(
                    UniverseDefinition.user_id == self.user_id,
                    UniverseMembershipVersion.instrument_id == instrument_id,
                    UniverseMembershipVersion.observed_at <= cutoff,
                )
            )
        ).all()
        membership_ready = bool(sessions)
        for day in sessions or []:
            signal_time = calendar.session_close(exchange, day)
            member_candidates = [
                m
                for m in members
                if m.valid_from <= day
                and (m.valid_to is None or m.valid_to >= day)
                and m.known_at <= signal_time
                and m.observed_at <= signal_time
            ]
            # Any competing/removed interval requires P6 reconciliation, never a guessed membership.
            if len(member_candidates) != 1 or member_candidates[0].membership_status != "LISTED":
                membership_ready = False
                break
            member = member_candidates[0]
            review = await evidence.latest("membership", member.id, signal_time)
            universe_review = await evidence.latest("universe", member.universe_id, signal_time)
            if not (
                review
                and universe_review
                and available(
                    "STRICT_PIT",
                    signal_time,
                    member.known_at,
                    member.observed_at,
                    review.level,
                    review.created_at,
                )
                and universe_review.level.startswith("VERIFIED_")
                and universe_review.evidence.get("includes_delisted") is True
                and universe_review.evidence.get("valid_from", "9999")
                <= day.isoformat()
                <= universe_review.evidence.get("valid_to", "0000")
            ):
                membership_ready = False
                break
        fx_results = []
        strict_fx_ready = True
        query = MarketQueryService(self.db)

        async def fx_for(day: date, at: datetime) -> dict[str, Any]:
            try:
                converted: dict[str, Any] = json_value(
                    await query.fx(instrument.currency, "CHF", day, at)
                )
                return converted
            except AppError as error:
                return {"status": "UNAVAILABLE", "reason": error.code}

        for day in sessions or []:
            fx_results.append(await fx_for(day, cutoff))
            signal_time = calendar.session_close(exchange, day)
            conversion = await fx_for(day, signal_time)
            if conversion.get("status") != "AVAILABLE":
                strict_fx_ready = False
            for leg in conversion.get("legs", []):
                fx_row = await self.db.get(FxRateVersion, UUID(leg["id"]))
                review = await evidence.latest("fx", UUID(leg["id"]), signal_time)
                if not (
                    fx_row
                    and review
                    and available(
                        "STRICT_PIT",
                        signal_time,
                        fx_row.known_at,
                        fx_row.observed_at,
                        review.level,
                        review.created_at,
                    )
                ):
                    strict_fx_ready = False
        # A missing calendar cannot imply successful FX coverage from zero checked sessions.
        if not sessions:
            fx_results.extend([await fx_for(date.fromisoformat(p["date"]), cutoff) for p in prices])
        fx_missing = sum(r.get("status") != "AVAILABLE" for r in fx_results)
        missing_fields: Counter[str] = Counter()
        for p in prices:
            for field in ("open", "high", "low", "volume"):
                missing_fields[field] += p[field] is None
        latest = max(prices, key=lambda p: p["date"]) if prices else None
        quarantined_dates = {str(r.row_data.get("date")) for r in quarantine}
        daily_status = []
        for offset in range((end - start).days + 1):
            day = start + timedelta(days=offset)
            classification = (
                "UNKNOWN"
                if not exchange or (instrument.listed_at and day < instrument.listed_at)
                else "DELISTED"
                if instrument.delisted_at and day > instrument.delisted_at
                else "NOT_YET_PUBLISHED"
                if day in pending
                else "MARKET_CLOSED"
                if not calendar.is_session(exchange, day)
                else "INVALID_DATA"
                if day.isoformat() in quarantined_dates
                else "AVAILABLE"
                if day in dates
                else "SOURCE_MISSING"
            )
            daily_status.append({"date": day.isoformat(), "classification": classification})
        full_prices = bool(sessions) and not missing and not quarantine
        strict_ready = (
            full_prices
            and set(sessions or []) <= strict_dates
            and proof is not None
            and not fx_missing
            and strict_fx_ready
        )
        dataset_ready = bool(strict_ready and membership_ready)
        state = (
            "UNAVAILABLE"
            if not prices
            else "STRICT_PIT_READY"
            if dataset_ready
            else "RECONSTRUCTED_RESEARCH_ONLY"
            if full_prices and proof is not None and not fx_missing
            else "PARTIAL"
        )
        reasons = []
        if sessions is None:
            reasons.append("CALENDAR_UNAVAILABLE")
        if missing:
            reasons.append("SOURCE_MISSING")
        if not proof:
            reasons.append("CORPORATE_ACTION_COVERAGE_UNVERIFIED")
        if fx_missing:
            reasons.append("FX_UNAVAILABLE")
        if not membership_ready:
            reasons.append("HISTORICAL_MEMBERSHIP_REQUIRES_P6_INTERVAL_REVIEW")
        result: dict[str, Any] = json_value(
            {
                "version": self.version,
                "instrument_id": instrument_id,
                "start": start,
                "end": end,
                "as_of": cutoff,
                "exchange": instrument.exchange,
                "currency": instrument.currency,
                "state": state,
                "reasons": reasons,
                "price_coverage": {
                    "expected_sessions": len(sessions) if sessions is not None else None,
                    "available_valid_sessions": len(valid),
                    "missing_sessions": missing,
                    "daily_status": daily_status,
                    "duplicate_sessions": sorted(
                        {
                            r.row_data.get("date")
                            for r in quarantine
                            if "duplicate" in r.reason.lower() and r.row_data.get("date")
                        }
                    ),
                    "quarantined_sessions": sorted(quarantined_dates - {"None"}),
                    "quarantined_rows": len(quarantine),
                    "not_yet_published": pending,
                    "last_verified_market_session": max(valid) if valid else None,
                    "stale": bool(
                        sessions and (not latest or latest["date"] < sessions[-1].isoformat())
                    ),
                    "missing_classification": "SOURCE_MISSING"
                    if sessions is not None
                    else "UNKNOWN",
                },
                "OHLC_coverage": {
                    "available": len(prices),
                    "missing_fields": dict(missing_fields),
                    "open_available": sum(p["open"] is not None for p in prices),
                    "complete_ohlc_sessions": sum(
                        all(p[k] is not None for k in ("open", "high", "low")) for p in prices
                    ),
                    "execution_fallback": "NO_FILL",
                },
                "volume_coverage": {"available": sum(p["volume"] is not None for p in prices)},
                "corporate_action_coverage": {
                    "status": "VERIFIED" if proof else "UNVERIFIED",
                    "review_id": proof,
                    "events": known_actions,
                    "by_type": by_type,
                    "return_supported_events": actions,
                },
                "FX_coverage": {
                    "base": instrument.currency,
                    "quote": "CHF",
                    "missing_sessions": fx_missing,
                    "checked_sessions": len(fx_results),
                    "max_carry_days": query.max_fx_carry_days,
                },
                "fundamental_coverage": {
                    "metrics": metrics,
                    "missing_metrics": sorted(required - set(metrics)),
                    "periods": sorted({f.period_end.isoformat() for f in accepted}),
                    "latest_filing_id": accepted[0].filing_id if accepted else None,
                    "rejected_facts": sum(f.validation_status == "REJECTED" for f in facts),
                    "restated_facts": sum(f.replaces_version_id is not None for f in facts),
                },
                "historical_membership_coverage": {
                    "status": "VERIFIED" if membership_ready else "UNVERIFIED",
                    "observed_versions": len(members),
                    "survivorship_risk": "CURRENT_UNIVERSE_IS_NOT_HISTORICAL_MEMBERSHIP",
                },
                "verified_availability": {
                    "strict_price_sessions": len(strict_dates & set(sessions or [])),
                    "price_fx_actions_ready": strict_ready,
                    "dataset_ready": dataset_ready,
                    "classification_contract": (
                        "P6 AvailabilityReview; local observation and review cutoff required"
                    ),
                },
                "latest_price": latest,
                "last_successful_update": max((p["observed_at"] for p in prices), default=None),
                "readiness": {
                    "valuation": "AVAILABLE"
                    if latest and sessions is not None and not fx_missing
                    else "PARTIAL",
                    "momentum": "AVAILABLE" if proof and full_prices else "COVERAGE_UNVERIFIED",
                    "training": "DATA_LIMITED",
                    "forecasts": "SHADOW",
                    "recommendations": "GATED",
                    "risk": "PARTIAL",
                    "production": "NOT_RELEASED",
                },
            }
        )
        if save:
            self.db.add(
                DataCoverageSnapshot(
                    user_id=self.user_id,
                    instrument_id=instrument_id,
                    result=result,
                    content_hash=digest(result),
                )
            )
            await self.db.commit()
        return result
