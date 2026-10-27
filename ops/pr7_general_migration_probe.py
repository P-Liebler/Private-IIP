"""Actual S3 integration for the general migration engine, isolated synthetic only."""
import hashlib
import json
import os
from pathlib import Path
import sys

import boto3
from botocore.config import Config

from s3_migrate import copy, inventory, save, validate_manifest


def api(host):
    return boto3.client("s3", endpoint_url=f"https://{host}:8443",
        aws_access_key_id=os.environ["S3_TEST_ACCESS"], aws_secret_access_key=os.environ["S3_TEST_SECRET"],
        verify="/trust/root.crt", region_name="us-east-1",
        config=Config(signature_version="s3v4", connect_timeout=5, read_timeout=30,
                      retries={"max_attempts": 0}, s3={"addressing_style": "path"}))


def main():
    if os.environ.get("PR5_SYNTHETIC_S3") != "explicit-isolated-fixture":
        raise RuntimeError("SYNTHETIC_ISOLATED_PROJECT_REQUIRED")
    root = Path("/evidence/general-migration")
    root.mkdir(exist_ok=True)
    source, target = api("source-tls"), api("target-tls")
    src, dst = "pr7-versioned-originals", "pr7-versioned-copy"
    phase = sys.argv[1]
    path = root / "manifest.json"
    checkpoint = root / "journal.json"
    if phase == "interrupt":
        assert not path.exists() and not checkpoint.exists()
        for store, bucket in ((source, src), (target, dst)):
            store.create_bucket(Bucket=bucket)
            store.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
        originals = {"raw/original": b"SYNTHETIC original bytes v1",
                     "documents/original": b"SYNTHETIC document original\n",
                     "0-model/large": b"SYNTHETIC-NONEXECUTABLE-MODEL\n" * 600000}
        for key, data in originals.items():
            source.put_object(Bucket=src, Key=key, Body=data, ContentType="application/octet-stream",
                              Metadata={"sha256": hashlib.sha256(data).hexdigest(), "scope": "synthetic"})
        corrected = b"SYNTHETIC corrected original v2"
        source.put_object(Bucket=src, Key="raw/original", Body=corrected,
                          ContentType="application/octet-stream", Metadata={"scope": "synthetic"})
        # Preserve a delete marker and its older bytes without resurrecting it.
        source.put_object(Bucket=src, Key="withdrawn-key", Body=b"SYNTHETIC old version")
        source.delete_object(Bucket=src, Key="withdrawn-key")
        refs = [{"table": "synthetic_fixture", "bucket": src, "key": "raw/original",
                 "sha256": hashlib.sha256(corrected).hexdigest()}]
        manifest = inventory(source, [src], refs, "https://source-tls:8443")
        save(path, manifest, new=True)
        journal = {}
        copy(manifest, source, target, {src: dst}, journal,
             lambda: save(checkpoint, journal), stop_after_parts=1)
        raise AssertionError("INTERRUPTION_NOT_TRIGGERED")
    assert phase == "resume"
    manifest = json.loads(path.read_text())
    payload = validate_manifest(manifest)
    journal = json.loads(checkpoint.read_text())
    persist = lambda: save(checkpoint, journal)
    copy(manifest, source, target, {src: dst}, journal, persist)
    first = checkpoint.read_bytes()
    copy(manifest, source, target, {src: dst}, journal, persist)
    assert checkpoint.read_bytes() == first
    assert not any(r["Key"] == "withdrawn-key" for p in target.get_paginator("list_objects_v2").paginate(Bucket=dst) for r in p.get("Contents", []))
    result = {"status": "VERIFIED_SYNTHETIC_GENERAL_ENGINE", "manifest_sha256": manifest["sha256"],
              "versions_and_markers": len(payload["records"]), "references": len(payload["references"]),
              "resumed_new_process": True, "idempotent_journal": True,
              "deleted_latest_not_resurrected": True, "application_cutover": False,
              "full_database_rag_mlflow_restore": "SEPARATE_ACCEPTANCE_REQUIRED"}
    save(root / "result.json", result, new=True)
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except InterruptedError:
        print("CONTROLLED_MULTIPART_INTERRUPTION")
        raise SystemExit(77)
