"""Real interrupted multipart/resume and mirror/restore, synthetic isolated S3 only."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, SSLError

SOURCE = "pr5-synthetic-source"
TARGET = "pr5-synthetic-target"
RESTORED = "pr5-synthetic-restored"
PART = 5 * 1024 * 1024
ROOT = Path("/evidence")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def client(host, *, valid=True, trust=True):
    return boto3.client("s3", endpoint_url=f"https://{host}:8443",
        aws_access_key_id=os.environ["S3_TEST_ACCESS"] if valid else "invalid-synthetic-access",
        aws_secret_access_key=os.environ["S3_TEST_SECRET"] if valid else "invalid-synthetic-secret",
        verify="/trust/root.crt" if trust else True, region_name="us-east-1",
        config=Config(signature_version="s3v4", retries={"max_attempts": 0},
                      connect_timeout=5, read_timeout=15, s3={"addressing_style": "path"}))


def objects(api, bucket):
    return sorted(x["Key"] for page in api.get_paginator("list_objects_v2").paginate(Bucket=bucket)
                  for x in page.get("Contents", []))


def read(api, bucket, key):
    body = api.get_object(Bucket=bucket, Key=key)["Body"]
    try:
        return b"".join(body.iter_chunks(chunk_size=65536))
    finally:
        body.close()


def manifest(api, bucket):
    result = {}
    for key in objects(api, bucket):
        head = api.head_object(Bucket=bucket, Key=key)
        data = read(api, bucket, key)
        result[key] = {"sha256": sha(data), "size": len(data), "metadata": head["Metadata"], "content_type": head["ContentType"]}
    return result


def main():
    if os.environ.get("PR5_SYNTHETIC_S3") != "explicit-isolated-fixture":
        raise ValueError("ISOLATED_SYNTHETIC_FIXTURE_REQUIRED")
    phase = sys.argv[1]
    assert phase in {"interrupt", "resume"}
    source, target = client("source-tls"), client("target-tls")
    for _ in range(60):
        try:
            source.list_buckets(); target.list_buckets(); break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError("ISOLATED_S3_STARTUP_FAILED")
    checkpoint = ROOT / "multipart-checkpoint.json"
    if phase == "interrupt":
        assert not checkpoint.exists(), "Never overwrite a completed prototype"
        source.create_bucket(Bucket=SOURCE); target.create_bucket(Bucket=TARGET)
        examples = {"raw/synthetic.csv": b"SYNTHETIC NON-FINANCIAL ORIGINAL\n",
                    "model-artifacts/synthetic.json": b'{"synthetic":true,"executable":false}',
                    "documents/synthetic.bin": b"SYNTHETIC-PR5-OBJECT-" * 600000}
        for key, data in examples.items():
            source.put_object(Bucket=SOURCE, Key=key, Body=data, ContentType="application/octet-stream",
                              Metadata={"sha256": sha(data), "evidence": "synthetic-only"})
        original = manifest(source, SOURCE)
        # Verify auth, missing-object, range and strict TLS behavior before copying.
        try:
            client("target-tls", valid=False).list_buckets(); raise AssertionError("AUTH_NOT_REQUIRED")
        except ClientError as e:
            assert e.response["ResponseMetadata"]["HTTPStatusCode"] == 403
        try:
            client("target-tls", trust=False).list_buckets(); raise AssertionError("TLS_NOT_VERIFIED")
        except SSLError:
            pass
        try:
            source.head_object(Bucket=SOURCE, Key="missing-synthetic"); raise AssertionError("MISSING_NOT_REPORTED")
        except ClientError as e:
            assert e.response["ResponseMetadata"]["HTTPStatusCode"] == 404
        ranged = source.get_object(Bucket=SOURCE, Key="documents/synthetic.bin", Range="bytes=0-31")["Body"]
        try:
            assert ranged.read() == examples["documents/synthetic.bin"][:32]
        finally:
            ranged.close()
        for key in ("raw/synthetic.csv", "model-artifacts/synthetic.json"):
            target.put_object(Bucket=TARGET, Key=key, Body=examples[key],
                              ContentType=original[key]["content_type"], Metadata=original[key]["metadata"])
        key = "documents/synthetic.bin"
        upload = target.create_multipart_upload(Bucket=TARGET, Key=key, ContentType=original[key]["content_type"], Metadata=original[key]["metadata"])["UploadId"]
        part = target.upload_part(Bucket=TARGET, Key=key, UploadId=upload, PartNumber=1, Body=examples[key][:PART])
        assert target.list_parts(Bucket=TARGET, Key=key, UploadId=upload)["Parts"][0]["Size"] == PART
        with checkpoint.open("x") as f:
            json.dump({"manifest": original, "upload_id": upload, "part1_etag": part["ETag"]}, f)
        assert len(objects(target, TARGET)) == 2  # Incomplete object must not look committed.
        print(json.dumps({"interrupted_after_uploaded_bytes": PART, "completed_objects": 2, "incomplete_object_visible": False}))
        return 77  # Deliberate process boundary; later invocation resumes same upload.
    saved = json.loads(checkpoint.read_text())
    assert manifest(source, SOURCE) == saved["manifest"]
    assert len(objects(target, TARGET)) == 2
    key = "documents/synthetic.bin"
    data = read(source, SOURCE, key)
    parts = target.list_parts(Bucket=TARGET, Key=key, UploadId=saved["upload_id"])["Parts"]
    assert len(parts) == 1 and parts[0]["ETag"] == saved["part1_etag"]
    part2 = target.upload_part(Bucket=TARGET, Key=key, UploadId=saved["upload_id"], PartNumber=2, Body=data[PART:])
    target.complete_multipart_upload(Bucket=TARGET, Key=key, UploadId=saved["upload_id"], MultipartUpload={"Parts": [{"PartNumber": 1, "ETag": saved["part1_etag"]}, {"PartNumber": 2, "ETag": part2["ETag"]}]})
    assert manifest(target, TARGET) == saved["manifest"]
    mirror = ROOT / "mirror"; mirror.mkdir(exist_ok=False)
    target.create_bucket(Bucket=RESTORED)
    for key, entry in saved["manifest"].items():
        data = read(target, TARGET, key)
        path = mirror / key; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        assert sha(path.read_bytes()) == entry["sha256"]
        target.put_object(Bucket=RESTORED, Key=key, Body=path.read_bytes(), ContentType=entry["content_type"], Metadata=entry["metadata"])
    assert manifest(target, RESTORED) == manifest(source, SOURCE) == saved["manifest"]
    target.put_object(Bucket=RESTORED, Key="controlled-delete", Body=b"synthetic")
    target.delete_object(Bucket=RESTORED, Key="controlled-delete")
    assert "controlled-delete" not in objects(target, RESTORED)
    value = {"passed": True, "scope": "ISOLATED_SYNTHETIC_S3_NOT_PRODUCTION_MIGRATION",
             "objects": 3, "bytes": sum(v["size"] for v in saved["manifest"].values()),
             "manifest_sha256": sha(json.dumps(saved["manifest"], sort_keys=True).encode()),
             "put_get_head_list_delete": "PASS", "streaming_range_metadata_sha256": "PASS",
             "strict_tls_and_invalid_auth": "PASS", "interrupted_multipart_resume": "PASS",
             "mirror_and_isolated_object_restore": "PASS", "source_unchanged": True,
             "rollback": "ORIGINAL_ENDPOINT_READ_VERIFIED_NO_APPLICATION_SWITCH",
             "full_application_restore": "SEPARATE_ACCEPTANCE_REQUIRED"}
    with (ROOT / "result.json").open("x") as f:
        json.dump(value, f, indent=2)
    print(json.dumps(value)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
