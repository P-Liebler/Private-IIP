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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--security-report", type=Path, required=True)
    parser.add_argument("--test-report", type=Path, action="append", required=True)
    parser.add_argument("--restore-status", type=Path, required=True)
    parser.add_argument("--migration-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
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
    validate_artifacts(payload, root)
    payload["content_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    write_new(args.output, payload)
    print("Local RC evidence recorded; no release approval or deployment")


if __name__ == "__main__":
    main()
