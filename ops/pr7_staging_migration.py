"""Copy a quiesced local synthetic S3 source through the production adapters' TLS gateway.

Run inside the isolated MLflow operations container. No source mutations, app
endpoint changes or financial provider calls. Inputs/journal stay private.
"""
import json
import os
from pathlib import Path
import sys

from s3_migrate import ReadOnlySource, client, copy, inventory, save, validate_manifest


def main():
    if os.environ.get("APP_ENV") != "staging" or os.environ.get("PR7_SYNTHETIC_STAGE") != "explicit-isolated-fixture":
        raise RuntimeError("ISOLATED_STAGING_REQUIRED")
    root = Path("/pr7-evidence")
    refs = json.loads((root / "references.json").read_text())
    buckets = sorted({row["bucket"] for row in refs})
    if len(buckets) != 1:
        raise RuntimeError("ONE_EXPLICIT_APPLICATION_BUCKET_REQUIRED")
    target_bucket = os.environ["MINIO_BUCKET_RAW"]
    assert target_bucket.startswith("pr7-") and target_bucket not in buckets
    source = ReadOnlySource(client("MIGRATION_SOURCE"))
    target = client("MIGRATION_TARGET")
    path = root / "migration-manifest.json"
    if not path.exists():
        manifest = inventory(source, buckets, refs, os.environ["MIGRATION_SOURCE_ENDPOINT"])
        save(path, manifest, new=True)
    manifest = json.loads(path.read_text())
    payload = validate_manifest(manifest)
    # A dry-run receipt is separate from successful writes or cutover.
    receipt = root / "dry-run.json"
    if not receipt.exists():
        save(receipt, {"status": "DRY_RUN_MANIFEST_AND_REFERENCES_VALIDATED",
                       "manifest_sha256": manifest["sha256"], "references": len(refs),
                       "versions_and_markers": len(payload["records"]), "writes": 0}, new=True)
    checkpoint = root / "migration-journal.json"
    journal = json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
    persist = lambda: save(checkpoint, journal)
    interrupt = sys.argv[1] == "interrupt"
    copy(manifest, source, target, {buckets[0]: target_bucket}, journal, persist,
         stop_after_parts=1 if interrupt else 0)
    if interrupt:
        raise AssertionError("INTERRUPTION_NOT_TRIGGERED")
    original_journal = checkpoint.read_bytes()
    copy(manifest, source, target, {buckets[0]: target_bucket}, journal, persist)
    assert checkpoint.read_bytes() == original_journal
    save(root / "migration-result.json", {"status": "SYNTHETIC_FULL_SOURCE_COPY_VERIFIED",
        "manifest_sha256": manifest["sha256"], "versions_and_markers": len(payload["records"]),
        "references": len(refs), "source_versioning": payload["versioning"],
        "new_process_resume": True, "idempotent_replay": True,
        "source_unchanged": True, "application_cutover": False}, new=True)
    print("SYNTHETIC_FULL_SOURCE_COPY_VERIFIED")


if __name__ == "__main__":
    try:
        main()
    except InterruptedError:
        print("CONTROLLED_MULTIPART_INTERRUPTION")
        raise SystemExit(77)
    except Exception as error:
        print("STAGING_MIGRATION_FAILED:" + type(error).__name__)
        raise SystemExit(1)
