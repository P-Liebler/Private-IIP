"""Audit pinned observations without fitting or silently completing financial inputs."""

from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

READINESS_VERSION = "p7-readiness-v1"


def finite_feature(value: Any) -> bool:
    try:
        return value is not None and Decimal(str(value)).is_finite()
    except (InvalidOperation, ValueError):
        return False


def audit_readiness(
    configuration: dict[str, Any],
    rows: list[dict[str, Any]],
    quality: dict[str, Any],
    required_features: list[str],
    horizon: int,
    as_of: datetime,
    partitions: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Eligibility is row-specific; synthetic strict data is never real evidence.

    Partitions must come from a verified chronological split. They are reported,
    never inferred from an arbitrary percentage or shuffled observations.
    """
    missing_features: Counter[str] = Counter()
    exclusions: Counter[str] = Counter()
    eligible_ids: set[str] = set()
    instruments: set[str] = set()
    dates: set[str] = set()
    missing_labels = 0
    malformed = 0
    for index, row in enumerate(rows):
        reasons = list(row.get("exclusions", []))
        if row.get("eligible") is not True:
            reasons.append("P6_HARD_GATE_FAILED")
        for name in required_features:
            feature = row.get("features", {}).get(name, {})
            if feature.get("missing_flag", True) or not finite_feature(feature.get("value")):
                missing_features[name] += 1
                reasons.append("MISSING_REQUIRED_FEATURE")
        target = row.get("target", {})
        try:
            cutoff = datetime.fromisoformat(row["information_cutoff_at"])
            signal = datetime.fromisoformat(target["signal_as_of"])
            start = datetime.fromisoformat(target["label_start"])
            end = datetime.fromisoformat(target["label_end"])
            available = datetime.fromisoformat(target["label_available_at"])
            valid_interval = cutoff <= signal < start < end <= available <= as_of
        except (KeyError, TypeError, ValueError):
            valid_interval = False
        if (
            target.get("status") != "AVAILABLE"
            or target.get("horizon_sessions") != horizon
            or not valid_interval
            or target.get("classification") not in (0, 1)
            or not finite_feature(target.get("excess_return"))
            or not finite_feature(target.get("instrument_return"))
        ):
            missing_labels += 1
            reasons.append("LABEL_UNAVAILABLE_OR_INVALID")
        if target.get("status") == "AVAILABLE" and not valid_interval:
            malformed += 1
        for reason in set(reasons):
            exclusions[reason] += 1
        if not reasons:
            eligible_ids.add(str(index))
            instruments.add(row["instrument_id"])
            dates.add(row["date"])
    synthetic = configuration.get("data_context") == "SYNTHETIC_SIMULATION_NOT_REAL_ARCHIVE"
    strict = configuration.get("availability_mode") == "STRICT_PIT"
    survivorship = quality.get("survivorship_risk", True)
    if malformed or (strict and survivorship):
        status = "DATA_QUALITY_FAILED"
    elif not strict:
        status = "RECONSTRUCTED_RESEARCH_ONLY"
    elif len(dates) < 252 or len(eligible_ids) < 500:
        status = "INSUFFICIENT_HISTORY"
    else:
        status = "STRICT_PIT_ELIGIBLE"
    counts = {name: len(eligible_ids.intersection(ids)) for name, ids in (partitions or {}).items()}
    return {
        "rule_version": READINESS_VERSION,
        "status": status,
        "availability_mode": configuration.get("availability_mode"),
        "data_context": configuration.get("data_context", "UNKNOWN"),
        "universe_id": configuration.get("universe_id"),
        "start": configuration.get("start"),
        "end": configuration.get("end"),
        "horizon_sessions": horizon,
        "total_observations": len(rows),
        "eligible_observations": len(eligible_ids),
        "eligible_row_ids": sorted(eligible_ids, key=int),
        "instruments": len({r["instrument_id"] for r in rows}),
        "eligible_instruments": len(instruments),
        "distinct_signal_dates": len(dates),
        "partition_observations": counts,
        "partition_status": "PINNED_SPLIT" if partitions is not None else "NOT_EVALUATED",
        "missing_features": dict(missing_features),
        "missing_labels": missing_labels,
        "exclusion_reasons": dict(exclusions),
        "survivorship_risk": survivorship,
        "corporate_action_limitations": quality.get("exclusion_reasons", {}),
        "required_features": required_features,
        "production_data_eligible": status == "STRICT_PIT_ELIGIBLE" and not synthetic,
        "synthetic_evidence": synthetic,
        "as_of": as_of.isoformat(),
    }
