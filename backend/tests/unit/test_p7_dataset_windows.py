from copy import deepcopy

import pytest

from app.ml.datasets import COMPATIBLE, POLICIES, compose_windows


def window(identifier, start, end):
    config = dict.fromkeys(COMPATIBLE, "same")
    config.update({"start": start, "end": end})
    manifest = dict.fromkeys(POLICIES, "same")
    manifest.update(
        {
            "versions": {},
            "version_hashes": {},
            "market": {},
            "actions": {},
            "feature_snapshot_ids": [],
            "coverage_ids": [],
        }
    )
    return {
        "id": identifier,
        "content_hash": identifier,
        "configuration": config,
        "manifest": manifest,
        "rows": [],
        "quality": {"survivorship_risk": False},
    }


def test_multi_year_pinned_windows_deterministic_and_immutable():
    a, b = window("a", "2020-01-01", "2021-12-31"), window("b", "2022-01-01", "2023-12-31")
    before = deepcopy([a, b])
    result = compose_windows([a, b])
    assert result == compose_windows([b, a])
    assert [a, b] == before
    assert result["configuration"]["window_ids"] == ["a", "b"]
    assert result["configuration"]["end"] == "2023-12-31"


@pytest.mark.parametrize("start", ["2021-12-31", "2022-01-02"])
def test_gap_and_overlap_rejected(start):
    with pytest.raises(ValueError, match="WINDOW_GAP_OR_OVERLAP"):
        compose_windows([window("a", "2020-01-01", "2021-12-31"), window("b", start, "2023-12-31")])


def test_changed_policy_rejected():
    a, b = window("a", "2020-01-01", "2021-12-31"), window("b", "2022-01-01", "2023-12-31")
    b["manifest"]["fx_policy"] = "different"
    with pytest.raises(ValueError, match="WINDOW_POLICY_MISMATCH"):
        compose_windows([a, b])


def test_nested_composition_and_unbounded_windows_rejected():
    a, b = window("a", "2020-01-01", "2021-12-31"), window("b", "2022-01-01", "2023-12-31")
    a["configuration"]["composition_version"] = "v1"
    with pytest.raises(ValueError, match="NESTED_COMPOSITION"):
        compose_windows([a, b])
    with pytest.raises(ValueError, match="COMPOSITION_WINDOW_LIMIT"):
        compose_windows([b] * 9)
