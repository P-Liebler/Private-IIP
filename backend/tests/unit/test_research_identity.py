from copy import deepcopy
from datetime import UTC, datetime

from app.services.research import snapshot_identity


def test_live_refresh_identity_preserves_inputs_rules_and_eligibility() -> None:
    first = {
        "as_of": "2026-10-13T12:00:00+00:00",
        "facts": [{"id": "original"}],
        "scores": {"Quality": {"as_of": "now", "score": 40}},
        "rule_version": "v1",
        "price": {"id": "p1"},
        "status": "PARTIAL",
    }
    later = deepcopy(first)
    later["as_of"] = "2026-10-13T12:01:00+00:00"
    later["scores"]["Quality"]["as_of"] = "later"
    assert snapshot_identity(first, None) == snapshot_identity(later, None)
    for key, replacement in [
        ("facts", [{"id": "restated"}]),
        ("price", {"id": "p2"}),
        ("rule_version", "v2"),
        ("status", "STALE"),
    ]:
        changed = deepcopy(later)
        changed[key] = replacement
        assert snapshot_identity(first, None) != snapshot_identity(changed, None)
    assert snapshot_identity(first, datetime(2026, 10, 12, tzinfo=UTC)) != snapshot_identity(
        first, datetime(2026, 10, 13, tzinfo=UTC)
    )
