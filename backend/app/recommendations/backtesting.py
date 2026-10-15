from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.backtesting.engine import run_backtest
from app.core.config import get_settings
from app.core.errors import AppError
from app.models import (
    ModelPromotionReview,
    PortfolioSnapshot,
    Prediction,
    ResearchSnapshot,
    RiskSnapshot,
    User,
)
from app.models.recommendations import (
    InvestmentProfileVersion,
    Recommendation,
    RecommendationBacktest,
    RecommendationStrategyReview,
)
from app.recommendations.contracts import RULE_ID
from app.schemas.pit import BacktestInput
from app.schemas.recommendations import StrategyBacktestInput, StrategyReviewInput
from app.services.fundamentals import digest
from app.services.pit_datasets import DatasetBuilder
from app.services.portfolios import PortfolioService

D = Decimal


def stable_oos_folds(strategy: dict[str, Any], baselines: dict[str, Any]) -> int:
    """Fixed three contiguous OOS windows, >=200 sessions each; after-cost wealth."""
    equity = strategy.get("equity", [])
    if len(equity) < 600 or any(e["value"] is None for e in equity):
        return 0
    passed = 0
    for fold in range(3):
        start, end = fold * len(equity) // 3, (fold + 1) * len(equity) // 3 - 1
        if D(equity[start]["value"]) <= 0:
            continue
        own = D(equity[end]["value"]) / D(equity[start]["value"]) - 1
        valid = True
        for baseline in baselines.values():
            curve = baseline.get("equity", [])
            if (
                len(curve) != len(equity)
                or any(curve[i]["value"] is None for i in (start, end))
                or D(curve[start]["value"]) <= 0
            ):
                valid = False
                break
            if own <= D(curve[end]["value"]) / D(curve[start]["value"]) - 1:
                valid = False
        if valid:
            passed += 1
    return passed


def replay_archived(row: Recommendation) -> dict[str, Any]:
    if digest(row.input_manifest) != row.input_manifest_hash:
        raise AppError(409, "RECOMMENDATION_CONTENT_CHANGED", "Pinned recommendation mismatch")
    if digest(row.result) != row.input_manifest["result_hash"]:
        raise AppError(409, "RECOMMENDATION_RESULT_CHANGED", "Pinned result mismatch")
    from app.recommendations.engine import evaluate

    manifest = row.input_manifest
    result = evaluate(
        manifest["checks"],
        row.eligibility["violations"],
        manifest["components"],
        any(
            str(h["instrument_id"]) == str(row.instrument_id)
            for h in manifest["portfolio_current"]["holdings"]
        ),
        manifest["references"],
        row.result["explanation"]["portfolio_impact"],
    )
    if digest(result) != digest(row.result):
        raise AppError(409, "RECOMMENDATION_REPLAY_CHANGED", "Archived rule replay differs")
    return result


