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
from pathlib import Path
import re

from security_audit import sha256, write_new
from verify_archive_metadata import LIMIT, from_image

ARCHIVES = {"dataset", "model", "predictions", "risk", "recommendations", "intelligence",
            "document_removals", "ui_requests", "collections", "validation"}
HASH = re.compile(r"[0-9a-f]{64}\Z")
STATIC_FIELDS = ("artifact_sha256", "historical_image", "historical_sbom_sha256",
                 "core_lock_sha256", "support_lock_sha256", "metadata_manifest_sha256",
                 "supporting_archive_contract", "checked_pins")


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
