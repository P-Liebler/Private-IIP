from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.backtesting.features import FEATURE_VERSION, feature, technical_features
from app.backtesting.validation import AvailabilityMode, available
from app.core.errors import AppError
from app.models import (
    ActionCoverageReview,
    CorporateActionVersion,
    FeatureSnapshot,
    FundamentalFact,
    Instrument,
    PriceDailyVersion,
)
from app.services.fundamental_metrics import FundamentalMetricsService, valuation
from app.services.fundamentals import FundamentalService, digest, fact_key
from app.services.market_calendar import MarketCalendarService
from app.services.market_queries import price_view
from app.services.pit_auxiliary import AuxiliaryFeatures
from app.services.pit_evidence import EvidenceService
from app.services.research_scores import calculate_scores


def json_value(value: Any) -> Any:
    return jsonable_encoder(value, custom_encoder={Decimal: str})


class FeatureSnapshotService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.calendar = MarketCalendarService()
        self.evidence = EvidenceService(db)

    async def prices(
        self, instrument_id: UUID, start: date, end: date, cutoff: datetime, mode: AvailabilityMode
    ) -> list[dict[str, Any]]:
        instrument = await self.db.get(Instrument, instrument_id)
        if instrument is None or not instrument.exchange:
            raise AppError(422, "CALENDAR_UNAVAILABLE", "Instrument exchange required")
        query = select(PriceDailyVersion).where(
            PriceDailyVersion.instrument_id == instrument_id,
            PriceDailyVersion.trading_date.between(start, end),
            PriceDailyVersion.resolution.in_(["ACCEPTED", "MANUAL_OVERRIDE"]),
            PriceDailyVersion.validation_status != "REJECTED",
        )
        if mode == "STRICT_PIT":
            query = query.where(
                PriceDailyVersion.known_at <= cutoff, PriceDailyVersion.observed_at <= cutoff
            )
        rows = (
            await self.db.scalars(
                query.order_by(
                    PriceDailyVersion.trading_date,
                    PriceDailyVersion.known_at.desc(),
                    PriceDailyVersion.id.desc(),
                )
            )
        ).all()
        selected = {}
        for row in rows:
            if row.trading_date in selected or not self.calendar.is_session(
                instrument.exchange, row.trading_date
            ):
                continue
            close = self.calendar.session_close(instrument.exchange, row.trading_date)
            if close > cutoff:
                continue
            review = await self.evidence.latest(
                "price", row.id, cutoff if mode == "STRICT_PIT" else None
            )
            if mode == "STRICT_PIT" and not available(
                mode,
                cutoff,
                row.known_at,
                row.observed_at,
                review.level if review else "UNVERIFIED",
                review.created_at if review else None,
            ):
                continue
            selected[row.trading_date] = json_value(price_view(row))
            selected[row.trading_date]["availability_review_id"] = (
                str(review.id) if review else None
            )
        return list(selected.values())

    async def actions(
        self, instrument_id: UUID, start: date, end: date, cutoff: datetime, mode: AvailabilityMode
    ) -> tuple[list[dict[str, Any]], str | None]:
        rows = (
            await self.db.scalars(
                select(CorporateActionVersion)
                .where(
                    CorporateActionVersion.instrument_id == instrument_id,
                    CorporateActionVersion.action_date.between(start, end),
                )
                .order_by(CorporateActionVersion.known_at.desc(), CorporateActionVersion.id.desc())
            )
        ).all()
        chosen = {}
        for r in rows:
            if mode == "STRICT_PIT" and (r.known_at > cutoff or r.observed_at > cutoff):
                continue
            key = (r.action_date, r.action_type)
            if key not in chosen:
                chosen[key] = r
        coverage_query = select(ActionCoverageReview).where(
            ActionCoverageReview.instrument_id == instrument_id,
            ActionCoverageReview.start_date <= start,
            ActionCoverageReview.end_date >= end,
        )
        if mode == "STRICT_PIT":
            coverage_query = coverage_query.where(ActionCoverageReview.created_at <= cutoff)
        reviews = (
            await self.db.scalars(coverage_query.order_by(ActionCoverageReview.created_at.desc()))
        ).all()
        ids = sorted(str(r.id) for r in chosen.values())
        proof = None
        for candidate in reviews:
            if not {"SPLIT", "DIVIDEND"} <= set(candidate.action_types):
                continue
            reviewed = []
            missing = False
            for value in candidate.action_version_ids:
                action = await self.db.get(CorporateActionVersion, UUID(value))
                if action is None:
                    missing = True
                    break
                if start <= action.action_date <= end:
                    reviewed.append(value)
            if not missing and sorted(reviewed) == ids:
                proof = candidate
                break
        # Any revised action invalidates the previous review, even if arithmetic agrees.
        if proof is None or any(
            r.validation_status == "REJECTED" or r.action_type not in {"SPLIT", "DIVIDEND"}
            for r in chosen.values()
        ):
            return [], None
        result = [
            {
                "id": str(r.id),
                "date": r.action_date.isoformat(),
                "type": r.action_type,
                "ratio": str(r.ratio) if r.ratio is not None else None,
                "cash_amount": str(r.cash_amount) if r.cash_amount is not None else None,
                "currency": r.currency,
                "payment_date": r.payment_date.isoformat() if r.payment_date else None,
                "raw_ingestion_id": str(r.raw_ingestion_id),
                "source_id": str(r.source_id),
                "known_at": r.known_at.isoformat(),
                "observed_at": r.observed_at.isoformat(),
            }
            for r in chosen.values()
        ]
        return sorted(result, key=lambda a: (a["date"], a["type"])), str(proof.id)

    @staticmethod
    def total_return(
        prices: list[dict[str, Any]], actions: list[dict[str, Any]]
    ) -> list[Decimal] | None:
        if not prices:
            return None
        if len({p["currency"] for p in prices}) != 1:
            return None  # A redenomination needs its own explicit conversion/action contract.
        x = [Decimal(str(prices[0]["close"]))]
        for previous, current in zip(prices, prices[1:], strict=False):
            ratio = Decimal(1)
            cash = Decimal(0)
            events = [a for a in actions if previous["date"] < a["date"] <= current["date"]]
            if len(events) > 1:
                return None  # ambiguous same-session entitlement requires explicit review policy
            for a in events:
                if a["type"] == "SPLIT":
                    if a["ratio"] is None or Decimal(a["ratio"]) <= 0:
                        return None
                    ratio = Decimal(a["ratio"])
                elif a["type"] == "DIVIDEND":
                    if a["cash_amount"] is None or a["currency"] != current["currency"]:
                        return None
                    cash = Decimal(a["cash_amount"])
            x.append(
                x[-1]
                * (Decimal(str(current["close"])) * ratio + cash)
                / Decimal(str(previous["close"]))
            )
        return x

    async def build(
        self,
        instrument_id: UUID,
        cutoff: datetime,
        mode: AvailabilityMode,
        benchmark_id: UUID | None = None,
    ) -> FeatureSnapshot:
        instrument = await self.db.get(Instrument, instrument_id)
        if instrument is None or not instrument.exchange:
            raise AppError(422, "CALENDAR_UNAVAILABLE", "Exchange missing")
        sessions = self.calendar.sessions_between(
            instrument.exchange, cutoff.date() - timedelta(days=550), cutoff.date()
        )
        sessions = [
            d for d in sessions if self.calendar.session_close(instrument.exchange, d) <= cutoff
        ][-253:]
        start = sessions[0] if sessions else cutoff.date()
        prices = await self.prices(instrument_id, start, cutoff.date(), cutoff, mode)
        actions, proof = await self.actions(instrument_id, start, cutoff.date(), cutoff, mode)
        total = self.total_return(prices, actions) if proof else None
        benchmark = None
        benchmark_ids = []
        benchmark_prices: list[str] = []
        benchmark_actions: list[str] = []
        benchmark_coverage: list[str] = []
        benchmark_evidence: list[str] = []
        if benchmark_id:
            bp = await self.prices(benchmark_id, start, cutoff.date(), cutoff, mode)
            ba, bc = await self.actions(benchmark_id, start, cutoff.date(), cutoff, mode)
            if (
                bc
                and [p["date"] for p in bp] == [p["date"] for p in prices]
                and {p["currency"] for p in bp} == {p["currency"] for p in prices}
            ):
                benchmark = self.total_return(bp, ba)
                benchmark_ids = [p["id"] for p in bp] + [a["id"] for a in ba] + [bc]
                benchmark_prices = [p["id"] for p in bp]
                benchmark_actions = [a["id"] for a in ba]
                benchmark_coverage = [bc]
                benchmark_evidence = [
                    p["availability_review_id"] for p in bp if p.get("availability_review_id")
                ]
        values = technical_features(prices, total, [d.isoformat() for d in sessions], benchmark)
        if any(a["type"] == "DIVIDEND" for a in actions):
            values["ATR"] = feature(
                None, [p["id"] for p in prices], "DIVIDEND_ADJUSTED_OHLC_POLICY_UNAVAILABLE"
            )
        # No sentiment/estimate/macro provider or fabricated historical snapshot.
        for name in [
            "EPS_revision_30d",
            "EPS_revision_90d",
            "target_change",
            "recommendation_change",
            "earnings_surprise",
            "sentiment_1d",
            "sentiment_7d",
            "sentiment_30d",
            "news_volume",
            "negative_news_ratio",
            "positive_news_ratio",
            "sentiment_change",
            "Fed_rate",
            "SNB_rate",
            "ECB_rate",
            "yield_2Y",
            "yield_10Y",
            "yield_curve",
            "inflation",
            "VIX",
            "credit_spreads",
            "USD_CHF",
            "EUR_CHF",
            "oil",
            "relative_sector_valuation",
            "relative_historical_valuation",
        ]:
            values[name] = feature(None, [], "HISTORICAL_INPUT_OR_MODEL_UNAVAILABLE")
        facts = await FundamentalService(self.db).get_fundamentals(instrument_id, cutoff)
        accepted = []
        reviews = []
        for f in facts:
            review = await self.evidence.latest("fact", f.id, cutoff)
            if available(
                "STRICT_PIT",
                cutoff,
                f.known_at,
                f.observed_at,
                review.level if review else "UNVERIFIED",
                review.created_at if review else None,
            ):
                accepted.append(f)
                if review:
                    reviews.append(str(review.id))
        calculated = FundamentalMetricsService(accepted).calculate("ANNUAL")
        val = valuation(accepted, prices[-1] if prices else None, cutoff.date(), str(instrument_id))
        annual = [f for f in accepted if f.period_type == "ANNUAL"]
        stale = bool(annual) and (cutoff.date() - max(f.period_end for f in annual)).days > 550
        rejected = (
            await self.db.scalars(
                select(FundamentalFact).where(
                    FundamentalFact.instrument_id == instrument_id,
                    FundamentalFact.validation_status == "REJECTED",
                    FundamentalFact.known_at <= cutoff,
                    FundamentalFact.observed_at <= cutoff,
                )
            )
        ).all()
        by_key = {fact_key(f): f for f in accepted}
        conflict = any(
            fact_key(f) not in by_key or f.observed_at >= by_key[fact_key(f)].observed_at
            for f in rejected
        )
        stale = stale or conflict
        for name, item in {**calculated, **val}.items():
            values[name] = feature(
                Decimal(item["value"]) if item.get("value") is not None and not stale else None,
                item.get("inputs", []),
                "STALE_OR_MISSING_FUNDAMENTALS",
            )
        scores = calculate_scores({**calculated, **val}, cutoff.isoformat())
        q = scores["Quality"]["score"]
        v = scores["Value"]["score"]
        values["quality_value"] = feature(
            (Decimal(q) + Decimal(v)) / 2
            if q is not None and v is not None and not stale
            else None,
            [str(f.id) for f in accepted],
        )
        auxiliary, auxiliary_ids = await AuxiliaryFeatures(self.db).calculate(instrument_id, cutoff)
        values.update(auxiliary)
        if any(a["type"] == "SPLIT" for a in actions):
            for name in ("volume_change", "volume_zscore"):
                values[name] = feature(
                    None, [p["id"] for p in prices], "SPLIT_VOLUME_BASIS_UNVERIFIED"
                )
        for alias, original in {
            "revenue_growth": "revenue_growth_yoy",
            "EPS_growth": "eps_growth_yoy",
            "FCF_growth": "fcf_growth_yoy",
            "FCF_margin": "fcf_margin",
            "PE": "P/E",
            "forward_PE": "Forward P/E",
            "PS": "P/S",
            "PB": "P/B",
            "EV_EBITDA": "EV/EBITDA",
            "EV_FCF": "EV/FCF",
            "FCF_yield": "FCF Yield",
            "earnings_yield": "Earnings Yield",
        }.items():
            values[alias] = values.get(original, feature(None, [], "INPUT_UNAVAILABLE"))
        result = {
            "instrument_id": str(instrument_id),
            "as_of": cutoff.isoformat(),
            "information_cutoff_at": cutoff.isoformat(),
            "feature_set_version": FEATURE_VERSION,
            "calendar_version": self.calendar.version,
            "availability_mode": mode,
            "availability_status": "STRICT_PIT"
            if mode == "STRICT_PIT"
            else "RECONSTRUCTED / HISTORICAL_AVAILABILITY_UNVERIFIED",
            "features": values,
            "input_version_ids": {
                "prices": [p["id"] for p in prices],
                "facts": sorted({str(f.id) for f in [*accepted, *rejected]}),
                "actions": [a["id"] for a in actions],
                "coverage": [proof] if proof else [],
                "benchmark": benchmark_ids,
                "benchmark_prices": benchmark_prices,
                "benchmark_actions": benchmark_actions,
                "benchmark_coverage": benchmark_coverage,
                **auxiliary_ids,
                "evidence": sorted(
                    set(
                        reviews
                        + benchmark_evidence
                        + auxiliary_ids["evidence"]
                        + [
                            p["availability_review_id"]
                            for p in prices
                            if p.get("availability_review_id")
                        ]
                    )
                ),
            },
            "quality": {
                "missing_features": sum(f["missing_flag"] for f in values.values()),
                "action_coverage": proof,
            },
            "configuration": {
                "benchmark_id": str(benchmark_id) if benchmark_id else None,
                "price_policy": "raw+explicit_actions-v1",
            },
        }
        content = digest(result)
        existing = (
            await self.db.scalars(
                select(FeatureSnapshot).where(
                    FeatureSnapshot.instrument_id == instrument_id,
                    FeatureSnapshot.content_hash == content,
                )
            )
        ).first()
        if existing:
            return existing
        snapshot = FeatureSnapshot(
            instrument_id=instrument_id,
            as_of=cutoff,
            information_cutoff_at=cutoff,
            feature_set_version=FEATURE_VERSION,
            content_hash=content,
            result=result,
        )
        self.db.add(snapshot)
        await self.db.flush()
        return snapshot
