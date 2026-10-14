from typing import Any

import lightgbm as lgb
import numpy as np
import xgboost as xgb


def explain(model: dict[str, Any], x: Any, preprocessing: dict[str, Any]) -> dict[str, Any]:
    names = preprocessing["names"]
    transformed_names = [names[i] for i in preprocessing["retained"]] + [
        n + " missing flag" for n in names
    ]
    if "coefficients" in model:
        contributions = x[0] * np.asarray(model["coefficients"])
        method = "linear-score-contributions"
    elif model["type"].startswith("LIGHTGBM"):
        contributions = lgb.Booster(model_str=model["native_model"]).predict(
            x, pred_contrib=True, num_threads=1
        )[0][:-1]
        method = "native-tree-shap"
    else:
        import json

        booster = xgb.Booster(params={"nthread": 1})
        booster.load_model(bytearray(json.dumps(model["native_model"]).encode()))
        contributions = booster.predict(xgb.DMatrix(x), pred_contribs=True)[0][:-1]
        method = "native-tree-shap"
    factors = [
        {"feature": name, "transformed_value": float(value), "contribution": float(contribution)}
        for name, value, contribution in zip(transformed_names, x[0], contributions, strict=True)
    ]
    return {
        "method": method,
        "positive_factors": [f for f in factors if f["contribution"] > 0],
        "negative_factors": [f for f in factors if f["contribution"] < 0],
        "interpretation": (
            "Associations on the model score scale before probability calibration; "
            "no causal inference"
        ),
    }
