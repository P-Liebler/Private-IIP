"""Disposable S3 contract; only the explicitly named isolated SeaweedFS fixture.

No production originals, configuration, database, credentials or buckets are used.
Run the minio and boto3 modes in the application's corresponding runtime images.
"""
import hashlib
from io import BytesIO
import json
import os
import sys
import time

PROBE_STAGE = "startup"


def main():
    global PROBE_STAGE
    if os.environ.get("S3_COMPAT_TEST_MODE") != "synthetic-isolated-pr4":
        raise RuntimeError("Explicit isolated fixture required")
    endpoint = "seaweed:8333"
    bucket = "pr4-synthetic-contract"
    key = "raw/synthetic-original.bin"
    data = b"SYNTHETIC PR4 S3 CONTRACT\n" * 270000
    expected = hashlib.sha256(data).hexdigest()
    access, secret = os.environ["S3_TEST_ACCESS"], os.environ["S3_TEST_SECRET"]
    mode = os.environ["S3_PROBE_SDK"]
    if mode == "minio":
        from minio import Minio
        from app.core.storage import MinioObjectStorage
        client = Minio(endpoint, access_key=access, secret_key=secret, secure=False)
        storage = MinioObjectStorage(client, bucket)
        PROBE_STAGE = "bucket"
        for attempt in range(30):
            try:
                storage.ensure_bucket()
                break
            except Exception:
                if attempt == 29:
                    raise RuntimeError("ISOLATED_S3_NOT_READY") from None
                time.sleep(1)
        PROBE_STAGE = "original-put"
        if storage.exists(key):
            assert hashlib.sha256(storage.get(key)).hexdigest() == expected
        else:
            storage.put(key, data, "application/octet-stream")
        PROBE_STAGE = "original-read"
        assert storage.exists(key)
        assert hashlib.sha256(storage.get(key)).hexdigest() == expected
        PROBE_STAGE = "immutable-wrapper"
        try:
            storage.put(key, b"MUST_NOT_REPLACE_ORIGINAL")
        except FileExistsError:
            pass
        else:
            raise AssertionError("IMMUTABLE_WRAPPER_CONTRACT_FAILED")
        assert hashlib.sha256(storage.get(key)).hexdigest() == expected
        PROBE_STAGE = "metadata-and-list"
        client.put_object(bucket, "metadata/synthetic", BytesIO(b"SYNTHETIC"), 9,
                          metadata={"original-sha256": expected})
        assert client.stat_object(bucket, "metadata/synthetic").metadata["x-amz-meta-original-sha256"] == expected
        assert len(list(client.list_objects(bucket, recursive=True))) == 2
        print(json.dumps({"sdk": mode, "success": True, "bytes": len(data), "sha256": expected,
                          "tests": ["bucket", "put-multipart", "stat", "get-sha256", "immutable-wrapper", "metadata", "list"]}))
    elif mode == "boto3":
        PROBE_STAGE = "boto3-contract"
        import boto3
        from botocore.config import Config
        from botocore.exceptions import ClientError
        config = Config(signature_version="s3v4", s3={"addressing_style": "path"},
                        connect_timeout=3, read_timeout=10, retries={"max_attempts": 0})
        def create(secret_key):
            return boto3.client("s3", endpoint_url="http://" + endpoint, aws_access_key_id=access,
                                aws_secret_access_key=secret_key, region_name="us-east-1", config=config)
        client = create(secret)
        assert hashlib.sha256(client.get_object(Bucket=bucket, Key=key)["Body"].read()).hexdigest() == expected
        assert client.head_object(Bucket=bucket, Key="metadata/synthetic")["Metadata"]["original-sha256"] == expected
        assert client.get_object(Bucket=bucket, Key=key, Range="bytes=0-8")["Body"].read() == data[:9]
        client.upload_fileobj(BytesIO(data), bucket, "mlflow-artifacts/synthetic.bin")
        assert hashlib.sha256(client.get_object(Bucket=bucket, Key="mlflow-artifacts/synthetic.bin")["Body"].read()).hexdigest() == expected
        try:
            create("invalid-synthetic-signature").get_object(Bucket=bucket, Key=key)
        except ClientError as error:
            assert error.response["ResponseMetadata"]["HTTPStatusCode"] in {400, 401, 403}
        else:
            raise AssertionError("INVALID_AUTH_WAS_ACCEPTED")
        client.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
        assert client.get_bucket_versioning(Bucket=bucket)["Status"] == "Enabled"
        first = client.put_object(Bucket=bucket, Key="versioning/synthetic", Body=b"first")
        second = client.put_object(Bucket=bucket, Key="versioning/synthetic", Body=b"second")
        assert first["VersionId"] != second["VersionId"]
        assert client.get_object(Bucket=bucket, Key="versioning/synthetic", VersionId=first["VersionId"])["Body"].read() == b"first"
        print(json.dumps({"sdk": mode, "success": True, "sha256": expected,
                          "tests": ["get", "head-metadata", "range", "upload-fileobj", "auth-rejection", "versioning"]}))
    else:
        raise RuntimeError("Unknown SDK")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # SDK exception messages can contain request/signature details.
        print(json.dumps({"success": False, "error_type": type(error).__name__,
                          "phase": PROBE_STAGE, "reason_type": type(getattr(error, "reason", None)).__name__,
                          "missing_module": error.name if isinstance(error, ModuleNotFoundError) else None}), file=sys.stderr)
        raise SystemExit(1) from None
