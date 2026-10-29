"""Create append-only local RC evidence; it never publishes or deploys a release."""
import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
from security_audit import sha256, write_new


def source_snapshot(root, excluded=()):
    """Bind Git-visible source bytes, including uncommitted work, without ignored secrets."""
    names = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root
    ).decode("utf-8").split("\0")
    result = {}
    for name in sorted(set(names) - {"", *excluded}):
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("UNSAFE_RELEASE_SOURCE_PATH")
        if path.is_file():
            result[name] = sha256(path)
    return result


def validate_manifest(manifest, root):
    payload = {key: value for key, value in manifest.items() if key != "content_sha256"}
    actual = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if actual != manifest.get("content_sha256"):
        raise ValueError("RELEASE_MANIFEST_MISMATCH")
    validate_artifacts(manifest, root)
    for name, expected in manifest.get("source_file_hashes", {}).items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or sha256(path) != expected:
            raise ValueError("RELEASE_SOURCE_MISMATCH")
    if not manifest.get("source_file_hashes"):
        raise ValueError("RELEASE_SOURCE_NOT_BOUND")
    actual_sources = source_snapshot(root, manifest.get("source_excluded_paths", ()))
    if actual_sources != manifest["source_file_hashes"]:
        raise ValueError("RELEASE_SOURCE_SET_MISMATCH")


def validate_artifacts(manifest, root):
    for name, expected in manifest["artifact_hashes"].items():
        source = (root / name).resolve()
        if not source.is_relative_to(root.resolve()) or sha256(source) != expected:
            raise ValueError("RELEASE_ARTIFACT_MISMATCH")


