"""Classify CI failures without confusing a download failure with a CVE finding."""
import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re

from security_audit import write_new
from security_audit import sha256
from security_policy import evaluate
from release_scope import active_services, evaluate_scope
from ci_full_image_audit import CONFIGURATION_FILES


def read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def dependency_findings(root):
    for name in ("core", "mlflow", "npm"):
        value = read(root / f"pr4-{name}-dependencies.json")
        if not isinstance(value, dict):
            continue
        if name == "npm":
            if value.get("metadata", {}).get("vulnerabilities", {}).get("total", 0) > 0:
                return True
        elif any(dependency.get("vulns") for dependency in value.get("dependencies", [])):
            return True
    return False


def classify(root, steps, full=False):
    record = {"scope": "FULL" if full else "CORE", "steps": steps,
              "release_status": "NOT_APPROVED", "status": "SCAN_INCOMPLETE",
              "core_release_scope_status": "SCAN_INCOMPLETE" if full else "NOT_REQUESTED_NOT_VERIFIED"}
    # Historical evidence is retained independently. It cannot describe the
    # images built in this run; current findings below still fail closed.
    record["historical_inventory_step"] = steps.get("historical", "unknown")
    if steps.get("scanner") != "success":
        record["status"] = "SCANNER_INSTALL_FAILED"
        return record
    database = read(root / "vulnerability-db.json")
    if steps.get("database") != "success" or not database or database.get("status") != "DATABASE_READY":
        state = database.get("status") if database else None
        record["status"] = state if state in {"SCANNER_INSTALL_FAILED", "VULNERABILITY_DB_STALE", "VULNERABILITY_DB_UNAVAILABLE"} else "VULNERABILITY_DB_UNAVAILABLE"
        return record
    record["database_sha256"] = database.get("database_sha256")
    record["database_age_seconds_at_acquisition"] = database.get("age_seconds")
    if dependency_findings(root):
        record["status"] = "DEPENDENCY_VULNERABLE"
        return record
    required = ["contracts", "dependencies", "images", "critical"]
    if full:
        required.append("full")
    for folder in (["pr4-images", "pr4-full-images"] if full else ["pr4-images"]):
        inventory = read(root / folder / "inventory.json")
        if not inventory or not inventory.get("images"):
            return record
        if folder == "pr4-images":
            expected = ["api", "web"]
        else:
            scope = read(root / "pr4-release-scope.json")
            if not scope:
                return record
            expected = list(active_services(scope))
            proof = read(root / folder / "release-scope-audit.json")
            exact = {name: row["image"] for name, row in active_services(scope).items()}
            if (not proof or proof.get("status") != "EXACT_CONFIG_AND_IMAGE_SCOPE_VERIFIED"
                    or proof.get("scope_sha256") != sha256(root / "pr4-release-scope.json")
                    or proof.get("verified_service_images") != exact
                    or not isinstance(proof.get("configuration_sha256"), str)
                    or not re.fullmatch(r"[0-9a-f]{64}", proof["configuration_sha256"])
                    or proof.get("selected_config_files_sha256") != {
                        name: sha256(Path(name)) for name in CONFIGURATION_FILES}):
                return record
            # Do not retain secret-bearing resolved Compose JSON as an artifact.
            # The audit already checked the real configuration; this binds the
            # public exact-image inventory to that selected release scope.
            # Raw scanner inventories call this field database; the public
            # publisher calls the same metadata scanner_database.
            scoped_inventory = {**inventory, "scanner_database": inventory.get("scanner_database", inventory.get("database"))}
            scoped = evaluate_scope(scope, scoped_inventory, {"services": {
                name: {"image": row["image"]} for name, row in active_services(scope).items()}})
            record["core_release_scope_status"] = scoped
            if scoped == "SCAN_INCOMPLETE":
                return record
        policy = evaluate(inventory["images"], expected)
        if policy == "SCAN_INCOMPLETE":
            return record
        if any(finding.get("severity") in {"HIGH", "CRITICAL"} for image in inventory["images"] for finding in image.get("findings", [])):
            record["status"] = "IMAGE_VULNERABLE"
            return record
        sbom = read(root / ("pr4-core-sbom-validation.json" if folder == "pr4-images" else "pr4-full-sbom-validation.json"))
        if not sbom or sbom.get("valid") is not True or not sbom.get("records"):
            return record
        if {row.get("component") for row in sbom["records"] if row.get("valid") is True} != set(expected):
            return record
    if any(steps.get(step) != "success" for step in required):
        return record
    source = read(root / "pr4-source/source-security.json")
    if not source or source.get("status") != "NO_KNOWN_SECRET_FINDINGS" or source.get("finding_count") != 0:
        return record
    for name in ("core", "mlflow", "npm"):
        value = read(root / f"pr4-{name}-dependencies.json")
        if not isinstance(value, dict):
            return record
        if name != "npm" and (not isinstance(value.get("dependencies"), list) or not value["dependencies"]):
            return record
        if name == "npm" and value.get("metadata", {}).get("vulnerabilities", {}).get("total") != 0:
            return record
    record["status"] = "SECURITY_CHECK_PASSED"
    # This checks the requested automated scope, never target-host/operator approval.
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    names = ["scanner", "database", "contracts", "dependencies", "images", "critical", "historical", "full"]
    steps = {name: os.environ.get("SECURITY_" + name.upper() + "_STEP", "unknown") for name in names}
    try:
        record = classify(args.root, steps, os.environ.get("SECURITY_FULL_REQUESTED") == "true")
    except (ValueError, TypeError, KeyError, AttributeError):
        record = {"status": "SCAN_INCOMPLETE", "release_status": "NOT_APPROVED",
                  "reason": "MALFORMED_SECURITY_EVIDENCE", "steps": steps}
    record["recorded_at"] = datetime.now(UTC).isoformat()
    write_new(args.output, record)
    print(record["status"])
    return 0 if record["status"] == "SECURITY_CHECK_PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
