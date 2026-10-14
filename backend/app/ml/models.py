"""Bounded estimators and data-only artifacts. No pickle or executable uploads."""

import json
from typing import Any, Literal

import lightgbm as lgb
import numpy as np
import xgboost as xgb
from scipy.special import expit
from sklearn.linear_model import LinearRegression, LogisticRegression

ModelType = Literal[
    "LOGISTIC",
    "LINEAR",
    "LIGHTGBM_CLASSIFIER",
    "LIGHTGBM_REGRESSOR",
    "XGBOOST_CLASSIFIER",
    "XGBOOST_REGRESSOR",
]
CLASSIFIERS = {"LOGISTIC", "LIGHTGBM_CLASSIFIER", "XGBOOST_CLASSIFIER"}


def model_parameters(kind: str, seed: int, complexity: int) -> dict[str, Any]:
    if kind == "LOGISTIC":
        return {
            "C": (0.1, 1.0, 10.0)[complexity - 1],
            "max_iter": 300,
            "solver": "lbfgs",
            "random_state": seed,
        }
    if kind == "LINEAR":
        return {"n_jobs": 1, "fit_intercept": True}
    return {
        "n_estimators": 50 * complexity,
        "max_depth": 3,
        "learning_rate": 0.05,
        "n_jobs": 1,
        "random_state": seed,
        "backend": "CPU_DETERMINISTIC",
        "num_leaves": 7 if kind.startswith("LIGHTGBM") else None,
    }


def fit_preprocessor(x: Any, names: list[str], required: list[str]) -> dict[str, Any]:
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[1] != len(names) or not len(x) or np.isinf(x).any():
        raise ValueError("INVALID_TRAINING_FEATURES")
    if any(np.isnan(x[:, names.index(name)]).any() for name in required):
        raise ValueError("MISSING_CRITICAL_FINANCIAL_FEATURE")
    medians = []
    for column in x.T:
        if np.isnan(column).all():
            raise ValueError("FEATURE_HAS_NO_TRAINING_OBSERVATIONS")
        medians.append(float(np.nanmedian(column)))
    filled = np.where(np.isnan(x), np.asarray(medians), x)
    means, scales = filled.mean(axis=0), filled.std(axis=0)
    # A constant feature is removed based solely on TRAIN. Missing flags remain.
    retained = [i for i, scale in enumerate(scales) if scale > 0]
    if not retained:
        raise ValueError("NO_VARYING_TRAINING_FEATURES")
    return {
        "contract": "train-only-median-scale-flags-v1",
        "names": names,
        "required": required,
        "medians": medians,
        "means": means.tolist(),
        "scales": scales.tolist(),
        "retained": retained,
        "training_rows": len(x),
    }


def transform(x: Any, parameters: dict[str, Any]) -> Any:
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[1] != len(parameters["names"]) or np.isinf(x).any():
        raise ValueError("INVALID_INFERENCE_FEATURES")
    if any(
        np.isnan(x[:, parameters["names"].index(name)]).any() for name in parameters["required"]
    ):
        raise ValueError("MISSING_CRITICAL_FINANCIAL_FEATURE")
    missing = np.isnan(x)
    filled = np.where(missing, np.asarray(parameters["medians"]), x)
    retained = parameters["retained"]
    scaled = (filled[:, retained] - np.asarray(parameters["means"])[retained]) / np.asarray(
        parameters["scales"]
    )[retained]
    return np.concatenate([scaled, missing.astype(float)], axis=1)


def fit_estimator(
    kind: ModelType, x: Any, y: Any, seed: int, complexity: int = 1
) -> dict[str, Any]:
    if complexity not in (1, 2, 3):
        raise ValueError("SEARCH_SPACE_LIMIT")
    y = np.asarray(y)
    if kind in CLASSIFIERS and len(np.unique(y)) != 2:
        raise ValueError("TRAINING_REQUIRES_TWO_CLASSES")
    if kind == "LOGISTIC":
        estimator = LogisticRegression(
            C=(0.1, 1.0, 10.0)[complexity - 1], max_iter=300, random_state=seed
        )
        estimator.fit(x, y)
        return {
            "type": kind,
            "coefficients": estimator.coef_[0].tolist(),
            "intercept": float(estimator.intercept_[0]),
        }
    if kind == "LINEAR":
        estimator = LinearRegression(n_jobs=1).fit(x, y)
        return {
            "type": kind,
            "coefficients": estimator.coef_.tolist(),
            "intercept": float(estimator.intercept_),
        }
    params: dict[str, Any] = {
        "n_estimators": 50 * complexity,
        "max_depth": 3,
        "learning_rate": 0.05,
        "n_jobs": 1,
        "random_state": seed,
    }
    if kind.startswith("LIGHTGBM"):
        factory = lgb.LGBMClassifier if kind in CLASSIFIERS else lgb.LGBMRegressor
        estimator = factory(
            **params,
            num_leaves=7,
            min_child_samples=10,
            deterministic=True,
            force_col_wise=True,
            verbosity=-1,
        ).fit(x, y)
        return {"type": kind, "native_model": estimator.booster_.model_to_string()}
    if kind.startswith("XGBOOST"):
        factory = xgb.XGBClassifier if kind in CLASSIFIERS else xgb.XGBRegressor
        estimator = factory(**params, tree_method="hist", device="cpu").fit(x, y)
        return {
            "type": kind,
            "native_model": json.loads(estimator.get_booster().save_raw(raw_format="json")),
        }
    raise ValueError("MODEL_TYPE_NOT_ALLOWED")


def predict_estimator(model: dict[str, Any], x: Any) -> Any:
    if model["type"] in {"LOGISTIC", "LINEAR"}:
        value = np.asarray(x) @ np.asarray(model["coefficients"]) + model["intercept"]
        return expit(value) if model["type"] == "LOGISTIC" else value
    if model["type"].startswith("LIGHTGBM"):
        return lgb.Booster(model_str=model["native_model"]).predict(x, num_threads=1)
    if model["type"].startswith("XGBOOST"):
        booster = xgb.Booster(params={"nthread": 1})
        booster.load_model(bytearray(json.dumps(model["native_model"]).encode()))
        return booster.predict(xgb.DMatrix(x))
    raise ValueError("MODEL_TYPE_NOT_ALLOWED")
