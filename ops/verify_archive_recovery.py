"""Verify supplied artifact/image metadata; compare a separately supplied receipt.

This optional integrity contract does not satisfy or replace the required legacy
runtime contract. No restored database or object store is accessed and no fresh
restore is proven. The operator supplies the original manifest's independently
retained SHA-256; expected values never come from the new envelope or receipt.
"""
import argparse
import base64
import hashlib
import json
import io
from pathlib import Path
import re
import tarfile
from datetime import UTC, datetime

from security_audit import sha256, write_new
from verify_archive_metadata import LIMIT, LOCKS, from_image, metadata_paths, verify_metadata

ARCHIVES = {"dataset", "model", "predictions", "risk", "recommendations", "intelligence",
            "document_removals", "ui_requests", "collections", "validation"}
HASH = re.compile(r"[0-9a-f]{64}\Z")
STATIC_FIELDS = ("artifact_sha256", "historical_image", "historical_sbom_sha256",
                 "core_lock_sha256", "support_lock_sha256", "metadata_manifest_sha256",
                 "supporting_archive_contract", "checked_pins")
CORE_RECOVERY = "PRIVATE_CORE_ARCHIVE_RECOVERY_V1"
CORE_EXPECTATIONS = "PRIVATE_CORE_RESTORE_EXPECTATIONS_V1"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def read_json(path, limit=2_000_000):
    with path.open("rb") as stream:
        body = stream.read(limit + 1)
    if len(body) > limit:
        raise ValueError("ARCHIVE_EVIDENCE_LIMIT")
    return json.loads(body), hashlib.sha256(body).hexdigest()


def original_reference(root, manifest, name):
    """Only hash-bound original references inside the frozen manifest are anchors."""
    path = root / name
    if (not isinstance(name, str) or path.is_symlink()
            or not path.resolve().is_relative_to(root.resolve()) or not path.is_file()):
        raise ValueError("ARCHIVE_ORIGINAL_REFERENCE_REJECTED")
    expected = [mapping[name] for key in ("source_file_hashes", "artifact_hashes")
                if name in (mapping := manifest.get(key, {}))]
    value, actual = read_json(path)
    if not expected or any(actual != item for item in expected):
        raise ValueError("ARCHIVE_ORIGINAL_REFERENCE_MISMATCH")
    return value, actual


def prepare(envelope, root, manifest_path, manifest_sha256, static_reference, restored_path):
    if not HASH.fullmatch(manifest_sha256):
        raise ValueError("ARCHIVE_INDEPENDENT_MANIFEST_HASH_REQUIRED")
    manifest, actual = read_json(manifest_path)
    if actual != manifest_sha256:
        raise ValueError("ARCHIVE_ORIGINAL_MANIFEST_HASH_MISMATCH")
    if digest({k: v for k, v in manifest.items() if k != "content_sha256"}) != manifest.get("content_sha256"):
        raise ValueError("ARCHIVE_ORIGINAL_MANIFEST_CONTENT_MISMATCH")
    baseline, baseline_hash = original_reference(root, manifest, static_reference)
    original, original_hash = original_reference(root, manifest, manifest["restore_verification_reference"])
    restored, restored_hash = read_json(restored_path)
    if (baseline.get("contract") != "PR9_STATIC_ARCHIVE_METADATA_V1"
            or baseline.get("archive_bytes_verified") is not True
            or baseline.get("historical_dependency_metadata_verified") is not True
            or baseline.get("historical_image_started") is not False
            or baseline.get("archived_package_code_imported") is not False
            or any(not HASH.fullmatch(baseline.get(key, "")) for key in STATIC_FIELDS
                   if key.endswith("sha256"))):
        raise ValueError("ARCHIVE_ORIGINAL_STATIC_CONTRACT_REJECTED")
    contracts = original.get("archive_contracts", {})
    if (set(contracts) != ARCHIVES or any(not HASH.fullmatch(value or "") for value in contracts.values())
            or contracts["model"] != baseline["artifact_sha256"]
            or any(record.get("success") is not True or record.get("cleanup_success") is not True
                   for record in (original, restored))
            or restored.get("archive_contracts") != contracts
            or not isinstance(original.get("verified_backup_files"), int)
            or not isinstance(restored.get("verified_backup_files"), int)
            or restored["verified_backup_files"] < original["verified_backup_files"]
            or any(restored.get(key) != original.get(key) for key in
                   ("expected_value", "valuation_as_of", "expected_current_issue"))):
        raise ValueError("ARCHIVE_REPORTED_HISTORY_MISMATCH")
    if len(envelope) > LIMIT:
        raise ValueError("ARCHIVE_INPUT_REJECTED")
    value = json.loads(envelope)
    body = base64.b64decode(value["artifact_base64"], validate=True)
    if (len(body) > 20_000_000 or value.get("contract") != "PR5_LEGACY_VERIFICATION_V1"
            or hashlib.sha256(body).hexdigest() != baseline["artifact_sha256"]
            or value.get("artifact_sha256") != baseline["artifact_sha256"]):
        raise ValueError("ARCHIVE_ORIGINAL_ARTIFACT_MISMATCH")
    artifact = json.loads(body)
    if (artifact.get("contract") != "internal-data-only-model-v1"
            or artifact.get("training_code") != value.get("training_code")
            or artifact.get("configuration") != value.get("configuration")):
        raise ValueError("ARCHIVE_ORIGINAL_MODEL_METADATA_MISMATCH")
    return baseline, {
        "original_manifest_sha256": actual, "original_static_proof_sha256": baseline_hash,
        "original_restore_proof_sha256": original_hash, "supplied_restore_receipt_sha256": restored_hash,
        "original_archive_contracts": contracts,
        "reported_verified_backup_files": restored["verified_backup_files"],
        "supplied_receipt_comparison": ("ORIGINAL_RECEIPT_RECHECK_ONLY" if restored_hash == original_hash
                                        else "DIFFERENT_RECEIPT_MATCHES_ORIGINAL_REPORTED_CONTRACTS_ONLY"),
        "supplied_receipt_claims_independently_verified": False,
        "training_code_content_sha256": digest(artifact["training_code"]),
        "configuration_content_sha256": digest(artifact["configuration"]),
        "supplied_receipt_reports_separate_legacy_execution": "legacy_verification" in restored,
    }


