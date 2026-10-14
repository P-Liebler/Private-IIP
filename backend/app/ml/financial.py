"""Execute OOS model scores and baselines through the single P6 simulator."""

from decimal import Decimal
from typing import Any

from app.backtesting.engine import run_backtest
from app.schemas.pit import BacktestInput


def financial_evaluation(dataset: Any, evaluation: dict[str, Any], horizon: int) -> dict[str, Any]:
    results = []
    for fold in evaluation["folds"]:
        start, end = fold["window"]["test_start"][:10], fold["window"]["final_end"][:10]
        pinned = {
            "configuration": dataset.configuration,
            "rows": [r for r in dataset.rows if start <= r["date"] <= end],
            "market": {
                d: bars for d, bars in dataset.manifest["market"].items() if start <= d <= end
            },
            "actions": {
                iid: [a for a in actions if start <= a["date"] <= end]
                for iid, actions in dataset.manifest["actions"].items()
            },
        }
        scores = {
            (
                dataset.rows[int(p["row_id"])]["date"],
                dataset.rows[int(p["row_id"])]["instrument_id"],
            ): Decimal(str(p["prediction"]))
            for p in fold["oos_predictions"]
        }
        config = BacktestInput(dataset_id=dataset.id, rebalance_sessions=horizon)
        model = run_backtest(pinned, config, signal_scores=scores)
        baselines = {
            strategy: run_backtest(pinned, config.model_copy(update={"strategy": strategy}))
            for strategy in ("BENCHMARK_ONLY", "EQUAL_WEIGHT", "MOMENTUM", "QUALITY_VALUE")
        }
        results.append(
            {
                "window": fold["window"],
                "model": model,
                "baselines": baselines,
                "cost_configuration": config.model_dump(mode="json"),
                "ranking_policy": "top-n-oos-model-score-v1",
                "profitability_claim": "REQUIRES_INDEPENDENT_ROBUST_OOS_EVIDENCE",
            }
        )
    # All appropriate comparators must be complete; cash-only or unavailable
    # baseline results cannot satisfy a promotion criterion.
    passed = bool(results) and all(
        r["model"]["status"] == "STRICT_PIT_VALID"
        and all(b["status"] == "STRICT_PIT_VALID" for b in r["baselines"].values())
        and r["model"]["metrics"].get("Total Return") is not None
        and all(
            Decimal(str(r["model"]["metrics"]["Total Return"]))
            > Decimal(str(b["metrics"]["Total Return"]))
            for b in r["baselines"].values()
        )
        for r in results
    )
    return {"contract": "p7-p6-oos-cost-comparison-v1", "folds": results, "passed": passed}
