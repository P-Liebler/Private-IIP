import asyncio
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.ml.promotion import promotion_reasons
from app.models import (
    DatasetVersion,
    Instrument,
    MLModelVersion,
    ModelPromotionReview,
    Prediction,
)
from app.models.recommendations import (
    InvestmentProfileVersion,
    Recommendation,
    RecommendationRuleVersion,
    RecommendationStrategyReview,
)
from app.recommendations.candidates import candidates
from app.recommendations.contracts import RULE_CONFIG, RULE_ID
from app.recommendations.engine import evaluate, ranking_key
from app.recommendations.portfolio_context import candidate_trade, constraints, valuation_identity
from app.recommendations.preferences import PreferenceService
from app.schemas.recommendations import InvestmentPreferences, RecommendationInput
from app.schemas.risk import WhatIfInput
from app.services.fundamentals import digest
from app.services.ml_registry import ModelRegistryService
from app.services.pit_datasets import code_manifest
from app.services.portfolio_risk import PortfolioRiskService
from app.services.portfolio_valuation import PortfolioValuationService
from app.services.predictions import PredictionService
from app.services.rate_limit import rate_limiter
from app.services.research import ResearchService
from app.services.risk_simulations import RiskSimulationService
from app.services.work_limits import work_slot

D = Decimal