def verify(envelope, root, manifest_path, manifest_sha256, static_reference, restored_path, inventory, workdir):
    baseline, anchors = prepare(envelope, root, manifest_path, manifest_sha256, static_reference, restored_path)
    # All original-envelope/receipt comparisons precede Docker access. This helper
    # creates an inert container and copies only SBOM-allowlisted metadata.
    result = from_image(envelope, baseline["historical_image"], workdir, inventory)
    if (any(result.get(key) != baseline.get(key) for key in STATIC_FIELDS)
            or result.get("historical_image_started") is not False
            or result.get("archived_package_code_imported") is not False
            or result.get("archive_bytes_verified") is not True
            or result.get("historical_dependency_metadata_verified") is not True):
        raise ValueError("ARCHIVE_ORIGINAL_METADATA_MISMATCH")
    return anchors | {
        "contract": "PR10_ARCHIVE_INTEGRITY_RECOVERY_V2", "integrity_verified": True,
        "integrity_scope": "SUPPLIED_ARTIFACT_BYTES_AND_HISTORICAL_IMAGE_METADATA_ONLY",
        "supplied_artifact_bytes_verified": True,
        "original_metadata_verified": True, "historical_image": baseline["historical_image"],
        "artifact_sha256": baseline["artifact_sha256"],
        "historical_sbom_sha256": result["historical_sbom_sha256"],
        "metadata_manifest_sha256": result["metadata_manifest_sha256"],
        "checked_pins": result["checked_pins"], "historical_image_started_by_this_verifier": False,
        "archived_package_code_imported": False,
        "fresh_restore_executed_by_this_verifier": False,
        "fresh_restore_proven_by_this_verifier": False,
        "restored_database_accessed_by_this_verifier": False,
        "restored_object_store_accessed_by_this_verifier": False,
        "restored_archive_bytes_checked_by_this_verifier": False,
        "historical_runtime_execution": "NOT_EXECUTED_NOT_PROVEN",
        "historical_numerical_reproducibility": "NOT_EXECUTED_NOT_PROVEN",
        "required_legacy_runtime_check_satisfied": False, "security_approval": False,
        "forecast_validation": False, "model_or_strategy_promotion": False,
    }


