"""Bind runtime and recovery images to an explicit release scope.

Historical reporting never grants approval. Active evaluation uses the unchanged
High/Critical policy and requires exact service, image and configuration sets.
"""
import argparse
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import re

from security_audit import sha256, write_new
from security_policy import evaluate

REFERENCE = re.compile(r"[A-Za-z0-9_./:-]+@sha256:[0-9a-f]{64}\Z")
ROLES = {"runtime", "recovery", "optional", "migration_source", "archive"}
CORE_REQUIRED = {"api", "web", "worker", "scheduler", "postgres", "valkey", "minio",
                 "caddy", "ca-export", "prometheus", "backup", "storage-init", "legacy-verifier"}
CORE_REQUIRED_V2 = CORE_REQUIRED - {"legacy-verifier"}
CORE_RECOVERY = "PRIVATE_CORE_ARCHIVE_RECOVERY_V1"


def validate_archive_recovery(scope):
    recovery = scope.get("archive_recovery", {})
    legacy = scope.get("services", {}).get("legacy-verifier", {})
    if (recovery.get("contract") != CORE_RECOVERY or recovery.get("checked_pins") != 66
            or recovery.get("current_expectations_contract") != "PRIVATE_CORE_RESTORE_EXPECTATIONS_V1"
            or recovery.get("historical_runtime_execution") != "NOT_EXECUTED_NOT_PROVEN"
            or recovery.get("optional_dynamic_legacy_status") != "SECURITY_BLOCKED"
            or legacy.get("role") != "archive" or legacy.get("enabled") is not False):
        raise ValueError("CORE_ARCHIVE_RECOVERY_CONTRACT_REQUIRED")
    for name in ("original_manifest_sha256", "metadata_bundle_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", recovery.get(name, "")):
            raise ValueError("CORE_ARCHIVE_RECOVERY_ANCHOR_REQUIRED")
    for name in ("original_manifest_reference", "original_static_reference", "historical_inventory_reference"):
        value = recovery.get(name)
        if (not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_./-]+", value)
                or value.startswith("/") or any(part in {"", ".", ".."} for part in value.split("/"))):
            raise ValueError("CORE_ARCHIVE_RECOVERY_REFERENCE_REJECTED")
    return recovery


def validate_scope(scope):
    contract = scope.get("contract")
    if contract not in {"PRIVATE_CORE_SCOPE_V1", "PRIVATE_CORE_SCOPE_V2"}:
        raise ValueError("UNSUPPORTED_RELEASE_SCOPE")
    services = scope.get("services")
    if not isinstance(services, dict) or not services:
        raise ValueError("EMPTY_RELEASE_SCOPE")
    for name, row in services.items():
        if (not re.fullmatch(r"[a-z][a-z0-9-]*", name)
                or row.get("role") not in ROLES
                or not REFERENCE.fullmatch(row.get("image", ""))
                or not row.get("reason")
                or not isinstance(row.get("enabled"), bool)):
            raise ValueError("INVALID_RELEASE_SERVICE")
        if row["role"] in {"runtime", "recovery"} and not row["enabled"]:
            raise ValueError("REQUIRED_SERVICE_DISABLED")
        if row["role"] in {"archive", "migration_source"} and row["enabled"]:
            raise ValueError("LEGACY_SERVICE_CANNOT_BE_ACTIVE")
    if not any(row["role"] == "recovery" for row in services.values()):
        raise ValueError("RECOVERY_SCOPE_REQUIRED")
    required = CORE_REQUIRED if contract == "PRIVATE_CORE_SCOPE_V1" else CORE_REQUIRED_V2
    if not required <= {name for name, row in services.items() if row["enabled"]}:
        raise ValueError("CORE_SERVICE_OMITTED")
    if contract == "PRIVATE_CORE_SCOPE_V2":
        validate_archive_recovery(scope)
    return services


def active_services(scope):
    return {name: row for name, row in validate_scope(scope).items() if row["enabled"]}


def evaluate_scope(scope, inventory, config):
    try:
        updated = datetime.fromisoformat(inventory["scanner_database"]["UpdatedAt"].replace("Z", "+00:00"))
        now = datetime.now(UTC)
        if updated.tzinfo is None or not timedelta(0) <= now - updated <= timedelta(hours=48):
            return "SCAN_INCOMPLETE"
    except (KeyError, TypeError, ValueError, AttributeError):
        return "SCAN_INCOMPLETE"
    required = active_services(scope)
    configured = config.get("services", {})
    # Caller resolves only the selected profiles; an extra started service fails.
    if set(configured) != set(required):
        return "SCAN_INCOMPLETE"
    for name, row in required.items():
        service = configured[name]
        if service.get("image") != row["image"] or service.get("build"):
            return "SCAN_INCOMPLETE"
    images = inventory.get("images", [])
    if {row.get("component") for row in images} != set(required):
        return "SCAN_INCOMPLETE"
    for image in images:
        reference = required[image["component"]]["image"]
        if (image.get("image_reference") != reference
                or image.get("image_id") != reference.split("@", 1)[1]):
            return "SCAN_INCOMPLETE"
    return evaluate(images, list(required))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    historical = sub.add_parser("historical")
    historical.add_argument("inventory", type=Path)
    historical.add_argument("--output", type=Path, required=True)
    active = sub.add_parser("evaluate")
    active.add_argument("--scope", type=Path, required=True)
    active.add_argument("--inventory", type=Path, required=True)
    active.add_argument("--config", type=Path, required=True)
    active.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = {"release_status": "NOT_APPROVED"}
    if args.action == "historical":
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        record.update(kind="HISTORICAL_ONLY", inventory_sha256=sha256(args.inventory),
                      status=evaluate(inventory["images"], [i["component"] for i in inventory["images"]]))
        # Reporting succeeded; the immutable historical failure remains visible.
        code = 0
    else:
        try:
            scope = json.loads(args.scope.read_text(encoding="utf-8"))
            inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
            config = json.loads(args.config.read_text(encoding="utf-8"))
            record.update(kind="ACTIVE_SCOPE", scope_sha256=sha256(args.scope),
                          configuration_sha256=hashlib.sha256(args.config.read_bytes()).hexdigest(),
                          status=evaluate_scope(scope, inventory, config))
        except (OSError, ValueError, KeyError, TypeError):
            record.update(kind="ACTIVE_SCOPE", status="SCAN_INCOMPLETE")
        code = 2 if record["status"] == "SCAN_INCOMPLETE" else 1
    write_new(args.output, record)
    print(record["status"])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