class RecommendationService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db, self.user_id = db, user_id

    async def owned(self, identifier: UUID) -> Recommendation:
        row = await self.db.get(Recommendation, identifier)
        if not row or row.user_id != self.user_id:
            raise AppError(404, "RECOMMENDATION_NOT_FOUND", "Recommendation not found")
        return row

    async def forecast(
        self, iid: UUID, horizon: int, now: datetime
    ) -> tuple[Prediction | None, bool]:
        # P7 rechecks current membership, PIT features, calibration and immutable
        # artifacts. An old cached prediction cannot authorize a changed context.
        prediction = await PredictionService(self.db).generate(iid, horizon, self.user_id)
        now = datetime.now(UTC)
        if not prediction or prediction.result.get("confidence_status") != "VALIDATED":
            return prediction, False
        result = prediction.result
        if (
            not now - timedelta(hours=24) <= prediction.generated_at <= now
            or prediction.information_cutoff_at > now
            or not result.get("model_versions")
            or prediction.dataset_id is None
        ):
            return prediction, False
        registry = ModelRegistryService(self.db)
        for identifier in result["model_versions"]:
            model = await self.db.get(MLModelVersion, UUID(identifier))
            if (
                not model
                or model.user_id != self.user_id
                or model.horizon != horizon
                or await registry.status(model.id) != "PRODUCTION"
            ):
                return prediction, False
            # Revalidate pinned bytes and code/dependency compatibility, not just review label.
            try:
                await registry.artifact(model)
            except (AppError, ValueError):
                return prediction, False
            dataset = await self.db.get(DatasetVersion, model.dataset_id)
            evidence = model.evaluation.get("promotion_evidence", {})
            review = await self.db.scalar(
                select(ModelPromotionReview)
                .where(ModelPromotionReview.model_id == model.id)
                .order_by(ModelPromotionReview.created_at.desc(), ModelPromotionReview.id.desc())
                .limit(1)
            )
            checked_evidence = {
                **(review.evidence.get("gates", evidence) if review else evidence),
                "model_card_verified": bool(review and review.evidence.get("model_card_hash")),
            }
            if (
                not dataset
                or dataset.configuration.get("availability_mode") != "STRICT_PIT"
                or promotion_reasons(checked_evidence)
            ):
                return prediction, False
        lower, upper = result.get("lower_bound"), result.get("upper_bound")
        coverage = result.get("empirical_coverage")
        valid = (
            lower is not None
            and upper is not None
            and coverage is not None
            and D(str(upper)) - D(str(lower)) <= D(".5")
            and D(str(upper)) >= D(str(lower))
            and D(str(coverage)) >= D(".85")
        )
        return prediction, valid

    async def strategy(self) -> RecommendationStrategyReview | None:
        return cast(
            RecommendationStrategyReview | None,
            await self.db.scalar(
                select(RecommendationStrategyReview)
                .where(
                    RecommendationStrategyReview.user_id == self.user_id,
                    RecommendationStrategyReview.rule_version_id == RULE_ID,
                )
                .order_by(
                    RecommendationStrategyReview.created_at.desc(),
                    RecommendationStrategyReview.id.desc(),
                )
                .limit(1)
            ),
        )

    async def run(self, request: RecommendationInput) -> list[Recommendation]:
        await rate_limiter.check_work("recommendations", str(self.user_id))
        try:
            async with work_slot(608690), asyncio.timeout(120):
                return await self._run(request)
        except TimeoutError as error:
            await self.db.rollback()
            raise AppError(
                503, "RECOMMENDATION_TIMEOUT", "Candidate evaluation timed out"
            ) from error

    async def _run(self, request: RecommendationInput) -> list[Recommendation]:
        risk = await PortfolioRiskService(self.db, self.user_id).owned_snapshot(
            request.portfolio_id, request.risk_snapshot_id
        )
        registered_rule = await self.db.get(RecommendationRuleVersion, RULE_ID)
        if registered_rule is None:
            raise AppError(503, "RECOMMENDATION_RULE_UNAVAILABLE", "Migrate the rule registry")
        if (
            registered_rule.content_hash != digest(RULE_CONFIG)
            or registered_rule.configuration != RULE_CONFIG
        ):
            raise AppError(
                503,
                "RECOMMENDATION_RULE_CHANGED",
                "Create a new version for changed recommendation rules",
            )
        profile = await PreferenceService(self.db, self.user_id).latest()
        if profile is None:
            defaults = InvestmentPreferences(
                base_currency=risk.result["current_valuation"]["base_currency"]
            ).model_dump(mode="json")
            profile = InvestmentProfileVersion(
                user_id=self.user_id, preferences=defaults, content_hash=digest(defaults)
            )
            self.db.add(profile)
            await self.db.flush()
        prefs, now = profile.preferences, datetime.now(UTC)
        value = cast(
            dict[str, Any],
            await PortfolioValuationService(self.db, self.user_id).value(request.portfolio_id),
        )
        value = {**value}  # P4 retains Decimal arithmetic until serializing the manifest.
        context_matches = valuation_identity(value) == valuation_identity(
            risk.result["current_valuation"]
        )
        held = [UUID(str(h["instrument_id"])) for h in value["holdings"]]
        identifiers = await candidates(self.db, self.user_id, request, held, now)
        strategy = await self.strategy()
        batch_id = str(uuid4())
        output = []
        for iid in identifiers:
            instrument = await self.db.get(Instrument, iid)
            if instrument is None:
                raise AppError(422, "INSTRUMENT_NOT_FOUND", "Candidate instrument does not exist")
            research = await ResearchService(self.db).materialize(iid, now)
            prediction, forecast_valid = await self.forecast(iid, prefs["investment_horizon"], now)
            nav = (
                D(str(value["total_value_base"])) if value["total_value_base"] is not None else None
            )
            current = sum(
                (
                    D(str(h["market_value_base"]))
                    for h in value["holdings"]
                    if str(h["instrument_id"]) == str(iid) and h["market_value_base"] is not None
                ),
                D(0),
            )
            amount = (
                request.amount
                if request.amount_mode == "FIXED"
                else request.amount * nav
                if nav is not None
                else None
            )
            if amount is not None and request.amount_mode == "TARGET_WEIGHT":
                amount -= current
            side = request.side
            if amount is not None and request.amount_mode == "TARGET_WEIGHT":
                side = "BUY" if amount > 0 else "SELL"
                amount = abs(amount)
            impact, impact_error = None, None
            if amount is not None and amount > 0:
                try:
                    simulation = await RiskSimulationService(self.db, self.user_id).whatif(
                        request.portfolio_id,
                        WhatIfInput(
                            risk_snapshot_id=risk.id,
                            trades=[candidate_trade(iid, side, amount, current)],
                            commission_base=D(prefs["commission_base"]),
                            spread_bps=D(prefs["spread_bps"]),
                            slippage_bps=D(prefs["slippage_bps"]),
                            scenario_benchmark_mappings=request.scenario_benchmark_mappings,
                        ),
                    )
                    impact = {**simulation.result, "what_if_run_id": str(simulation.id)}
                except AppError as error:
                    impact_error = error.code
            holding: dict[str, Any] = next(
                (h for h in value["holdings"] if str(h["instrument_id"]) == str(iid)), {}
            )
            metrics = risk.result["metrics"]
            scores = cast(dict[str, Any], research.result["scores"])
            liquid = (impact or risk.result).get("liquidity_evidence", {}).get(str(iid), {})
            volume = liquid.get("average_volume")
            asset = (impact or risk.result).get("asset_quality", {}).get(str(iid), {})
            cells = [
                c
                for c in (impact or risk.result)
                .get("correlations", {})
                .get("252", {})
                .get("cells", [])
                if str(iid) in (c.get("left"), c.get("right")) and c.get("left") != c.get("right")
            ]
            needed_peers = len(set(held) - {iid})
            corr_valid = len(cells) >= needed_peers and all(
                c.get("value") is not None for c in cells
            )
            constraints_valid, violations = constraints(
                impact["current_valuation"] if impact else value,
                impact["exposures"] if impact else risk.result["exposures"],
                impact["metrics"] if impact else metrics,
                prefs,
                amount or D(0),
            )
            if (
                not instrument.active
                or instrument.delisted_at
                and instrument.delisted_at <= now.date()
            ):
                violations.append("INSTRUMENT_NOT_TRADABLE")
            if (
                str(iid) in prefs["excluded_instruments"]
                or instrument.sector in prefs["excluded_sectors"]
            ):
                violations.append("USER_EXCLUSION")
            checks = {
                "PROFILE_CONFIRMED": prefs["confirmed"],
                "INSTRUMENT_EXCHANGE_VERIFIED": bool(instrument.exchange),
                "VALID_LATEST_PRICE": holding.get("valuation_status") == "CURRENT"
                or impact is not None,
                "VALID_FX": holding.get("fx", {}).get("status") == "AVAILABLE"
                or impact is not None,
                "CORPORATE_ACTION_COVERAGE": asset.get("status") == "AVAILABLE",
                "SUFFICIENT_HISTORY": metrics.get("observations", 0) >= 252,
                "FUNDAMENTAL_QUALITY": scores.get("Quality", {}).get("score") is not None,
                "VALUATION_QUALITY": scores.get("Value", {}).get("score") is not None,
                "NO_VALIDATED_PRODUCTION_FORECAST": forecast_valid,
                "VALIDATED_STRATEGY": strategy is not None and strategy.status == "PRODUCTION",
                "PORTFOLIO_COMPLETE": value["status"] == "COMPLETE",
                "RISK_CURRENT": now - timedelta(hours=24) <= risk.as_of <= now,
                "RISK_CONTEXT_MATCHES_LEDGER": context_matches,
                "RISK_METRICS": all(
                    metrics.get(k) is not None
                    for k in ("annualized_volatility", "maximum_drawdown")
                )
                and metrics.get("var", {}).get("status") == "AVAILABLE",
                "CVAR_COVERAGE": metrics.get("var", {}).get("cvar_status") == "AVAILABLE",
                "CORRELATION_COVERAGE": corr_valid,
                "SCENARIO_COVERAGE": impact is not None
                and len(impact.get("scenarios", {})) == 7
                and all(
                    s[side].get("status") == "AVAILABLE"
                    for s in impact.get("scenarios", {}).values()
                    for side in ("before", "after")
                ),
                "LIQUIDITY": volume is not None
                and D(str(volume)) >= D(prefs["minimum_liquidity"])
                and liquid.get("observations", 0) >= 20,
                "PORTFOLIO_CONSTRAINTS_KNOWN": constraints_valid,
                "HYPOTHETICAL_IMPACT_AVAILABLE": impact is not None
                and not impact.get("missing_inputs"),
                "POSITIVE_CANDIDATE_AMOUNT": amount is not None and amount > 0,
            }
            if impact_error:
                checks[impact_error] = False
            refs = {
                "risk_snapshot_id": str(risk.id),
                "research_snapshot_id": str(research.id),
                "prediction_id": str(prediction.id) if prediction else None,
                "model_versions": prediction.result.get("model_versions", []) if prediction else [],
                "profile_version_id": str(profile.id),
                "rule_version_id": str(RULE_ID),
            }
            pred = prediction.result if prediction and forecast_valid else {}
            excess, probability = (
                pred.get("expected_excess_return"),
                pred.get("probability_outperform"),
            )
            components = {
                "expected_excess_return": 50 + 500 * D(str(excess)) if excess is not None else None,
                "forecast_confidence": 100 * D(str(probability))
                if probability is not None
                else None,
                "quality": scores.get("Quality", {}).get("score"),
                "valuation": scores.get("Value", {}).get("score"),
                "momentum": scores.get("Momentum", {}).get("score"),
                "risk_penalty": D(str(metrics["annualized_volatility"])) * 200
                if metrics.get("annualized_volatility") is not None
                else None,
                "concentration_penalty": D(
                    risk.result["exposures"]["concentration"]["largest_position_weight"]
                )
                * 100
                if risk.result["exposures"].get("concentration")
                else None,
                "correlation_penalty": max(
                    [max(D(0), D(str(c["value"]))) * 100 for c in cells] or [D(0)]
                )
                if corr_valid
                else None,
                "transaction_cost_penalty": D(impact["costs_base"]) / amount * 10000
                if impact and amount and amount > 0
                else None,
            }
            result = evaluate(checks, violations, components, iid in held, refs, impact)
            manifest = {
                "references": refs,
                "evaluation_batch_id": batch_id,
                "candidate_set": [str(identifier) for identifier in identifiers],
                "configuration": request.model_dump(mode="json"),
                "profile_hash": profile.content_hash,
                "profile_preferences": prefs,
                "risk_hash": risk.content_hash,
                "research_hash": research.input_hash,
                "prediction": pred,
                "checks": checks,
                "components": components,
                "portfolio_current": value,
                "rule_hash": digest(RULE_CONFIG),
                "code": code_manifest(),
                "result_hash": digest(result),
                "strategy_review_id": str(strategy.id) if strategy else None,
            }
            manifest = json.loads(json.dumps(manifest, default=str))
            row = Recommendation(
                user_id=self.user_id,
                portfolio_id=request.portfolio_id,
                instrument_id=iid,
                portfolio_snapshot_id=risk.portfolio_snapshot_id,
                risk_snapshot_id=risk.id,
                prediction_id=prediction.id if prediction else None,
                research_snapshot_id=research.id,
                profile_version_id=profile.id,
                rule_version_id=RULE_ID,
                generated_at=datetime.now(UTC),
                input_manifest=manifest,
                input_manifest_hash=digest(manifest),
                category=result["category"],
                eligibility=result["eligibility"],
                result=result,
            )
            output.append(row)
        output.sort(
            key=lambda row: ranking_key(row.result["scoring"]["score"], str(row.instrument_id))
        )
        self.db.add_all(output)
        await self.db.commit()
        return output
