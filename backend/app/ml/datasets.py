"""Bounded multi-year composition of already immutable P6 windows."""

from datetime import date, timedelta
from typing import Any

from app.services.fundamentals import digest

COMPOSITION_VERSION = "p7-pinned-window-composition-v1"
COMPATIBLE = (
    "universe_id",
    "benchmark_id",
    "availability_mode",
    "feature_set_version",
    "target_horizon",
    "base_currency",
    "data_context",
)
POLICIES = (
    "calendar_version",
    "feature_version",
    "target_version",
    "action_policy",
    "execution_policy",
    "fx_policy",
    "availability_policy",
    "quality_policy",
    "git_commit",
    "code_hash",
    "dependencies",
)


def compose_windows(windows: list[dict[str, Any]]) -> dict[str, Any]:
    if not 2 <= len(windows) <= 8:
        raise ValueError("COMPOSITION_WINDOW_LIMIT")
    windows = sorted(windows, key=lambda w: w["configuration"]["start"])
    first = windows[0]
    configuration = dict(first["configuration"])
    manifest = {key: first["manifest"][key] for key in POLICIES}
    manifest.update({"versions": {}, "version_hashes": {}, "market": {}, "actions": {}})
    feature_ids: set[str] = set()
    coverage_ids: set[str] = set()
    rows = []
    exclusions: dict[str, int] = {}
    previous_end = None
    for window in windows:
        config, pinned = window["configuration"], window["manifest"]
        if config.get("composition_version"):
            raise ValueError("NESTED_COMPOSITION_FORBIDDEN")
        if any(config.get(k) != configuration.get(k) for k in COMPATIBLE):
            raise ValueError("WINDOW_CONFIGURATION_MISMATCH")
        if any(pinned.get(k) != manifest.get(k) for k in POLICIES):
            raise ValueError("WINDOW_POLICY_MISMATCH")
        start, end = date.fromisoformat(config["start"]), date.fromisoformat(config["end"])
        if start > end or (previous_end and start != previous_end + timedelta(days=1)):
            raise ValueError("WINDOW_GAP_OR_OVERLAP")
        previous_end = end
        if any(not config["start"] <= r["date"] <= config["end"] for r in window["rows"]):
            raise ValueError("ROW_OUTSIDE_WINDOW")
        rows.extend(window["rows"])
        if len(rows) > 30_000:
            raise ValueError("COMPOSITION_ROW_LIMIT")
        feature_ids.update(pinned["feature_snapshot_ids"])
        coverage_ids.update(pinned["coverage_ids"])
        for kind, entries in pinned["version_hashes"].items():
            hashes = manifest["version_hashes"].setdefault(kind, {})
            for key, value in entries.items():
                if key in hashes and hashes[key] != value:
                    raise ValueError("PINNED_VERSION_CONFLICT")
                hashes[key] = value
        for day, bars in pinned["market"].items():
            if day in manifest["market"]:
                raise ValueError("MARKET_WINDOW_OVERLAP")
            manifest["market"][day] = bars
        for iid, actions in pinned["actions"].items():
            target = manifest["actions"].setdefault(iid, {})
            for action in actions:
                if action["id"] in target and target[action["id"]] != action:
                    raise ValueError("PINNED_ACTION_CONFLICT")
                target[action["id"]] = action
        for reason, count in window["quality"].get("exclusion_reasons", {}).items():
            exclusions[reason] = exclusions.get(reason, 0) + count
    if len({(r["date"], r["instrument_id"]) for r in rows}) != len(rows):
        raise ValueError("DUPLICATE_OBSERVATION")
    configuration.update(
        {
            "end": windows[-1]["configuration"]["end"],
            "composition_version": COMPOSITION_VERSION,
            "window_ids": [w["id"] for w in windows],
        }
    )
    if (
        date.fromisoformat(configuration["end"]) - date.fromisoformat(configuration["start"])
    ).days > 5844:
        raise ValueError("COMPOSITION_TIME_LIMIT")
    manifest["windows"] = [{"id": w["id"], "content_hash": w["content_hash"]} for w in windows]
    manifest["versions"] = {k: sorted(v) for k, v in manifest["version_hashes"].items()}
    manifest["feature_snapshot_ids"] = sorted(feature_ids)
    manifest["coverage_ids"] = sorted(coverage_ids)
    manifest["actions"] = {
        k: sorted(v.values(), key=lambda a: (a["date"], a["id"]))
        for k, v in manifest["actions"].items()
    }
    manifest["universe_id"] = configuration["universe_id"]
    quality = {
        key: sum(w["quality"].get(key, 0) for w in windows)
        for key in (
            "total_observations",
            "valid_observations",
            "excluded_observations",
            "missing_features",
            "unavailable_targets",
        )
    }
    quality.update(
        {
            "exclusion_reasons": exclusions,
            "survivorship_risk": any(w["quality"].get("survivorship_risk", True) for w in windows),
        }
    )
    result = {
        "configuration": configuration,
        "manifest": manifest,
        "rows": rows,
        "quality": quality,
    }
    return {**result, "content_hash": digest(result)}