def core_anchors(root, manifest_path, manifest_sha256, static_reference, inventory):
    """Original data expectations, never a receipt supplied as a fresh restore."""
    if not HASH.fullmatch(manifest_sha256 or ""):
        raise ValueError("ARCHIVE_INDEPENDENT_MANIFEST_HASH_REQUIRED")
    manifest, actual = read_json(manifest_path)
    if actual != manifest_sha256:
        raise ValueError("ARCHIVE_ORIGINAL_MANIFEST_HASH_MISMATCH")
    if digest({k: v for k, v in manifest.items() if k != "content_sha256"}) != manifest.get("content_sha256"):
        raise ValueError("ARCHIVE_ORIGINAL_MANIFEST_CONTENT_MISMATCH")
    baseline, static_hash = original_reference(root, manifest, static_reference)
    original, restore_hash = original_reference(root, manifest, manifest["restore_verification_reference"])
    if (baseline.get("contract") != "PR9_STATIC_ARCHIVE_METADATA_V1"
            or baseline.get("archive_bytes_verified") is not True
            or baseline.get("historical_dependency_metadata_verified") is not True
            or baseline.get("historical_image_started") is not False
            or baseline.get("archived_package_code_imported") is not False
            or baseline.get("checked_pins") != 66
            or any(not HASH.fullmatch(baseline.get(key, "")) for key in STATIC_FIELDS
                   if key.endswith("sha256"))):
        raise ValueError("CORE_ORIGINAL_STATIC_CONTRACT_REJECTED")
    contracts = original.get("archive_contracts", {})
    if (set(contracts) != ARCHIVES or any(not HASH.fullmatch(value or "") for value in contracts.values())
            or contracts["model"] != baseline["artifact_sha256"]
            or original.get("success") is not True or original.get("cleanup_success") is not True
            or type(original.get("verified_backup_files")) is not int or original["verified_backup_files"] < 1
            or not original.get("valuation_as_of") or not original.get("expected_current_issue")):
        raise ValueError("CORE_ORIGINAL_RESTORE_CONTRACT_REJECTED")
    try:
        inventory_name = inventory.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        raise ValueError("CORE_ORIGINAL_INVENTORY_OUTSIDE_ANCHOR_ROOT") from None
    original_reference(root, manifest, inventory_name)
    paths, sbom_hash = metadata_paths(inventory, baseline["historical_image"])
    files = baseline.get("metadata_file_hashes", {})
    if (not isinstance(files, dict) or set(paths) != set(files)
            or any(not HASH.fullmatch(value or "") for value in files.values())
            or sbom_hash != baseline["historical_sbom_sha256"]):
        raise ValueError("CORE_ORIGINAL_METADATA_ANCHOR_MISMATCH")
    return baseline, original, {
        "original_manifest_sha256": actual, "original_static_proof_sha256": static_hash,
        "original_restore_proof_sha256": restore_hash, "historical_sbom_sha256": sbom_hash,
    }


def core_expectations(original, current):
    """Bind caller expectations before any restore mutation or archive access."""
    fields = ("archive_contracts", "expected_value", "valuation_as_of", "expected_current_issue",
              "verified_backup_files", "backup_run_id", "backup_manifest_sha256", "raw_object_count")
    if any(current.get(key) != original.get(key) for key in fields):
        raise ValueError("CORE_RESTORE_EXPECTATION_MISMATCH")


def current_expectations(path, expected_sha256, original_manifest_sha256, artifact_sha256, *, now=None):
    """A new backup has a new independently retained pre-restore checkpoint.

    This file is an input expectation only, never evidence of a successful
    restore. Aggregate hashes may grow; the original model bytes cannot change.
    """
    if not HASH.fullmatch(expected_sha256 or "") or path.is_symlink():
        raise ValueError("CORE_CURRENT_EXPECTATIONS_INDEPENDENT_HASH_REQUIRED")
    value, actual = read_json(path)
    if actual != expected_sha256:
        raise ValueError("CORE_CURRENT_EXPECTATIONS_HASH_MISMATCH")
    try:
        recorded = datetime.fromisoformat(value["recorded_at"].replace("Z", "+00:00"))
        cutoff = datetime.fromisoformat(value["valuation_as_of"].replace("Z", "+00:00"))
        observed = now or datetime.now(UTC)
        if recorded.tzinfo is None or cutoff.tzinfo is None or recorded > observed or cutoff > recorded:
            raise ValueError
    except (ValueError, TypeError, KeyError, AttributeError):
        raise ValueError("CORE_CURRENT_EXPECTATIONS_TIME_REJECTED") from None
    contracts = value.get("archive_contracts", {})
    if (value.get("contract") != CORE_EXPECTATIONS
            or value.get("original_manifest_sha256") != original_manifest_sha256
            or not HASH.fullmatch(value.get("backup_manifest_sha256", ""))
            or set(contracts) != ARCHIVES or any(not HASH.fullmatch(item or "") for item in contracts.values())
            or contracts["model"] != artifact_sha256
            or type(value.get("verified_backup_files")) is not int or value["verified_backup_files"] < 1
            or type(value.get("raw_object_count")) is not int or not 0 < value["raw_object_count"] < value["verified_backup_files"]
            or not isinstance(value.get("expected_value"), str) or not value["expected_value"]
            or value.get("expected_current_issue") not in {"STALE_PRICE", "MISSING_PRICE", "MISSING_FX"}
            or not re.fullmatch(r"[A-Za-z0-9_-]+", value.get("backup_run_id", ""))):
        raise ValueError("CORE_CURRENT_EXPECTATIONS_CONTRACT_REJECTED")
    return value


