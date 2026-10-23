"""Read-only TLS/SDK check against the isolated synthetic PR5 S3 fixture."""
import hashlib
import json
import os
import ssl
import sys
from importlib.metadata import version

import httpx
from minio import Minio
import urllib3


def main():
    if os.environ.get("PR5_SYNTHETIC_S3") != "explicit-isolated-fixture":
        raise ValueError("ISOLATED_SYNTHETIC_FIXTURE_REQUIRED")
    assert version("certifi") == "2026.10.19"
    context = ssl.create_default_context(cafile="/trust/root.crt")
    with httpx.Client(verify=context, trust_env=False) as client:
        response = client.get("https://source-tls:8443/pr5-synthetic-source/missing")
        assert response.status_code == 403
    try:
        with httpx.Client(trust_env=False) as client:
            client.get("https://source-tls:8443/", timeout=5)
        raise AssertionError("UNTRUSTED_TLS_ACCEPTED")
    except httpx.ConnectError:
        pass
    api = Minio("source-tls:8443", access_key=os.environ["S3_TEST_ACCESS"],
                secret_key=os.environ["S3_TEST_SECRET"], secure=True,
                http_client=urllib3.PoolManager(ssl_context=context))
    assert len(list(api.list_objects("pr5-synthetic-source", recursive=True))) == 3
    response = api.get_object("pr5-synthetic-source", "raw/synthetic.csv")
    try:
        data = response.read()
    finally:
        response.close()
        response.release_conn()
    assert data == b"SYNTHETIC NON-FINANCIAL ORIGINAL\n"
    assert api.stat_object("pr5-synthetic-source", "raw/synthetic.csv").metadata["x-amz-meta-sha256"] == hashlib.sha256(data).hexdigest()
    # Exercise the application's actual configured storage factory, including
    # clearing its process cache at each synthetic endpoint switch and rollback.
    sys.path.insert(0, "/app")
    from app.core.config import get_settings
    from app.core.storage import get_storage
    expected = {
        "raw/synthetic.csv": b"SYNTHETIC NON-FINANCIAL ORIGINAL\n",
        "model-artifacts/synthetic.json": b'{"synthetic":true,"executable":false}',
        "documents/synthetic.bin": b"SYNTHETIC-PR5-OBJECT-" * 600000,
    }
    for endpoint, bucket in [("source-tls:8443", "pr5-synthetic-source"),
                             ("target-tls:8443", "pr5-synthetic-target"),
                             ("source-tls:8443", "pr5-synthetic-source")]:
        os.environ.update(APP_ENV="test", DATABASE_URL="postgresql+asyncpg://unused.invalid/synthetic",
                          VALKEY_URL="redis://unused.invalid:6379/0",
                          MINIO_ENDPOINT=endpoint, MINIO_BUCKET_RAW=bucket,
                          MINIO_ACCESS_KEY=os.environ["S3_TEST_ACCESS"],
                          MINIO_SECRET_KEY=os.environ["S3_TEST_SECRET"],
                          MINIO_SECURE="true", MINIO_CA_CERT_PATH="/trust/root.crt")
        get_settings.cache_clear()
        get_storage.cache_clear()
        for key, original in expected.items():
            assert hashlib.sha256(get_storage().get(key)).digest() == hashlib.sha256(original).digest()
    print(json.dumps({"scope": "ISOLATED_SYNTHETIC_CORE_TLS", "certifi": version("certifi"),
                      "httpx_private_ca": "PASS", "untrusted_ca_rejected": "PASS",
                      "minio_sdk_authenticated_tls_read_sha256": "PASS",
                      "application_storage_source_target_source_rollback": "PASS",
                      "production_endpoint_changed": False}))


if __name__ == "__main__":
    main()
