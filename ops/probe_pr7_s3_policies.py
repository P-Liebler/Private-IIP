"""Synthetic staging policy/retention probe. Admin credentials arrive on stdin."""
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


def main():
    if os.environ.get("APP_ENV") != "staging" or os.environ.get("MINIO_ENDPOINT") != "caddy:9002":
        raise RuntimeError("ISOLATED_STAGING_REQUIRED")
    control = json.loads(sys.stdin.readline())
    if control["scope"] != "PR7_SYNTHETIC_NEW_PROJECT":
        raise RuntimeError("SYNTHETIC_CONTROL_REQUIRED")
    endpoint = "https://caddy:9002"
    ca = os.environ["MINIO_CA_CERT_PATH"]

    def client(access, secret):
        return boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=access,
            aws_secret_access_key=secret, region_name="us-east-1", verify=ca,
            config=Config(signature_version="s3v4", connect_timeout=5, read_timeout=15,
                          retries={"max_attempts": 0}, s3={"addressing_style": "path"}))

    admin = client(control["access"], control["secret"])
    app = client(os.environ["MINIO_ACCESS_KEY"], os.environ["MINIO_SECRET_KEY"])
    raw = os.environ["MINIO_BUCKET_RAW"]
    assert raw.startswith("pr7-")
    if control.get("phase") == "bootstrap":
        admin.create_bucket(Bucket=raw)
        admin.put_bucket_versioning(Bucket=raw, VersioningConfiguration={"Status": "Enabled"})
        print(json.dumps({"status": "EMPTY_VERSIONED_TARGET_CREATED"}))
        return
    assert admin.get_bucket_versioning(Bucket=raw).get("Status") == "Enabled"
    policy = {"Version": "2012-10-17", "Statement": [{"Effect": "Deny", "Principal": "*",
        "Action": "s3:PutObject", "Resource": f"arn:aws:s3:::{raw}/denied/*"}]}
    admin.put_bucket_policy(Bucket=raw, Policy=json.dumps(policy))
    app.put_object(Bucket=raw, Key="policy-allowed", Body=b"SYNTHETIC POLICY CONTROL")
    try:
        app.put_object(Bucket=raw, Key="denied/normal-put", Body=b"SYNTHETIC DENIED")
        raise AssertionError("DENY_PUT_NOT_ENFORCED")
    except ClientError as error:
        assert error.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    signed = app.generate_presigned_post(Bucket=raw, Key="denied/post-policy", ExpiresIn=60)
    boundary = "pr7" + uuid.uuid4().hex
    body = bytearray()
    for key, value in signed["fields"].items():
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="synthetic.txt"\r\nContent-Type: text/plain\r\n\r\nSYNTHETIC DENIED POST\r\n--{boundary}--\r\n'.encode())
    request = urllib.request.Request(signed["url"], data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(request, context=ssl.create_default_context(cafile=ca), timeout=15):
            raise AssertionError("DENY_POST_NOT_ENFORCED")
    except urllib.error.HTTPError as error:
        assert error.code == 403
    # Object Lock is a separate native contract; never confuse application
    # immutability or versioning with enforced server-side retention.
    locked = "pr7-retention-fixture"
    admin.create_bucket(Bucket=locked, ObjectLockEnabledForBucket=True)
    admin.put_bucket_versioning(Bucket=locked, VersioningConfiguration={"Status": "Enabled"})
    original = b"SYNTHETIC RETENTION ORIGINAL"
    result = admin.put_object(Bucket=locked, Key="locked", Body=original,
        ObjectLockMode="COMPLIANCE", ObjectLockRetainUntilDate=datetime.now(UTC) + timedelta(days=1))
    version = result["VersionId"]
    try:
        admin.delete_object(Bucket=locked, Key="locked", VersionId=version)
        raise AssertionError("COMPLIANCE_RETENTION_DELETE_ALLOWED")
    except ClientError as error:
        assert error.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    stream = admin.get_object(Bucket=locked, Key="locked", VersionId=version)["Body"]
    try:
        assert hashlib.sha256(stream.read()).digest() == hashlib.sha256(original).digest()
    finally:
        stream.close()
    print(json.dumps({"status": "SYNTHETIC_POLICY_RETENTION_VERIFIED",
        "ordinary_put_denied": True, "post_upload_denied": True,
        "native_versioning": True, "compliance_version_delete_denied": True,
        "original_version_bytes_preserved": True, "production_approval": False}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "STAGING_POLICY_RETENTION_FAILED", "error_type": type(error).__name__}))
        raise SystemExit(1)
