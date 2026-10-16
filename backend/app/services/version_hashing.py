"""Exact, versioned row serialization for archived P6 content hashes."""

from typing import Any

from app.core.errors import AppError
from app.services.pit_features import json_value

# The v1 archive predates migration 0018. Only these exact migration defaults
# may be absent from its hash. Non-default additions fail, rather than disappear.
V1_ADDITIONS: dict[str, dict[str, Any]] = {
    "coverage": {"action_types": ["SPLIT", "DIVIDEND"], "coverage_evidence": None},
    "action": {"event_details": None},
    "macro": {
        "frequency": None,
        "provider_series": None,
        "release_date": None,
        "revision_type": None,
    },
}


def version_payload(row: Any, kind: str, fields: list[str] | None) -> dict[str, Any]:
    values = {column.name: getattr(row, column.name) for column in row.__table__.columns}
    if fields is None:
        for name, default in V1_ADDITIONS.get(kind, {}).items():
            if values[name] != default:
                raise AppError(
                    409, "PINNED_VERSION_CHANGED", "Legacy input has non-default added metadata"
                )
            del values[name]
    elif len(fields) != len(set(fields)) or set(fields) != set(values):
        raise AppError(409, "PINNED_VERSION_SCHEMA_CHANGED", "Pinned row field set changed")
    result: dict[str, Any] = json_value(values)
    return result
