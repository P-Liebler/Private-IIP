"""Pure bounded training kernel shared by API jobs, workers and offline tests."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

import numpy as np
from pydantic import Field, model_validator
from threadpoolctl import threadpool_limits

from app.ml.calibration import calibrated, fit_conformal, fit_platt
from app.ml.metrics import block_bootstrap_brier, classification_metrics, regression_metrics
from app.ml.models import (
    CLASSIFIERS,
    ModelType,
    fit_estimator,
    fit_preprocessor,
    model_parameters,
    predict_estimator,
    transform,
)
from app.ml.promotion import PROMOTION_RULES
from app.ml.validation import FoldWindow, split_rows
from app.schemas.pit import StrictModel


def default_complexities() -> list[Literal[1, 2, 3]]:
    return [1, 2, 3]


class FinancialCosts(StrictModel):
    commission: Decimal = Field(default=Decimal("1"), gt=0, le=1000, allow_inf_nan=False)
    spread_bps: Decimal = Field(default=Decimal("5"), gt=0, le=1000, allow_inf_nan=False)
    slippage_bps: Decimal = Field(default=Decimal("5"), gt=0, le=1000, allow_inf_nan=False)
    fx_cost_bps: Decimal = Field(default=Decimal("5"), gt=0, le=1000, allow_inf_nan=False)


class TrainingInput(StrictModel):
    dataset_id: UUID
    model_type: ModelType
    target: Literal["classification", "excess_return", "instrument_return", "realized_volatility"]
    feature_names: list[str] = Field(min_length=1, max_length=50)
    required_features: list[str] = Field(min_length=1, max_length=50)
    horizon: Literal[30, 90] = 30
    folds: list[FoldWindow] = Field(min_length=1, max_length=5)
    seed: int = Field(default=71, ge=0, le=2**31 - 1)
    financial_costs: FinancialCosts = Field(default_factory=FinancialCosts)
    search_complexities: list[Literal[1, 2, 3]] = Field(
        default_factory=default_complexities, min_length=1, max_length=3
    )

    @model_validator(mode="after")
    def contract(self) -> "TrainingInput":
        if len(set(self.search_complexities)) != len(self.search_complexities):
            raise ValueError("DUPLICATE_SEARCH_PARAMETERS")
        if len(set(self.feature_names)) != len(self.feature_names) or not set(
            self.required_features
        ) <= set(self.feature_names):
            raise ValueError("INVALID_FEATURE_SELECTION")
        if (self.model_type in CLASSIFIERS) != (self.target == "classification"):
            raise ValueError("MODEL_TARGET_MISMATCH")
        for previous, following in zip(self.folds, self.folds[1:], strict=False):
            if (
                previous.final_end >= following.test_start
                or previous.validation_start >= following.validation_start
            ):
                raise ValueError("OOS_FOLDS_OVERLAP_OR_UNORDERED")
        return self


def feature_matrix(rows: list[dict[str, Any]], names: list[str]) -> Any:
    return np.asarray(
        [
            [
                float(row["features"][name]["value"])
                if row["features"].get(name, {}).get("value") is not None
                and not row["features"][name].get("missing_flag", True)
                else np.nan
                for name in names
            ]
            for row in rows
        ],
        dtype=float,
    )


def train_kernel(
    config: TrainingInput,
    rows: list[dict[str, Any]],
    readiness: dict[str, Any],
    exchanges: dict[str, str],
) -> dict[str, Any]:
    if len(rows) > 30_000:
        raise ValueError("TRAINING_ROW_LIMIT")
    eligible = [
        i
        for i in readiness["eligible_row_ids"]
        if rows[int(i)]["target"].get(config.target) is not None
    ]
    folds = []
    all_y, all_predictions, all_dates = [], [], []
    artifacts = []
    with threadpool_limits(limits=1):
        for window in config.folds:
            partitions = split_rows(rows, window, config.horizon, exchanges, eligible)
            selected = {name: [rows[int(i)] for i in ids] for name, ids in partitions.items()}
            if len(selected["training"]) < 50 or any(
                len(selected[k]) < 10 for k in ("validation", "calibration", "test")
            ):
                raise ValueError("INSUFFICIENT_PARTITION_HISTORY")
            x = {
                k: feature_matrix(v, config.feature_names)
                for k, v in selected.items()
                if k != "purged"
            }
            y = {
                k: np.asarray([float(r["target"][config.target]) for r in v])
                for k, v in selected.items()
                if k != "purged"
            }
            # Search reads TRAIN only. Inner chronological holdout purges labels
            # against the first inner-validation signal; no outer tuning.
            ordered_dates = sorted({r["date"] for r in selected["training"]})
            inner_day = ordered_dates[int(len(ordered_dates) * 0.7)]
            inner_signals = [
                datetime.fromisoformat(r["information_cutoff_at"])
                for r in selected["training"]
                if r["date"] >= inner_day
            ]
            inner_cutoff = min(inner_signals)
            inner_train = [
                r
                for r in selected["training"]
                if datetime.fromisoformat(r["target"]["label_available_at"]) < inner_cutoff
                and r["date"] < inner_day
            ]
            # Additional conservative session embargo before inner holdout.
            inner_window = FoldWindow(
                validation_start=inner_cutoff,
                calibration_start=window.calibration_start,
                test_start=window.test_start,
                final_end=window.final_end,
                embargo_sessions=window.embargo_sessions,
            )
            inner_ids = split_rows(
                selected["training"],
                inner_window,
                config.horizon,
                exchanges,
                [str(i) for i in range(len(selected["training"]))],
            )["training"]
            inner_train = [selected["training"][int(i)] for i in inner_ids]
            inner_validate = [r for r in selected["training"] if r["date"] >= inner_day]
            scores = []
            if len(inner_train) >= 30 and len(inner_validate) >= 10:
                prep = fit_preprocessor(
                    feature_matrix(inner_train, config.feature_names),
                    config.feature_names,
                    config.required_features,
                )
                tx, vx = (
                    transform(feature_matrix(inner_train, config.feature_names), prep),
                    transform(feature_matrix(inner_validate, config.feature_names), prep),
                )
                ty, vy = (
                    [float(r["target"][config.target]) for r in inner_train],
                    [float(r["target"][config.target]) for r in inner_validate],
                )
                if config.model_type not in CLASSIFIERS or len(set(ty)) == 2:
                    for complexity in (
                        [1] if config.model_type == "LINEAR" else config.search_complexities
                    ):
                        model = fit_estimator(config.model_type, tx, ty, config.seed, complexity)
                        predicted = predict_estimator(model, vx)
                        loss = float(np.mean((predicted - vy) ** 2))
                        scores.append({"complexity": complexity, "inner_training_loss": loss})
            chosen = (
                min(scores, key=lambda s: (s["inner_training_loss"], s["complexity"]))["complexity"]
                if scores
                else 1
                if config.model_type == "LINEAR"
                else min(config.search_complexities)
            )
            prep = fit_preprocessor(x["training"], config.feature_names, config.required_features)
            transformed = {k: transform(v, prep) for k, v in x.items()}
            model = fit_estimator(
                config.model_type, transformed["training"], y["training"], config.seed, int(chosen)
            )
            predictions = {
                k: predict_estimator(model, transformed[k])
                for k in ("validation", "calibration", "test")
            }
            classification = config.model_type in CLASSIFIERS
            calibrator = (
                fit_platt(predictions["calibration"], y["calibration"].astype(int))
                if classification
                else {"status": "NOT_APPLICABLE"}
            )
            interval = (
                fit_conformal(
                    y["calibration"],
                    predictions["calibration"],
                    [r["date"] for r in selected["calibration"]],
                    config.horizon,
                    [r["target"]["label_end"][:10] for r in selected["calibration"]],
                )
                if not classification
                else {"status": "NOT_APPLICABLE"}
            )
            if classification and calibrator["status"] == "AVAILABLE":
                predictions["test"] = calibrated(predictions["test"], calibrator)
            metric = classification_metrics if classification else regression_metrics
            test_metrics = metric(y["test"], predictions["test"])
            if interval["status"] == "AVAILABLE":
                interval["empirical_oos_coverage"] = float(
                    np.mean(abs(y["test"] - predictions["test"]) <= interval["radius"])
                )
            baselines = (
                {"constant_50": 0.5, "training_prevalence": float(y["training"].mean())}
                if classification
                else {"zero": 0.0, "training_historical_mean": float(y["training"].mean())}
            )
            baseline_metrics = {
                k: metric(y["test"], np.full(len(y["test"]), v)) for k, v in baselines.items()
            }
            dates = [r["date"] for r in selected["test"]]
            folds.append(
                {
                    "window": window.model_dump(mode="json"),
                    "partitions": partitions,
                    "sample_sizes": {k: len(v) for k, v in selected.items()},
                    "validation_metrics": metric(y["validation"], predictions["validation"]),
                    "test_metrics": test_metrics,
                    "calibration": calibrator,
                    "calibration_distinct_dates": len({r["date"] for r in selected["calibration"]}),
                    "interval": interval,
                    "baselines": baseline_metrics,
                    "search": {
                        "space": config.search_complexities,
                        "scores": scores,
                        "selected_complexity": chosen,
                        "scope": "TRAIN_ONLY_PURGED_INNER_HOLDOUT",
                        "hyperparameters": model_parameters(
                            config.model_type, config.seed, int(chosen)
                        ),
                    },
                    "oos_predictions": [
                        {"row_id": i, "prediction": float(p)}
                        for i, p in zip(partitions["test"], predictions["test"], strict=True)
                    ],
                }
            )
            artifacts.append(
                {
                    "preprocessor": prep,
                    "estimator": model,
                    "calibrator": calibrator,
                    "interval": interval,
                }
            )
            all_y.extend(y["test"].tolist())
            all_predictions.extend(predictions["test"].tolist())
            all_dates.extend(dates)
    classification = config.model_type in CLASSIFIERS
    return {
        "contract": "p7-train-only-four-window-v1",
        "promotion_rules": PROMOTION_RULES,
        "folds": folds,
        "aggregated_oos": (classification_metrics if classification else regression_metrics)(
            all_y, all_predictions
        ),
        "oos_distinct_dates": len(set(all_dates)),
        "uncertainty": block_bootstrap_brier(
            all_y, all_predictions, all_dates, config.horizon, config.seed
        )
        if classification
        else {"status": "NOT_EVALUATED"},
        "artifacts": artifacts,
    }
