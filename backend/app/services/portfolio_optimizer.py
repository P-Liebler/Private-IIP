"""Constrained, long-only simulations on pinned P8 observations. No ledger writer."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import numpy as np
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.tools import ToolRegistry, saved_production_forecast
from app.core.errors import AppError
from app.models import Instrument, OptimizerRun
from app.recommendations.portfolio_context import constraints, valuation_identity
from app.recommendations.preferences import PreferenceService
from app.risk.scenarios import SCENARIOS, scenario
from app.risk.whatif import hypothetical
from app.schemas.assistant import OptimizerInput
from app.services.fundamentals import digest
from app.services.pit_datasets import code_manifest
from app.services.pit_features import json_value
from app.services.portfolio_risk import PortfolioRiskService

D = Decimal
OPTIMIZER_VERSION = "long-only-shrinkage-slsqp-v1"


def unavailable(reason: str) -> dict[str, Any]:
    return {"status": "OPTIMIZATION_UNAVAILABLE", "reason": reason, "weights": None}


def optimize(
    risk: dict[str, Any],
    profile: dict[str, Any],
    request: OptimizerInput,
    forecasts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    value = risk["current_valuation"]
    if value["status"] != "COMPLETE" or not value["total_value_base"]:
        return unavailable("COMPLETE_VALUATION_REQUIRED")
    nav = D(str(value["total_value_base"]))
    if nav <= 0 or any(D(str(c["amount"])) < 0 for c in value["cash"]):
        return unavailable("LEVERAGE_OR_NEGATIVE_CASH_UNSUPPORTED")
    quotes = {str(h["instrument_id"]): h for h in value["holdings"]}
    ids = sorted(quotes)
    if not 2 <= len(ids) <= 20:
        return unavailable("TWO_TO_TWENTY_HELD_INSTRUMENTS_REQUIRED")
    if not profile["confirmed"] or profile["base_currency"] != value["base_currency"]:
        return unavailable("CONFIRMED_MATCHING_PROFILE_REQUIRED")
    if any(i in profile["excluded_instruments"] for i in ids):
        return unavailable("EXCLUDED_HOLDING_REQUIRES_MANUAL_REVIEW")
    for iid, quote in quotes.items():
        if not quote.get("sector") or not quote.get("country"):
            return unavailable("VERIFIED_SECTOR_AND_COUNTRY_REQUIRED")
        if quote["sector"] in profile["excluded_sectors"]:
            return unavailable("EXCLUDED_SECTOR_REQUIRES_MANUAL_REVIEW")
        liquidity = risk.get("liquidity_evidence", {}).get(iid, {})
        if (
            liquidity.get("average_volume") is None
            or liquidity.get("observations", 0) < 20
            or D(str(liquidity["average_volume"])) < D(profile["minimum_liquidity"])
        ):
            return unavailable("LIQUIDITY_EVIDENCE_REQUIRED")
        if quote.get("valuation_status") != "CURRENT":
            return unavailable("CURRENT_QUOTES_REQUIRED")
    dates = [o["date"] for o in risk["return_observations"][1:]]
    if len(dates) < 252 or not risk["quality"].get("complete_return_series"):
        return unavailable("252_COMPLETE_ALIGNED_SESSIONS_REQUIRED")
    foreign_totals: dict[str, Decimal] = {}
    for account in value["cash"]:
        if account["currency"] != value["base_currency"] and D(str(account["amount"])) != 0:
            currency = account["currency"]
            foreign_totals[currency] = foreign_totals.get(currency, D(0)) + D(
                str(account["base_amount"])
            )
    foreign = [
        {"currency": currency, "base_amount": str(amount)}
        for currency, amount in sorted(foreign_totals.items())
    ]
    matrix = []
    try:
        for day in dates:
            row = [float(risk["asset_returns"][iid][day]) for iid in ids]
            row.extend(float(risk["cash_fx_returns"][c["currency"]][day]) for c in foreign)
            matrix.append(row)
    except (KeyError, TypeError, ValueError):
        return unavailable("ALIGNED_ASSET_OR_FX_RETURNS_MISSING")
    data = np.asarray(matrix, dtype=float)
    if not np.isfinite(data).all():
        return unavailable("NONFINITE_RETURNS")
    estimator = LedoitWolf().fit(data)
    cov = np.asarray(estimator.covariance_) * 252
    eigen = np.linalg.eigvalsh(cov)
    if (
        not np.isfinite(cov).all()
        or not np.allclose(cov, cov.T)
        or eigen.min() < -1e-12
        or eigen.max() <= 1e-12
    ):
        return unavailable("COVARIANCE_INVALID_OR_DEGENERATE")
    floor = float(eigen.max()) * 1e-8
    regularization = max(0.0, floor - float(eigen.min()))
    cov += np.eye(len(cov)) * regularization
    old = np.array(
        [
            sum(
                float(h["market_value_base"])
                for h in value["holdings"]
                if str(h["instrument_id"]) == iid
            )
            / float(nav)
            for iid in ids
        ]
    )
    fixed = np.array([float(c["base_amount"]) / float(nav) for c in foreign])
    budget = float(old.sum())  # Keep invested notional; no trivial all-cash optimum.
    n = len(ids)
    cost_rate = float(D(profile["spread_bps"]) + D(profile["slippage_bps"])) / 10000
    commission_reserve = float(D(profile["commission_base"]) * n / nav)

    def full(w: Any) -> Any:
        return np.concatenate((w, fixed))

    def costs(w: Any) -> float:
        return float(np.abs(w - old).sum()) * cost_rate + commission_reserve

    def variance(w: Any, covariance: Any = cov) -> float:
        x = full(w)
        return float(x @ covariance @ x)

    targets = np.array([float(request.target_weights.get(UUID(i), D(0))) for i in ids])
    rb = np.array([float(request.risk_budgets.get(UUID(i), D(1) / n)) for i in ids])
    if request.objective == "TARGET_ALLOCATION" and (
        set(map(str, request.target_weights)) != set(ids)
        or abs(targets.sum() - budget) > 1e-6
        or (targets < 0).any()
    ):
        return unavailable("TARGET_WEIGHTS_MUST_MATCH_HELD_UNIVERSE_AND_INVESTED_BUDGET")
    if request.objective == "RISK_BUDGET" and (
        (rb <= 0).any()
        or abs(rb.sum() - 1) > 1e-6
        or request.risk_budgets
        and set(map(str, request.risk_budgets)) != set(ids)
    ):
        return unavailable("POSITIVE_NORMALIZED_RISK_BUDGETS_REQUIRED")
    mu = None
    if request.objective == "EXPECTED_RETURN":
        if set(forecasts) != set(ids):
            return unavailable("EXPECTED_RETURN_OPTIMIZATION_UNAVAILABLE")
        mu = np.array([float(forecasts[i]["expected_excess_return"]) for i in ids])
        if not np.isfinite(mu).all():
            return unavailable("EXPECTED_RETURN_OPTIMIZATION_UNAVAILABLE")

    def objective(w: Any, covariance: Any = cov) -> float:
        if request.objective == "MINIMUM_VARIANCE":
            return variance(w, covariance)
        if request.objective == "MINIMUM_CONCENTRATION":
            return float(w @ w)
        if request.objective == "TARGET_ALLOCATION":
            return float(np.square(w - targets).sum())
        if request.objective == "EXPECTED_RETURN":
            assert mu is not None
            return -float(w @ mu) + costs(w)
        x = full(w)
        contribution = w * (covariance @ x)[:n]
        total = float(contribution.sum())
        return float(np.square(contribution - rb * total).sum()) * 1e6

    def margins(w: Any, covariance: Any = cov) -> Any:
        expense = costs(w)
        remaining = 1 - expense
        buy = float(np.maximum(w - old, 0).sum())
        out = [
            float(profile["maximum_turnover"]) - float(np.abs(w - old).sum()) / 2,
            float(profile["maximum_new_investment"]) / float(nav) - buy,
            (float(value["cash_value_base"]) / float(nav) - expense)
            - float(profile["minimum_cash_reserve"]) * remaining,
            float(profile["maximum_portfolio_volatility"]) ** 2 - variance(w, covariance),
            float(profile["max_single_position_weight"]) * remaining - float(w.max()),
        ]
        for field, limit in (("sector", "max_sector_weight"), ("country", "max_country_weight")):
            for group in {q[field] for q in quotes.values()}:
                weight = sum(w[k] for k, iid in enumerate(ids) if quotes[iid][field] == group)
                out.append(float(profile[limit]) * remaining - weight)
        for currency in {q["currency"] for q in quotes.values()} | {c["currency"] for c in foreign}:
            if currency == profile["base_currency"]:
                continue
            weight = sum(w[k] for k, iid in enumerate(ids) if quotes[iid]["currency"] == currency)
            weight += sum(
                float(c["base_amount"]) / float(nav) for c in foreign if c["currency"] == currency
            )
            out.append(float(profile["max_currency_exposure"]) * remaining - abs(weight))
        return np.asarray(out)

    equal = np.full(n, budget / n)
    bounds = [(0.0, float(profile["max_single_position_weight"])) for _ in ids]

    def solve(covariance: Any, start: Any, selected_bounds: Any = bounds) -> Any:
        return minimize(
            lambda w: objective(w, covariance),
            start,
            method="SLSQP",
            bounds=selected_bounds,
            constraints=[
                {"type": "eq", "fun": lambda w: w.sum() - budget},
                {"type": "ineq", "fun": lambda w: margins(w, covariance)},
            ],
            options={"maxiter": 300, "ftol": 1e-11},
        )

    solved = solve(cov, old)
    if not solved.success or not np.isfinite(solved.x).all() or margins(solved.x).min() < -1e-7:
        return unavailable("HARD_CONSTRAINTS_INFEASIBLE_OR_SOLVER_FAILED")
    w = solved.x
    minimum = float(request.minimum_position_weight)
    pruned = [
        (0.0, 0.0) if 1e-7 < v < minimum else (minimum, b[1]) if v >= minimum else (0.0, 0.0)
        for v, b in zip(w, bounds, strict=True)
    ]
    if any(1e-7 < v < minimum for v in w):
        solved = solve(cov, w, pruned)
        if not solved.success or margins(solved.x).min() < -1e-7:
            return unavailable("MINIMUM_MEANINGFUL_POSITION_INFEASIBLE")
        w = solved.x

    def trades_for(proposed: Any) -> list[dict[str, Any]]:
        trades = []
        for side in ("SELL", "BUY"):
            for index, iid in enumerate(ids):
                delta = D(str(float(proposed[index] - old[index]))) * nav
                if abs(delta) < nav * D(".000001"):
                    continue
                if (side == "BUY") != (delta > 0):
                    continue
                trades.append(
                    {
                        "instrument_id": iid,
                        "side": side,
                        "amount_base": str(delta) if side == "BUY" else None,
                        "sell_fraction": str(min(D(1), -delta / (D(str(old[index])) * nav)))
                        if side == "SELL"
                        else None,
                        "cash_currency": value["base_currency"],
                    }
                )
        return trades

    trades = trades_for(w)
    config = {
        "trades": trades,
        **{k: profile[k] for k in ("commission_base", "spread_bps", "slippage_bps")},
    }
    try:
        after = hypothetical(risk, config, quotes) if trades else risk
    except AppError as error:
        return unavailable(error.code)
    buy_amount = sum((D(t["amount_base"]) for t in trades if t["side"] == "BUY"), D(0))
    complete, violations = constraints(
        after["current_valuation"], after["exposures"], after["metrics"], profile, buy_amount
    )
    if not complete or violations:
        return {**unavailable("POST_COST_P8_CONSTRAINTS_FAILED"), "violations": violations}
    # Correlation stress is a PSD convex common-factor covariance, then +25% volatility.
    std = np.sqrt(np.diag(cov))
    stressed_cov = (0.75 * cov + 0.25 * np.outer(std, std)) * 1.25**2
    stressed = solve(stressed_cov, w)
    shift = float(np.abs(stressed.x - w).sum()) / 2 if stressed.success else None
    stressed_violations = bool(margins(w, stressed_cov).min() < -1e-7)
    sensitivity: dict[str, Any] = {
        "covariance_stress_feasible": bool(stressed.success),
        "weight_turnover_under_stress": shift,
        "current_solution_breaches_stress": stressed_violations,
        "volatility_multiplier": 1.25,
        "common_factor_mix": 0.25,
    }
    if mu is not None:
        sensitivity["expected_return_lower"] = str(
            sum(D(str(w[k])) * D(str(forecasts[i]["lower_bound"])) for k, i in enumerate(ids))
        )
        sensitivity["expected_return_upper"] = str(
            sum(D(str(w[k])) * D(str(forecasts[i]["upper_bound"])) for k, i in enumerate(ids))
        )
    return_sensitivity_low = False
    if mu is not None:
        central_mu = mu.copy()
        moves = []
        for bound in ("lower_bound", "upper_bound"):
            mu = np.array([float(forecasts[i][bound]) for i in ids])
            alternate = solve(cov, w)
            moves.append(float(np.abs(alternate.x - w).sum()) / 2 if alternate.success else None)
        mu = central_mu
        sensitivity["forecast_interval_weight_shifts"] = moves
        return_sensitivity_low = any(m is None or m > 0.10 for m in moves)
    equal_valid = bool(margins(equal).min() >= -1e-7)
    equal_comparison: dict[str, Any] = {
        "variance": variance(equal),
        "status": "CONSTRAINTS_VIOLATED",
        "estimated_cost_base": str(D(str(costs(equal))) * nav),
    }
    if equal_valid:
        try:
            equal_trades = trades_for(equal)
            equal_after = (
                hypothetical(risk, {**config, "trades": equal_trades}, quotes)
                if equal_trades
                else risk
            )
            equal_complete, equal_violations = constraints(
                equal_after["current_valuation"],
                equal_after["exposures"],
                equal_after["metrics"],
                profile,
                sum((D(t["amount_base"]) for t in equal_trades if t["side"] == "BUY"), D(0)),
            )
            equal_comparison.update(
                {
                    "status": "AVAILABLE"
                    if equal_complete and not equal_violations
                    else "CONSTRAINTS_VIOLATED",
                    "violations": equal_violations,
                    "metrics": equal_after["metrics"],
                    "costs_base": equal_after.get("costs_base", "0"),
                }
            )
        except AppError as error:
            equal_comparison["status"] = error.code
    return cast(
        dict[str, Any],
        json_value(
            {
                "status": "AVAILABLE",
                "rule_version": OPTIMIZER_VERSION,
                "notice": "SIMULATION_ONLY_NOT_AN_INVESTMENT_RECOMMENDATION_NO_LEDGER_WRITES",
                "weights": dict(zip(ids, map(float, w), strict=True)),
                "cash_policy": "FIXED_FOREIGN_CASH_FIXED_INVESTED_NOTIONAL",
                "covariance": {
                    "estimator": "LedoitWolf",
                    "observations": len(dates),
                    "annualization": 252,
                    "shrinkage": float(estimator.shrinkage_),
                    "eigenvalue_floor_added": regularization,
                    "condition_number": float(np.linalg.cond(cov)),
                    "matrix": cov.tolist(),
                    "order": ids + [c["currency"] for c in foreign],
                },
                "comparisons": {
                    "NO_CHANGE": {
                        "variance": variance(old),
                        "costs_base": "0",
                        "weights": old.tolist(),
                    },
                    "CURRENT_PORTFOLIO": risk["metrics"],
                    "EQUAL_WEIGHT": equal_comparison,
                },
                "robustness": "LOW_ROBUSTNESS"
                if return_sensitivity_low or stressed_violations or shift is None or shift > 0.10
                else "LIMITED_STRESS_CHECKS_PASSED",
                "sensitivity": sensitivity,
                "trades": trades,
                "p8_whatif": after,
                "scenarios": {
                    slug: {
                        "before": scenario(risk, definition),
                        "after": scenario(after, definition),
                    }
                    for slug, _, original in SCENARIOS
                    for definition in [
                        {
                            **original,
                            "benchmark_id": str(
                                request.scenario_benchmark_mappings[original["market"]]
                            )
                            if original.get("market") in request.scenario_benchmark_mappings
                            else None,
                            "benchmark_mapping_confirmed": original.get("market")
                            in request.scenario_benchmark_mappings,
                        }
                    ]
                },
            }
        ),
    )


class PortfolioOptimizerService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db, self.user_id = db, user_id

    async def run(self, portfolio_id: UUID, request: OptimizerInput) -> OptimizerRun:
        risk = await PortfolioRiskService(self.db, self.user_id).owned_snapshot(
            portfolio_id, request.risk_snapshot_id
        )
        profile = await PreferenceService(self.db, self.user_id).latest()
        now = datetime.now(UTC)
        current = await ToolRegistry(self.db, self.user_id).value(portfolio_id, now)
        forecasts: dict[str, dict[str, Any]] = {}
        if request.objective == "EXPECTED_RETURN":
            for holding in current["holdings"][:20]:
                iid = UUID(str(holding["instrument_id"]))
                prediction = await saved_production_forecast(self.db, self.user_id, iid, 30, now)
                if prediction and all(
                    prediction.result.get(k) is not None
                    for k in ("expected_excess_return", "lower_bound", "upper_bound")
                ):
                    forecasts[str(iid)] = {**prediction.result, "prediction_id": str(prediction.id)}
        metadata_current = True
        for holding in current["holdings"][:21]:
            instrument = await self.db.get(Instrument, UUID(str(holding["instrument_id"])))
            if (
                not instrument
                or not instrument.active
                or instrument.updated_at > risk.as_of
                or instrument.delisted_at is not None
                and instrument.delisted_at <= now.date()
            ):
                metadata_current = False
        if not profile:
            result = unavailable("CONFIRMED_PROFILE_REQUIRED")
        elif risk.as_of < now - timedelta(hours=24) or risk.created_at > now:
            result = unavailable("FRESH_RISK_SNAPSHOT_REQUIRED")
        elif valuation_identity(current) != valuation_identity(risk.result["current_valuation"]):
            result = unavailable("RISK_SNAPSHOT_NO_LONGER_MATCHES_LEDGER_OR_MARKET")
        elif not metadata_current:
            result = unavailable("INSTRUMENT_METADATA_CHANGED_OR_INACTIVE")
        else:
            result = optimize(risk.result, profile.preferences, request, forecasts)
        manifest = {
            "risk_hash": risk.content_hash,
            "profile_hash": profile.content_hash if profile else None,
            "forecast_ids": {i: f["prediction_id"] for i, f in forecasts.items()},
            "current_valuation_hash": digest(current),
            "configuration": request.model_dump(mode="json"),
            "version": OPTIMIZER_VERSION,
            "code": code_manifest(),
        }
        result["input_manifest"] = manifest
        row = OptimizerRun(
            user_id=self.user_id,
            portfolio_id=portfolio_id,
            risk_snapshot_id=risk.id,
            profile_version_id=profile.id if profile else None,
            configuration=request.model_dump(mode="json"),
            input_hash=digest(manifest),
            result=result,
            created_at=now,
        )
        self.db.add(row)
        await self.db.commit()
        return row
