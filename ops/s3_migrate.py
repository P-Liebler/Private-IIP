"""Read-only S3 inventory and resumable copy into an explicitly isolated target.

Credentials are environment-only. This tool never switches application endpoints,
deletes source objects, creates buckets, or silently drops unsupported contracts.
Keep manifests/journals private: object names and DB references are sensitive.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlencode, urlsplit

from operation_lock import acquire

PART = 8 * 1024 * 1024
HEADERS = ("ContentType", "CacheControl", "ContentDisposition", "ContentEncoding",
           "ContentLanguage", "Expires", "WebsiteRedirectLocation")
ROW_KEYS = ("bucket", "key", "version", "latest", "deleted", "modified_at")


class DifferenceError(RuntimeError):
    def __init__(self, code, differences):
        super().__init__(code)
        self.differences = differences


class ReadOnlySource:
    """Enforce the operation allowlist even with an existing operator credential."""
    def __init__(self, api):
        self.api = api

    def __getattr__(self, name):
        if name not in {"get_bucket_versioning", "get_object_lock_configuration",
                        "get_object", "head_object", "get_object_tagging"}:
            raise RuntimeError("SOURCE_OPERATION_NOT_READ_ONLY")
        return getattr(self.api, name)

    def get_paginator(self, name):
        if name not in {"list_object_versions", "list_objects_v2"}:
            raise RuntimeError("SOURCE_OPERATION_NOT_READ_ONLY")
        return self.api.get_paginator(name)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def save(path, value, *, new=False):
    path = Path(path)
    if new:
        # Exclusive creation never replaces an existing historical manifest.
        # A crash may leave an incomplete file; hash validation rejects it and
        # an operator must choose a new evidence path for another inventory.
        with path.open("xb") as stream:
            stream.write(canonical(value) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        return
    temporary = path.with_suffix(path.suffix + ".pending")
    with temporary.open("wb") as stream:
        stream.write(canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    # Windows readers may briefly hold a handle without FILE_SHARE_DELETE.
    # Preserve the previous complete checkpoint and bound the sharing retry.
    for attempt in range(6):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.05 * (2**attempt))


def address(row):
    result = {"Bucket": row["bucket"], "Key": row["key"]}
    if row["version"] is not None:
        result["VersionId"] = row["version"]
    return result


def sha_object(api, args):
    response = api.get_object(**args)
    size = 0
    checksum = hashlib.sha256()
    try:
        for block in response["Body"].iter_chunks(chunk_size=1024 * 1024):
            size += len(block)
            checksum.update(block)
    finally:
        response["Body"].close()
    return size, checksum.hexdigest()


def listing(api, bucket):
    """List every native version, including null versions and delete markers."""
    state = api.get_bucket_versioning(Bucket=bucket).get("Status", "UNVERSIONED")
    rows = []
    if state in {"Enabled", "Suspended"}:
        for page in api.get_paginator("list_object_versions").paginate(Bucket=bucket):
            for kind in ("Versions", "DeleteMarkers"):
                for item in page.get(kind, []):
                    rows.append({"bucket": bucket, "key": item["Key"],
                                 "version": item["VersionId"], "latest": item["IsLatest"],
                                 "deleted": kind == "DeleteMarkers",
                                 "modified_at": item["LastModified"].isoformat() if item.get("LastModified") else None})
    elif state == "UNVERSIONED":
        for page in api.get_paginator("list_objects_v2").paginate(Bucket=bucket):
            rows.extend({"bucket": bucket, "key": item["Key"], "version": None,
                         "latest": True, "deleted": False,
                         "modified_at": item["LastModified"].isoformat() if item.get("LastModified") else None}
                        for item in page.get("Contents", []))
    else:
        raise RuntimeError("UNKNOWN_VERSIONING_STATE")
    return state, sorted(rows, key=lambda r: (r["key"], r["version"] or "", r["deleted"]))


def describe(api, row):
    args = address(row)
    head = api.head_object(**args)
    if any(head.get(k) for k in ("SSECustomerAlgorithm", "SSEKMSKeyId", "Restore", "ServerSideEncryption")) or head.get("StorageClass", "STANDARD") != "STANDARD":
        raise RuntimeError("ENCRYPTION_OR_ARCHIVE_REVIEW_REQUIRED")
    size, checksum = sha_object(api, args)
    if size != head["ContentLength"]:
        raise RuntimeError("SOURCE_CHANGED_DURING_INVENTORY")
    headers = {k: (v.isoformat() if isinstance(v, datetime) else v)
               for k in HEADERS if (v := head.get(k)) is not None}
    return {"size": size, "sha256": checksum, "metadata": head.get("Metadata", {}),
            "headers": headers,
            "tags": sorted(api.get_object_tagging(**args).get("TagSet", []), key=lambda t: t["Key"]),
            "retention": {k: (v.isoformat() if isinstance(v, datetime) else v)
                          for k, v in head.items() if k in
                          ("ObjectLockMode", "ObjectLockRetainUntilDate", "ObjectLockLegalHoldStatus")}}


def check_references(records, references):
    failures = []
    for ref in references:
        matches = [r for r in records if not r["deleted"] and r["bucket"] == ref["bucket"]
                   and r["key"] == ref["key"] and
                   (r["version"] == ref["version"] if ref.get("version") is not None else r["latest"])]
        if len(matches) != 1 or (ref.get("sha256") and matches[0]["sha256"] != ref["sha256"]):
            failures.append(ref)
    if failures:
        raise DifferenceError("DB_REFERENCE_MISMATCH:" + str(len(failures)), failures)


def inventory(api, buckets, references, source_id):
    states, rows = {}, []
    for bucket in sorted(set(buckets)):
        # A locked bucket needs an independently reviewed policy migration.
        # Never interpret unsupported/forbidden lock APIs as absence of a lock.
        try:
            lock = api.get_object_lock_configuration(Bucket=bucket)
        except Exception as exc:
            code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            if code not in {"ObjectLockConfigurationNotFoundError", "NoSuchObjectLockConfiguration"}:
                raise RuntimeError("OBJECT_LOCK_CAPABILITY_UNVERIFIED") from None
            lock = {}
        if lock.get("ObjectLockConfiguration", {}).get("ObjectLockEnabled") == "Enabled":
            raise RuntimeError("LOCKED_BUCKET_POLICY_MIGRATION_REQUIRES_REVIEW")
        state, items = listing(api, bucket)
        states[bucket] = state
        for item in items:
            row = dict(item)
            if not row["deleted"]:
                row.update(describe(api, row))
                if row["retention"]:
                    raise RuntimeError("OBJECT_RETENTION_MIGRATION_REQUIRES_REVIEW")
            row["id"] = digest({k: row[k] for k in ("bucket", "key", "version", "deleted")})
            rows.append(row)
        if listing(api, bucket) != (state, items):
            raise RuntimeError("SOURCE_LIST_CHANGED_DURING_INVENTORY")
    check_references(rows, references)
    payload = {"contract": "PR7_S3_MANIFEST_V2", "source": source_id,
               "versioning": states, "records": rows, "references": references}
    return {"payload": payload, "sha256": digest(payload)}


def validate_manifest(manifest):
    payload = manifest["payload"]
    if payload["contract"] not in {"PR7_S3_MANIFEST_V1", "PR7_S3_MANIFEST_V2"} or manifest["sha256"] != digest(payload):
        raise RuntimeError("MANIFEST_HASH_MISMATCH")
    check_references(payload["records"], payload["references"])
    return payload


def verify_source_set(source, payload):
    for bucket, state in payload["versioning"].items():
        expected = [{key: row[key] for key in ROW_KEYS}
                    for row in payload["records"] if row["bucket"] == bucket]
        if listing(source, bucket) != (state, expected):
            raise RuntimeError("SOURCE_VERSION_SET_CHANGED")


def transfer(source, target, row, bucket, key, state, checkpoint, *, stop_after_parts=0):
    """Re-read every completed object; recover a lost completion receipt by HEAD."""
    expected = {k: row[k] for k in ("size", "sha256", "metadata", "headers", "tags", "retention")}
    target_row = {"bucket": bucket, "key": key, "version": None}
    try:
        actual = describe(target, target_row)
    except Exception as exc:
        if getattr(exc, "response", {}).get("Error", {}).get("Code") not in {"404", "NoSuchKey", "NotFound"}:
            raise
    else:
        if actual != expected:
            raise DifferenceError("TARGET_COLLISION_OR_HASH_MISMATCH", [{
                "object_id": row["id"], "target_bucket": bucket, "target_key": key,
                "fields": [field for field in expected if actual.get(field) != expected[field]],
                "expected_sha256": row["sha256"], "actual_sha256": actual.get("sha256")}])
        state["verified"] = True
        state["target_version"] = target.head_object(Bucket=bucket, Key=key).get("VersionId")
        checkpoint()
        return
    if state.get("verified"):
        raise RuntimeError("PREVIOUSLY_VERIFIED_TARGET_MISSING")
    headers = dict(row["headers"])
    if "Expires" in headers:
        headers["Expires"] = datetime.fromisoformat(headers["Expires"])
    kwargs = {"Bucket": bucket, "Key": key, "Metadata": row["metadata"], **headers}
    if row["tags"]:
        kwargs["Tagging"] = urlencode([(t["Key"], t["Value"]) for t in row["tags"]])
    if row["size"] == 0:
        target.put_object(**kwargs, Body=b"")
    else:
        if not state.get("upload"):
            state["upload"] = target.create_multipart_upload(**kwargs)["UploadId"]
            checkpoint()
        # Re-upload known ranges with stable part numbers. A lost per-part
        # receipt is safe; S3 replaces that part within this exact upload.
        parts = []
        checksum = hashlib.sha256()
        count = 0
        part_size = max(PART, (row["size"] + 9999) // 10000)
        for number, offset in enumerate(range(0, row["size"], part_size), 1):
            args = address(row)
            response = source.get_object(**args, Range=f"bytes={offset}-{min(offset + part_size, row['size']) - 1}")
            try:
                block = response["Body"].read(part_size + 1)
            finally:
                response["Body"].close()
            if len(block) != min(part_size, row["size"] - offset):
                raise RuntimeError("SOURCE_RANGE_LENGTH_MISMATCH")
            checksum.update(block)
            old = state.setdefault("parts", {}).get(str(number))
            block_hash = hashlib.sha256(block).hexdigest()
            if old and old["sha256"] != block_hash:
                raise RuntimeError("SOURCE_CHANGED_DURING_COPY")
            # Verify persisted part existence before reusing it.
            if old:
                remote = [p for page in target.get_paginator("list_parts").paginate(
                    Bucket=bucket, Key=key, UploadId=state["upload"])
                    for p in page.get("Parts", []) if p["PartNumber"] == number]
                if len(remote) != 1 or remote[0]["ETag"] != old["etag"] or remote[0]["Size"] != len(block):
                    raise RuntimeError("MULTIPART_CHECKPOINT_MISMATCH")
                etag = old["etag"]
            else:
                etag = target.upload_part(Bucket=bucket, Key=key, UploadId=state["upload"],
                                          PartNumber=number, Body=block)["ETag"]
                state["parts"][str(number)] = {"etag": etag, "sha256": block_hash}
                checkpoint()
                count += 1
                if stop_after_parts and count >= stop_after_parts:
                    raise InterruptedError("CONTROLLED_MULTIPART_INTERRUPTION")
            parts.append({"PartNumber": number, "ETag": etag})
        if checksum.hexdigest() != row["sha256"]:
            raise RuntimeError("SOURCE_HASH_CHANGED")
        target.complete_multipart_upload(Bucket=bucket, Key=key, UploadId=state["upload"],
                                         MultipartUpload={"Parts": parts})
    if describe(target, target_row) != expected:
        raise RuntimeError("TARGET_REREAD_MISMATCH")
    state["verified"] = True
    state["target_version"] = target.head_object(Bucket=bucket, Key=key).get("VersionId")
    checkpoint()


def copy(manifest, source, target, target_buckets, journal, persist, *, stop_after_parts=0):
    try:
        return _copy(manifest, source, target, target_buckets, journal, persist,
                     stop_after_parts=stop_after_parts)
    except Exception as exc:
        if journal.get("identity", {}).get("manifest") == manifest.get("sha256"):
            journal["status"] = "INTERRUPTED" if isinstance(exc, InterruptedError) else "COPY_FAILED"
            # Only our controlled error codes; SDK messages may contain private names.
            journal["failure"] = str(exc) if type(exc) in {RuntimeError, InterruptedError, DifferenceError} else type(exc).__name__
            journal["differences"] = getattr(exc, "differences", [{"reason": journal["failure"]}])
            persist()
        raise


def _copy(manifest, source, target, target_buckets, journal, persist, *, stop_after_parts=0):
    payload = validate_manifest(manifest)
    if payload["contract"] != "PR7_S3_MANIFEST_V2":
        raise RuntimeError("NEW_VERSIONED_INVENTORY_REQUIRED")
    if set(target_buckets) != set(payload["versioning"]) or set(target_buckets.values()) & set(target_buckets):
        raise RuntimeError("SEPARATE_EXACT_TARGET_BUCKETS_REQUIRED")
    identity = {"manifest": manifest["sha256"], "target_buckets": target_buckets}
    if journal.get("identity", identity) != identity:
        raise RuntimeError("JOURNAL_IDENTITY_MISMATCH")
    for bucket in target_buckets.values():
        keys = {r["key"] for r in listing(target, bucket)[1]}
        if "identity" not in journal and keys:
            raise RuntimeError("NEW_TARGET_MUST_BE_EMPTY")
        allowed = {f"__pr7_archive/{manifest['sha256']}/{r['id']}" for r in payload["records"]
                   if not r["deleted"]}
        allowed.update(r["key"] for r in payload["records"] if r["latest"] and not r["deleted"])
        if keys - allowed:
            raise RuntimeError("UNEXPECTED_TARGET_KEYS")
    journal["identity"] = identity
    journal["status"] = "COPY_IN_PROGRESS"
    journal.pop("failure", None)
    journal.pop("differences", None)
    persist()
    verify_source_set(source, payload)
    for bucket in payload["versioning"]:
        if target.get_bucket_versioning(Bucket=target_buckets[bucket]).get("Status") != "Enabled":
            raise RuntimeError("TARGET_VERSIONING_REQUIRED")
    for row in payload["records"]:
        if row["deleted"]:
            continue  # Preserved explicitly in the pinned manifest, never resurrected.
        archive_key = f"__pr7_archive/{manifest['sha256']}/{row['id']}"
        state = journal.setdefault("objects", {}).setdefault(row["id"], {})
        transfer(source, target, row, target_buckets[row["bucket"]], archive_key,
                 state, persist, stop_after_parts=stop_after_parts)
        if row["latest"]:
            if row["key"].startswith("__pr7_archive/"):
                raise RuntimeError("RESERVED_NAMESPACE_COLLISION")
            current = journal.setdefault("current", {}).setdefault(row["id"], {})
            transfer(source, target, row, target_buckets[row["bucket"]], row["key"], current, persist,
                     stop_after_parts=stop_after_parts)
    # Final source pass detects unversioned mutations and metadata/tag changes.
    for row in payload["records"]:
        if not row["deleted"] and describe(source, row) != {k: row[k] for k in
                ("size", "sha256", "metadata", "headers", "tags", "retention")}:
            raise RuntimeError("SOURCE_CHANGED_AFTER_COPY")
    verify_source_set(source, payload)
    journal["status"] = "COPY_VERIFIED_NO_APPLICATION_CUTOVER"
    persist()


def client(prefix):
    import boto3
    from botocore.config import Config
    endpoint = os.environ[prefix + "_ENDPOINT"]
    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise RuntimeError("STRICT_HTTPS_ENDPOINT_REQUIRED")
    return boto3.client("s3", endpoint_url=endpoint, region_name="us-east-1",
        aws_access_key_id=os.environ[prefix + "_ACCESS_KEY"],
        aws_secret_access_key=os.environ[prefix + "_SECRET_KEY"],
        verify=os.environ.get(prefix + "_CA_FILE") or True,
        config=Config(signature_version="s3v4", connect_timeout=5, read_timeout=30,
                      retries={"max_attempts": 0}, s3={"addressing_style": "path"}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("inventory", "dry-run", "copy"))
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--references", type=Path, help="Private DB export: [{bucket,key,sha256,version?}]")
    parser.add_argument("--bucket", action="append")
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--target-map", type=Path, help="JSON source bucket -> pre-created isolated target bucket")
    parser.add_argument("--authorize-isolated-target", action="store_true")
    parser.add_argument("--stop-after-parts", type=int, default=0)
    args = parser.parse_args()
    if args.mode == "inventory":
        if not args.references or not args.bucket:
            parser.error("Inventory requires explicit buckets and a DB reference export")
        source = ReadOnlySource(client("MIGRATION_SOURCE"))
        try:
            result = inventory(source, args.bucket, json.loads(args.references.read_text(encoding="utf-8")),
                               os.environ["MIGRATION_SOURCE_ENDPOINT"])
        except DifferenceError as error:
            save(args.manifest.with_suffix(".reference-differences.json"),
                 {"status": "INVENTORY_FAILED", "differences": error.differences}, new=True)
            raise
        save(args.manifest, result, new=True)
    else:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        payload = validate_manifest(manifest)
        if args.mode == "dry-run":
            print(json.dumps({"status": "DRY_RUN_NO_NETWORK_NO_WRITES", "manifest": manifest["sha256"],
                              "versions": len(payload["records"]), "db_references": len(payload["references"])}))
            return 0
        if not args.authorize_isolated_target or not args.journal or not args.target_map:
            parser.error("Copy requires an explicitly authorized isolated target, map and durable journal")
        source_id = os.environ["MIGRATION_SOURCE_ENDPOINT"]
        target_id = os.environ["MIGRATION_TARGET_ENDPOINT"]
        if source_id.rstrip("/") == target_id.rstrip("/") or source_id != payload["source"]:
            raise RuntimeError("SEPARATE_PINNED_SOURCE_AND_TARGET_REQUIRED")
        mapping = json.loads(args.target_map.read_text(encoding="utf-8"))
        if set(mapping) != set(payload["versioning"]) or len(set(mapping.values())) != len(mapping):
            raise RuntimeError("EXACT_UNIQUE_BUCKET_MAP_REQUIRED")
        lock = acquire(args.journal.parent)
        try:
            journal = json.loads(args.journal.read_text(encoding="utf-8")) if args.journal.exists() else {}
            if journal.get("target_endpoint", target_id) != target_id:
                raise RuntimeError("TARGET_ENDPOINT_CHANGED")
            journal["target_endpoint"] = target_id
            copy(manifest, ReadOnlySource(client("MIGRATION_SOURCE")), client("MIGRATION_TARGET"), mapping, journal,
                 lambda: save(args.journal, journal), stop_after_parts=args.stop_after_parts)
        finally:
            lock.close()
    print(json.dumps({"status": "VERIFIED", "application_cutover": False}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except InterruptedError:
        print("CONTROLLED_MULTIPART_INTERRUPTION", file=sys.stderr)
        raise SystemExit(77)
    except Exception as exc:
        # SDK exceptions may include sensitive endpoints/object names. Keep the
        # private journal and investigate locally; never emit credential traces.
        print("MIGRATION_FAILED:" + type(exc).__name__, file=sys.stderr)
        raise SystemExit(1)