def metadata_bundle(path, expected_sha256, baseline):
    """Read an inert uncompressed TAR; never extract names or execute bytes."""
    if (not HASH.fullmatch(expected_sha256 or "") or path.is_symlink()
            or not path.is_file() or path.stat().st_size > 80 * 1024**2):
        raise ValueError("CORE_METADATA_BUNDLE_HASH_MISMATCH")
    with path.open("rb") as stream:
        body = stream.read(80 * 1024**2 + 1)
    if len(body) > 80 * 1024**2 or hashlib.sha256(body).hexdigest() != expected_sha256:
        raise ValueError("CORE_METADATA_BUNDLE_HASH_MISMATCH")
    expected = baseline.get("metadata_file_hashes", {})
    if not 2 < len(expected) <= 1500 or not set(LOCKS) <= set(expected):
        raise ValueError("CORE_METADATA_BUNDLE_ALLOWLIST_MISSING")
    for name in expected:
        if name not in LOCKS and not re.fullmatch(
            r"usr/local/lib/python3\.12/site-packages/[^/]+\.dist-info/METADATA", name
        ):
            raise ValueError("CORE_METADATA_BUNDLE_ALLOWLIST_REJECTED")
    seen, total = set(), 0
    with tarfile.open(fileobj=io.BytesIO(body), mode="r:") as archive:
        for member in archive:
            name = member.name
            if (name not in expected or name in seen or not member.isfile()
                    or member.pax_headers or member.size > 2_000_000 or member.size < 0):
                raise ValueError("CORE_METADATA_BUNDLE_MEMBER_REJECTED")
            total += member.size
            if total > 64 * 1024**2:
                raise ValueError("CORE_METADATA_BUNDLE_TOTAL_LIMIT")
            data = archive.extractfile(member).read(2_000_001)
            if hashlib.sha256(data).hexdigest() != expected[name]:
                raise ValueError("CORE_METADATA_BUNDLE_FILE_MISMATCH")
            seen.add(name)
    if seen != set(expected):
        raise ValueError("CORE_METADATA_BUNDLE_FILES_MISSING")
    return body


def verify_core_archive(envelope, baseline, anchors, bundle, bundle_sha256):
    """Verify bytes exported by the active restore producer, not a supplied receipt.

    DB/S3 replay is performed by restore_verify before this function. This helper
    alone does not establish that replay or historical Python execution occurred.
    """
    body = metadata_bundle(bundle, bundle_sha256, baseline)
    result = verify_metadata(envelope, io.BytesIO(body), baseline["historical_image"])
    if (any(result.get(key) != baseline.get(key) for key in STATIC_FIELDS
            if key != "historical_sbom_sha256")
            or result.get("metadata_file_hashes") != baseline.get("metadata_file_hashes")
            or result.get("historical_image_started") is not False
            or result.get("archived_package_code_imported") is not False):
        raise ValueError("CORE_ORIGINAL_METADATA_MISMATCH")
    return anchors | {
        "contract": CORE_RECOVERY, "archive_bytes_verified": True,
        "original_metadata_verified": True, "metadata_bundle_sha256": bundle_sha256,
        "artifact_sha256": result["artifact_sha256"], "historical_image": result["historical_image"],
        "metadata_manifest_sha256": result["metadata_manifest_sha256"], "checked_pins": result["checked_pins"],
        "core_lock_sha256": result["core_lock_sha256"], "support_lock_sha256": result["support_lock_sha256"],
        "historical_image_started": False, "archived_package_code_imported": False,
        "historical_runtime_execution": "NOT_EXECUTED_NOT_PROVEN",
        "historical_numerical_reproducibility": "NOT_EXECUTED_NOT_PROVEN",
        "optional_dynamic_legacy_status": "SECURITY_BLOCKED",
        "security_approval": False, "forecast_validation": False, "model_or_strategy_promotion": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--envelope", type=Path, required=True)
    parser.add_argument("--original-manifest", type=Path, required=True)
    parser.add_argument("--expected-original-manifest-sha256", required=True)
    parser.add_argument("--original-static-reference", required=True)
    parser.add_argument("--restored-proof", type=Path, required=True,
                        help="Supplied producer receipt comparison only; no restored DB/S3 or freshness proof")
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.envelope.open("rb") as stream:
        envelope = stream.read(LIMIT + 1)
    result = verify(envelope, args.root, args.original_manifest,
                    args.expected_original_manifest_sha256, args.original_static_reference,
                    args.restored_proof, args.inventory, args.workdir)
    result["verifier_sha256"] = sha256(Path(__file__))
    write_new(args.output, result)
    print("SUPPLIED_ARTIFACT_AND_IMAGE_METADATA_VERIFIED; receipt comparison only; fresh restore NOT_PROVEN")


if __name__ == "__main__":
    main()
