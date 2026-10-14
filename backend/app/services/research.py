from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import FundamentalFact, Instrument, ResearchMetric, ResearchSnapshot
from app.services.fundamental_metrics import FundamentalMetricsService, unavailable, valuation
from app.services.fundamentals import FundamentalService, digest, fact_key, fact_view
from app.services.market_queries import MarketQueryService, pit_cutoff
from app.services.research_scores import SCORE_RULE, calculate_scores


def snapshot_identity(result: dict[str, Any], explicit_as_of: datetime | None) -> str:
    """Ignore refresh wall-clock time; retain every semantic output/input change.

    Explicit historical requests pin their exact cutoff. Live refreshes reuse the
    first immutable observation while inputs, age eligibility and rules agree.
    """

    def semantic(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: semantic(v) for k, v in value.items() if k != "as_of"}
        if isinstance(value, list):
            return [semantic(v) for v in value]
        return value

    return digest(
        {
            "identity_contract": "research-identity-v2",
            "historical_cutoff": pit_cutoff(explicit_as_of).isoformat() if explicit_as_of else None,
            "semantic_result": semantic(result),
        }
    )


class ResearchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def calculate(
        self, instrument_id: UUID, as_of: datetime | None = None, period: str = "ANNUAL"
    ) -> dict[str, Any]:
        cutoff = pit_cutoff(as_of)
        instrument = await self.db.get(Instrument, instrument_id)
        if instrument is None:
            raise AppError(404, "INSTRUMENT_NOT_FOUND", "Instrument not found")
        facts = await FundamentalService(self.db).get_fundamentals(instrument_id, cutoff)
        rejected = list(
            (
                await self.db.scalars(
                    select(FundamentalFact).where(
                        FundamentalFact.instrument_id == instrument_id,
                        FundamentalFact.validation_status == "REJECTED",
                        FundamentalFact.observed_at <= cutoff,
                        FundamentalFact.known_at <= cutoff,
                    )
                )
            ).all()
        )
        accepted = {fact_key(f): f for f in facts}
        conflicts = [
            f
            for f in rejected
            if fact_key(f) not in accepted or f.observed_at >= accepted[fact_key(f)].observed_at
        ]
        engine = FundamentalMetricsService(facts)
        metrics = engine.calculate(period)
        durations = [f for f in facts if f.period_type == period]
        stale = bool(durations) and (cutoff.date() - max(f.period_end for f in durations)).days > (
            550 if period == "ANNUAL" else 200
        )
        if stale:
            metrics = {key: unavailable("STALE_FUNDAMENTALS") for key in metrics}
        price_result = await MarketQueryService(self.db).prices(
            instrument_id, cutoff.date() - timedelta(days=366), cutoff.date(), cutoff
        )
        prices = price_result["prices"]
        assert isinstance(prices, list)
        price = prices[-1] if prices else None
        # Share-class proof is explicit internal ID, never company aggregate by assumption.
        valuations = valuation(facts, price, cutoff.date(), str(instrument.id))
        annual_margins: list[Decimal] = []
        annual_ids: list[str] = []
        for revenue in sorted(
            (f for f in facts if f.metric == "revenue" and f.period_type == "ANNUAL"),
            key=lambda f: f.period_end,
        )[-4:]:
            net = [
                f
                for f in facts
                if f.metric == "net_income"
                and f.period_start == revenue.period_start
                and f.period_end == revenue.period_end
                and f.currency == revenue.currency
                and f.period_type == "ANNUAL"
            ]
            if (
                revenue.value is not None
                and revenue.value > 0
                and len(net) == 1
                and net[0].value is not None
            ):
                annual_margins.append(net[0].value / revenue.value)
                annual_ids.extend([str(revenue.id), str(net[0].id)])
        stability = unavailable("Four comparable annual margins required")
        annual_revenues = sorted(
            (f for f in facts if f.metric == "revenue" and f.period_type == "ANNUAL"),
            key=lambda f: f.period_end,
        )[-4:]
        if (
            len(annual_margins) == 4
            and len({f.currency for f in annual_revenues}) == 1
            and all(
                350 <= (right.period_end - left.period_end).days <= 380
                for left, right in zip(annual_revenues, annual_revenues[1:], strict=False)
            )
        ):
            mean = sum(annual_margins, Decimal(0)) / 4
            variance = sum(((m - mean) ** 2 for m in annual_margins), Decimal(0)) / 4
            stability = {
                "value": str(max(Decimal(0), 1 - variance.sqrt() / Decimal("0.1"))),
                "status": "AVAILABLE",
                "inputs": annual_ids,
                "rule_version": SCORE_RULE,
            }
        momentum = unavailable(
            "Corporate-action coverage UNVERIFIED; raw prices plus validated actions policy"
        )
        if stale:
            stability = unavailable("STALE_FUNDAMENTALS")
        scores = calculate_scores(
            {**metrics, **valuations, "margin_stability": stability, "momentum_252d": momentum},
            cutoff.isoformat(),
        )
        if conflicts:
            for score in scores.values():
                score["score"] = None
                score["status"] = "INSUFFICIENT_DATA"
                score["missing_inputs"].append("UNRESOLVED_FUNDAMENTAL_CONFLICT")
        return {
            "instrument_id": str(instrument_id),
            "as_of": cutoff.isoformat(),
            "period": period,
            "status": "STALE" if stale else "PARTIAL" if facts else "INSUFFICIENT_DATA",
            "facts": [jsonable_encoder(fact_view(f), custom_encoder={Decimal: str}) for f in facts],
            "metrics": metrics,
            "ttm": {
                m: engine.ttm(m)
                for m in ["revenue", "net_income", "operating_cash_flow", "free_cash_flow"]
            },
            "valuation": valuations,
            "scores": scores,
            "price": jsonable_encoder(price, custom_encoder={Decimal: str}),
            "momentum": momentum,
            "rule_version": SCORE_RULE,
            "history_contract": "Public known_at AND local observed_at must be <= as_of",
            "issues": [
                {
                    "metric": f.metric,
                    "reason": "UNRESOLVED_FUNDAMENTAL_CONFLICT",
                    "raw_ingestion_id": str(f.raw_ingestion_id),
                }
                for f in conflicts
            ],
        }

    async def materialize(
        self, instrument_id: UUID, as_of: datetime | None = None
    ) -> ResearchSnapshot:
        # Lock identity serializes duplicate materializations/imports.
        if await self.db.get(Instrument, instrument_id, with_for_update=True) is None:
            raise AppError(404, "INSTRUMENT_NOT_FOUND", "Instrument not found")
        result = await self.calculate(instrument_id, as_of)
        # JSON serialization is stable and retains decimal strings, exact input version IDs.
        result = json.loads(json.dumps(result, default=str))
        input_hash = snapshot_identity(result, as_of)
        existing = (
            await self.db.scalars(
                select(ResearchSnapshot).where(
                    ResearchSnapshot.instrument_id == instrument_id,
                    ResearchSnapshot.input_hash == input_hash,
                )
            )
        ).one_or_none()
        if existing:
            return existing
        snapshot = ResearchSnapshot(
            instrument_id=instrument_id,
            as_of=pit_cutoff(as_of),
            rule_version=SCORE_RULE,
            input_hash=input_hash,
            result=result,
        )
        self.db.add(snapshot)
        await self.db.flush()
        for metric, item in {
            **result["metrics"],
            **result["valuation"],
            **{
                f"score_{key.lower()}": {"value": item["score"], "status": item["status"]}
                for key, item in result["scores"].items()
            },
        }.items():
            number = Decimal(str(item["value"])) if item.get("value") is not None else None
            representable = number is None or number.adjusted() < 26
            self.db.add(
                ResearchMetric(
                    snapshot_id=snapshot.id,
                    metric=metric,
                    value=number if representable else None,
                    status=item["status"] if representable else "DATA_UNAVAILABLE",
                )
            )
        await self.db.commit()
        return snapshot