def validate_scoped_restore(expected, restore, scope=None, expectations=None):
    """A successful restore of another candidate cannot establish this scope."""
    restored = restore.get("image_contract", {})
    aliases = {"api": "api", "postgres": "postgres", "object_store": "minio", "s3_client": "backup"}
    if not isinstance(restored, dict) or any(
        restored.get(name) != expected.get(service) or not expected.get(service)
        for name, service in aliases.items()
    ):
        raise ValueError("RELEASE_SCOPE_RESTORE_MISMATCH")
    if "legacy-verifier" in expected:
        legacy = restore.get("legacy_verification", {})
        if (not isinstance(legacy, dict) or legacy.get("verified") is not True
                or legacy.get("image") != expected["legacy-verifier"]
                or legacy.get("network") != "none" or legacy.get("read_only") is not True):
            raise ValueError("RELEASE_SCOPE_LEGACY_RESTORE_MISMATCH")
    if scope and scope.get("contract") == "PRIVATE_CORE_SCOPE_V2":
        from release_scope import validate_archive_recovery
        from verify_archive_recovery import ARCHIVES, HASH, CORE_EXPECTATIONS, core_expectations
        required = validate_archive_recovery(scope)
        integrity = restore.get("archive_integrity", {})
        verified = restore.get("restored_contract_verification", {})
        raw = restore.get("restored_raw_verification", {})
        if (restore.get("success") is not True or restore.get("cleanup_success") is not True
                or restore.get("recovery_contract") != required["contract"]
                or restore.get("restore_expectations_contract") != CORE_EXPECTATIONS
                or not HASH.fullmatch(restore.get("restore_expectations_sha256", ""))
                or not HASH.fullmatch(restore.get("backup_manifest_sha256", ""))
                or integrity.get("contract") != required["contract"]
                or integrity.get("original_manifest_sha256") != required["original_manifest_sha256"]
                or integrity.get("metadata_bundle_sha256") != required["metadata_bundle_sha256"]
                or integrity.get("historical_image") != scope["services"]["legacy-verifier"]["image"]
                or integrity.get("checked_pins") != 66
                or integrity.get("archive_bytes_verified") is not True
                or integrity.get("original_metadata_verified") is not True
                or integrity.get("historical_image_started") is not False
                or integrity.get("archived_package_code_imported") is not False
                or integrity.get("historical_runtime_execution") != "NOT_EXECUTED_NOT_PROVEN"
                or integrity.get("optional_dynamic_legacy_status") != "SECURITY_BLOCKED"
                or "legacy_verification" in restore
                or set(restore.get("archive_contracts", {})) != ARCHIVES
                or any(not HASH.fullmatch(value or "") for value in restore["archive_contracts"].values())
                or integrity.get("artifact_sha256") != restore["archive_contracts"]["model"]
                or verified.get("all_archive_contracts_verified") != sorted(ARCHIVES)
                or verified.get("database_and_object_store_checks_executed") is not True
                or verified.get("database_restored") is not True or verified.get("object_store_restored") is not True
                or verified.get("model_envelope_origin") != "THIS_RESTORED_DATABASE_AND_OBJECT_STORE"
                or verified.get("supplied_restore_receipt_used_as_fresh_evidence") is not False
                or not HASH.fullmatch(verified.get("fixture_verifier_output_sha256", ""))
                or type(raw.get("objects")) is not int or raw["objects"] < 1
                or raw["objects"] != restore.get("raw_object_count")
                or not HASH.fullmatch(raw.get("content_sha256", ""))):
            raise ValueError("RELEASE_SCOPE_CORE_ARCHIVE_RESTORE_MISMATCH")
        if not isinstance(expectations, dict):
            raise ValueError("RELEASE_SCOPE_CURRENT_EXPECTATIONS_REQUIRED")
        core_expectations(expectations, restore)
        try:
            recorded = datetime.fromisoformat(expectations["recorded_at"].replace("Z", "+00:00"))
            started = datetime.fromisoformat(restore["started_at"].replace("Z", "+00:00"))
            if recorded.tzinfo is None or started.tzinfo is None or recorded > started:
                raise ValueError
        except (KeyError, ValueError, TypeError, AttributeError):
            raise ValueError("RELEASE_SCOPE_EXPECTATIONS_NOT_PRE_RESTORE") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--security-report", type=Path, required=True)
    parser.add_argument("--test-report", type=Path, action="append", required=True)
    parser.add_argument("--restore-status", type=Path, required=True)
    parser.add_argument("--restore-expectations", type=Path,
                        help="V2: exact independently retained pre-restore current-backup checkpoint")
    parser.add_argument("--migration-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release-scope", type=Path, help="PR8 exact runtime and recovery scope")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", args.id):
        raise ValueError("INVALID_RC_ID")
    root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()).resolve()
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    restore = json.loads(args.restore_status.read_text(encoding="utf-8"))
    if restore.get("success") is not True or restore.get("cleanup_success") is not True:
        raise ValueError("RESTORE_NOT_VERIFIED")
    references = [args.inventory, args.security_report, args.restore_status, *args.test_report,
                  Path("backend/requirements.lock"), Path("backend/requirements-assistant.lock"),
                  Path("backend/requirements-mlflow.lock"), Path("frontend/web/package-lock.json")]
    if args.release_scope:
        references.extend([args.release_scope, Path("docker-compose.prod.yml"),
                           Path("ops/docker-compose.core.yml"), Path("ops/caddy/Core.Caddyfile")])
    if args.restore_expectations:
        references.append(args.restore_expectations)
    artifacts = {}
    for reference in references:
        resolved = reference.resolve()
        if not resolved.is_relative_to(root):
            raise ValueError("RC_REFERENCE_OUTSIDE_WORKSPACE")
        artifacts[resolved.relative_to(root).as_posix()] = sha256(resolved)
    images = {}
    sboms = {}
    service_images = {}
    aliases = {"backend": ("api", "worker", "scheduler", "ml-worker"),
               "caddy": ("caddy", "ca-export"), "minio": ("minio", "backup")}
    for image in inventory["images"]:
        if image.get("scan_status") != "SCANNED_EXACT_IMAGE":
            raise ValueError("RC_SCAN_INCOMPLETE")
        images[image["component"]] = {key: image[key] for key in ("image_reference", "image_id", "config_digest")}
        sboms[image["component"]] = image["sbom_sha256"]
        reference = image["image_reference"].split("@")[0]
        repository = reference.rsplit(":", 1)[0] if ":" in reference.rsplit("/", 1)[-1] else reference
        for service in aliases.get(image["component"], (image["component"],)):
            service_images[service] = repository + "@" + image["image_id"]
    scope_fields = {}
    if args.release_scope:
        from release_scope import active_services
        scope = json.loads(args.release_scope.read_text(encoding="utf-8"))
        expected = {name: row["image"] for name, row in active_services(scope).items()}
        by_component = {row["component"]: row for row in inventory["images"]}
        if set(by_component) != set(expected) or any(
            by_component[name].get("image_reference") != reference
            or by_component[name].get("image_id") != reference.split("@")[1]
            for name, reference in expected.items()
        ):
            raise ValueError("RELEASE_SCOPE_INVENTORY_MISMATCH")
        expectations = None
        if scope["contract"] == "PRIVATE_CORE_SCOPE_V2":
            from verify_archive_recovery import current_expectations
            if args.restore_expectations is None:
                raise ValueError("RELEASE_SCOPE_CURRENT_EXPECTATIONS_REQUIRED")
            expectations = current_expectations(args.restore_expectations,
                restore.get("restore_expectations_sha256"), scope["archive_recovery"]["original_manifest_sha256"],
                restore.get("archive_contracts", {}).get("model"))
        validate_scoped_restore(expected, restore, scope, expectations)
        service_images = expected
        scope_fields = {"release_scope_reference": args.release_scope.resolve().relative_to(root).as_posix(),
                        "release_scope_sha256": sha256(args.release_scope),
                        "configuration_contract_version": scope["contract"]}
        if scope["contract"] == "PRIVATE_CORE_SCOPE_V2":
            scope_fields["archive_recovery_contract"] = scope["archive_recovery"]
            scope_fields["restore_expectations_reference"] = args.restore_expectations.resolve().relative_to(root).as_posix()
            scope_fields["restore_expectations_sha256"] = sha256(args.restore_expectations)
    output_name = args.output.resolve().relative_to(root).as_posix()
    sources = source_snapshot(root, (output_name,))
    payload = {
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "working_tree_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()),
        "source_file_hashes": sources,
        "source_excluded_paths": [output_name],
        "source_content_sha256": hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "release_candidate_id": args.id, "build_timestamp": datetime.now(UTC).isoformat(),
        "image_digests": images, "sbom_hashes": sboms, "artifact_hashes": artifacts,
        "dependency_lock_hashes": {name: value for name, value in artifacts.items()
                                   if name.endswith((".lock", "package-lock.json"))},
        "inventory_reference": args.inventory.resolve().relative_to(root).as_posix(),
        "security_report_reference": args.security_report.resolve().relative_to(root).as_posix(),
        "security_report_hash": sha256(args.security_report),
        "test_report_references": [path.resolve().relative_to(root).as_posix() for path in args.test_report],
        "restore_verification_reference": args.restore_status.resolve().relative_to(root).as_posix(),
        "service_image_digests": service_images,
        "database_migration_head": args.migration_head, "configuration_contract_version": "PR4-1",
        "security_status": inventory["security_status"], "target_status": "TARGET_HOST_NOT_VERIFIED",
        "release_status": "NOT_RELEASED_OPERATOR_AND_SECURITY_GATES_REQUIRED",
        "source_status": "UNCHANGED_SOURCE_GATES", "forecast_status": "FORECASTS_SHADOW_ONLY",
        "real_data_status": "REAL_DATA_LIMITED",
        "recommendation_status": "RECOMMENDATIONS_GATED",
    }
    payload.update(scope_fields)
    validate_artifacts(payload, root)
    payload["content_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    write_new(args.output, payload)
    print("Local RC evidence recorded; no release approval or deployment")


if __name__ == "__main__":
    main()