def position_state(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("status") != "COMPLETE" or any(
        c["currency"] != value["base_currency"] and D(str(c["amount"])) != 0 for c in value["cash"]
    ):
        raise AppError(
            422,
            "HISTORICAL_CASH_CONTRACT_UNAVAILABLE",
            "Replay requires base-currency cash; foreign cash cannot be silently netted",
        )
    positions: dict[str, Decimal] = {}
    for h in value["holdings"]:
        iid = str(h["instrument_id"])
        positions[iid] = positions.get(iid, D(0)) + D(str(h["quantity"]))
    return {
        "cash": str(value["cash_value_base"]),
        "positions": {k: str(v) for k, v in positions.items()},
    }


class RecommendationBacktestingService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db, self.user_id = db, user_id

    async def run(self, request: StrategyBacktestInput) -> RecommendationBacktest:
        await PortfolioService(self.db, self.user_id).owned(request.portfolio_id)
        builder = DatasetBuilder(self.db)
        dataset = await builder.owned(request.dataset_id, self.user_id)
        rows = []
        for identifier in request.recommendation_ids:
            row = await self.db.get(Recommendation, identifier)
            if not row or row.user_id != self.user_id or row.portfolio_id != request.portfolio_id:
                raise AppError(404, "RECOMMENDATION_NOT_FOUND", "Recommendation not found")
            replay_archived(row)
            rows.append(row)
        rows.sort(key=lambda r: (r.generated_at, str(r.id)))
        reasons = []
        if (
            dataset.configuration.get("availability_mode") != "STRICT_PIT"
            or dataset.configuration.get("data_context") != "USER_ARCHIVE"
        ):
            reasons.append("REAL_STRICT_PIT_DATA_REQUIRED")
        plans: dict[str, Any] = {}
        initial = None
        for row in rows:
            # Bootstrap strategy evaluation may replay an archived SHADOW decision, but
            # only strategy approval is relaxed inside this offline simulation. All
            # financial, forecast, profile and risk gates remain binding.
            financial_checks = {
                k: v for k, v in row.input_manifest["checks"].items() if k != "VALIDATED_STRATEGY"
            }
            if not all(financial_checks.values()) or row.eligibility["violations"]:
                reasons.append("HISTORICAL_ELIGIBLE_RECOMMENDATIONS_REQUIRED")
                continue
            dependencies: list[tuple[Any, UUID | None]] = [
                (Prediction, row.prediction_id),
                (RiskSnapshot, row.risk_snapshot_id),
                (PortfolioSnapshot, row.portfolio_snapshot_id),
                (InvestmentProfileVersion, row.profile_version_id),
                (ResearchSnapshot, row.research_snapshot_id),
            ]
            for model, dependency_id in dependencies:
                dependency = await self.db.get(model, dependency_id) if dependency_id else None
                if dependency is None or dependency.created_at > row.generated_at:
                    reasons.append("DEPENDENCY_NOT_ARCHIVED_AT_SIGNAL")
            for mid in row.input_manifest["references"]["model_versions"]:
                review = await self.db.scalar(
                    select(ModelPromotionReview)
                    .where(
                        ModelPromotionReview.model_id == UUID(mid),
                        ModelPromotionReview.created_at <= row.generated_at,
                    )
                    .order_by(
                        ModelPromotionReview.created_at.desc(), ModelPromotionReview.id.desc()
                    )
                    .limit(1)
                )
                if not review or review.status != "PRODUCTION":
                    reasons.append("MODEL_NOT_PRODUCTIVE_AT_SIGNAL")
            before = row.input_manifest["portfolio_current"]
            impact = row.result["explanation"]["portfolio_impact"]
            if impact is None:
                reasons.append("HISTORICAL_IMPACT_UNAVAILABLE")
                continue
            from app.recommendations.engine import evaluate

            simulated_decision = evaluate(
                {**row.input_manifest["checks"], "VALIDATED_STRATEGY": True},
                [],
                row.input_manifest["components"],
                any(str(h["instrument_id"]) == str(row.instrument_id) for h in before["holdings"]),
                row.input_manifest["references"],
                impact,
            )
            category = simulated_decision["category"]
            preview_side = impact.get("trades", [{}])[0].get("side")
            expected_side = (
                "BUY"
                if category == "CONSIDER_INCREASE"
                else "SELL"
                if category == "REVIEW_REDUCE"
                else None
            )
            if expected_side and expected_side != preview_side:
                reasons.append("HISTORICAL_ACTION_PREVIEW_MISMATCH")
                continue
            profile = await self.db.get(InvestmentProfileVersion, row.profile_version_id)
            assert profile
            if any(
                D(str(profile.preferences[key])) != getattr(request, field)
                for key, field in (
                    ("commission_base", "commission_base"),
                    ("spread_bps", "spread_bps"),
                    ("slippage_bps", "slippage_bps"),
                )
            ):
                reasons.append("COSTS_MUST_MATCH_ARCHIVED_PROFILE")
            if request.spread_bps > 500:
                reasons.append("EXECUTION_SPREAD_LIMIT")
            try:
                old = position_state(before)
                proposed = position_state(impact["current_valuation"])
            except AppError as error:
                reasons.append(error.code)
                continue
            day = row.generated_at.date().isoformat()
            if day in plans:
                reasons.append("AMBIGUOUS_MULTIPLE_SIGNAL_PORTFOLIOS")
            plans[day] = {
                "targets": proposed["positions"] if expected_side else old["positions"],
                "before_positions": old["positions"],
                "before_cash": old["cash"],
                "signal_generated_at": row.generated_at.isoformat(),
                "information_cutoff_at": row.generated_at.isoformat(),
            }
            if initial is None:
                initial = old
                if D(str(before["total_value_base"])) != request.initial_capital:
                    reasons.append("INITIAL_CAPITAL_MUST_MATCH_ARCHIVED_PORTFOLIO")
        result: dict[str, Any] = {
            "status": "RECOMMENDATION_BACKTEST_UNAVAILABLE",
            "reasons": sorted(set(reasons)),
            "strategy_rule": "recommendation-score-v1",
            "production_evidence": False,
            "baselines": {},
            "recommendation_ids": [str(r.id) for r in rows],
        }
        if not reasons and initial and plans:
            rebuilt = await builder.rebuild(dataset.id, self.user_id)
            if min(rebuilt["market"]) != min(plans):
                result["reasons"] = ["INITIAL_STATE_DATE_MUST_MATCH_DATASET_START"]
            else:
                config = BacktestInput(
                    dataset_id=dataset.id,
                    initial_capital=request.initial_capital,
                    commission=request.commission_base,
                    # P8/profile uses one-sided spread; P6 expects full spread.
                    spread_bps=request.spread_bps * 2,
                    slippage_bps=request.slippage_bps,
                    rebalance_sessions=1,
                )
                strategy = run_backtest(
                    rebuilt, config, initial_state=initial, execution_plans=plans
                )
                baselines = {
                    name: run_backtest(
                        rebuilt, config.model_copy(update={"strategy": name}), compare=False
                    )
                    for name in ("BENCHMARK_ONLY", "EQUAL_WEIGHT", "MOMENTUM", "QUALITY_VALUE")
                }
                baselines["NO_CHANGE"] = run_backtest(
                    rebuilt, config, compare=False, initial_state=initial, execution_plans={}
                )
                result.update(
                    {
                        "status": strategy["status"],
                        "strategy": strategy,
                        "baselines": baselines,
                        "production_evidence": strategy["status"] == "STRICT_PIT_VALID",
                    }
                )
                result["oos_folds_passed"] = stable_oos_folds(strategy, baselines)
        saved = RecommendationBacktest(
            user_id=self.user_id,
            portfolio_id=request.portfolio_id,
            dataset_id=dataset.id,
            rule_version_id=RULE_ID,
            configuration=request.model_dump(mode="json"),
            result=result,
            content_hash=digest(result),
        )
        self.db.add(saved)
        await self.db.commit()
        return saved

    async def review(self, request: StrategyReviewInput) -> RecommendationStrategyReview:
        user = await self.db.get(User, self.user_id)
        if not user or user.username not in get_settings().ml_operator_usernames:
            raise AppError(
                403,
                "OPERATOR_REVIEW_REQUIRED",
                "An authorized operator must review strategy evidence",
            )
        backtest = await self.db.get(RecommendationBacktest, request.backtest_id)
        if not backtest or backtest.user_id != self.user_id:
            raise AppError(404, "BACKTEST_NOT_FOUND", "Backtest not found")
        result = backtest.result
        reasons = []
        if result.get("production_evidence") is not True:
            reasons.append("REAL_STRATEGY_EVIDENCE_REQUIRED")
        strategy = result.get("strategy", {})
        metrics = strategy.get("metrics", {})
        if len(strategy.get("equity", [])) < 600 or not strategy.get("fills"):
            reasons.append("OOS_HISTORY_INSUFFICIENT")
        own = metrics.get("Total Return")
        for name in ("NO_CHANGE", "BENCHMARK_ONLY", "EQUAL_WEIGHT", "MOMENTUM", "QUALITY_VALUE"):
            baseline = result.get("baselines", {}).get(name, {})
            comparator = baseline.get("metrics", {}).get("Total Return")
            if (
                baseline.get("status") != "STRICT_PIT_VALID"
                or own is None
                or comparator is None
                or D(own) <= D(comparator)
            ):
                reasons.append("BASELINE_COMPARISON_FAILED_" + name)
        # A complete chronological fold analysis is indispensable; never infer it from one run.
        if result.get("oos_folds_passed", 0) < 3:
            reasons.append("STABLE_OOS_FOLDS_REQUIRED")
        if request.status == "PRODUCTION" and reasons:
            raise AppError(409, "STRATEGY_PROMOTION_BLOCKED", "; ".join(reasons))
        review = RecommendationStrategyReview(
            user_id=self.user_id,
            rule_version_id=RULE_ID,
            backtest_id=backtest.id,
            status=request.status,
            evidence={
                "rule_version": "strategy-promotion-v1",
                "reasons": reasons,
                "rationale": request.rationale,
                "backtest_hash": backtest.content_hash,
                "reviewed_at": datetime.now(UTC).isoformat(),
            },
        )
        self.db.add(review)
        await self.db.commit()
        return review
