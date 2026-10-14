from datetime import datetime
from decimal import Decimal
from typing import Any


def no_skill() -> Decimal:
    return Decimal("0.5")


def train_only_baselines(
    training: list[dict[str, Any]], training_cutoff: datetime
) -> dict[str, str | None]:
    for row in training:
        if (
            row["partition"] != "training"
            or datetime.fromisoformat(row["label_available_at"]) > training_cutoff
        ):
            raise ValueError("BASELINE_TRAINING_LEAKAGE")
    labels = [Decimal(str(r["label"])) for r in training if r.get("label") is not None]
    excess = [
        Decimal(str(r["excess_return"])) for r in training if r.get("excess_return") is not None
    ]
    return {
        "constant_50": "0.5",
        "prevalence": str(sum(labels) / len(labels)) if labels else None,
        "zero_excess_return": "0",
        "historical_mean": str(sum(excess) / len(excess)) if excess else None,
    }


def ranking(rows: list[dict[str, Any]], strategy: str, top_n: int) -> list[str]:
    if strategy == "EQUAL_WEIGHT":
        return sorted(str(r["instrument_id"]) for r in rows)
    key = (
        "ml_score"
        if strategy == "ML_SCORE"
        else "momentum_120d"
        if strategy == "MOMENTUM"
        else "quality_value"
    )
    eligible = [
        r
        for r in rows
        if r["features"].get(key, {}).get("value") is not None
        and not r["features"][key].get("missing_flag", True)
    ]
    eligible.sort(
        key=lambda r: (-Decimal(str(r["features"][key]["value"])), str(r["instrument_id"]))
    )
    return [str(r["instrument_id"]) for r in eligible[:top_n]]
