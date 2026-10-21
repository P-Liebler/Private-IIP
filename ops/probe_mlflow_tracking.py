"""Run inside disposable loopback staging MLflow; synthetic artifact only."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.error
import urllib.request
import uuid


def main():
    if os.environ.get("APP_ENV") != "staging" or os.environ.get("MINIO_ENDPOINT") != "caddy:9002":
        raise ValueError("DISPOSABLE_STAGING_REQUIRED")
    if os.environ.get("MLFLOW_SERVER_ENABLE_JOB_EXECUTION") != "false":
        raise ValueError("TRACKING_ONLY_SERVER_REQUIRED")
    os.environ["MLFLOW_HTTP_REQUEST_TIMEOUT"] = "30"
    os.environ["MLFLOW_HTTP_REQUEST_MAX_RETRIES"] = "1"
    phase = "health-and-auth"
    try:
        endpoint = "http://localhost:5000"
        with urllib.request.urlopen(endpoint + "/health", timeout=30) as response:
            assert response.status == 200
        try:
            urllib.request.urlopen(urllib.request.Request(endpoint + "/api/2.0/mlflow/experiments/search", data=b"{}", headers={"Content-Type": "application/json"}), timeout=30)
            raise AssertionError("Unauthenticated metadata was accepted")
        except urllib.error.HTTPError as error:
            assert error.code == 401
        from mlflow.tracking import MlflowClient
        phase = "metadata"
        client = MlflowClient(tracking_uri=endpoint)
        experiment = client.create_experiment("PR4_SYNTHETIC_ARTIFACT_" + uuid.uuid4().hex)
        run = client.create_run(experiment, tags={"evidence_type": "SYNTHETIC_TECHNICAL_ONLY"})
        original = b"PR4 synthetic non-financial artifact integrity probe\n"
        digest = hashlib.sha256(original).hexdigest()
        with tempfile.TemporaryDirectory(prefix="pr4-artifact-") as folder:
            # A presigned download is HTTPS to the private S3 gateway. Retain the
            # public roots and explicitly trust this disposable staging CA too.
            import certifi
            bundle = Path(folder) / "staging-trust.pem"
            bundle.write_bytes(Path(certifi.where()).read_bytes() + b"\n" + Path(os.environ["MINIO_CA_CERT_PATH"]).read_bytes())
            os.environ["REQUESTS_CA_BUNDLE"] = str(bundle)
            source = Path(folder) / "probe.txt"
            source.write_bytes(original)
            phase = "artifact-upload"
            client.log_artifact(run.info.run_id, str(source), "pr4-probe")
            phase = "artifact-download"
            restored = client.download_artifacts(run.info.run_id, "pr4-probe/probe.txt", folder)
            assert hashlib.sha256(Path(restored).read_bytes()).hexdigest() == digest
            # Exercise MLflow's real Pillow integration with a harmless RGB image.
            from PIL import Image
            phase = "synthetic-image-upload"
            client.log_image(run.info.run_id, Image.new("RGB", (8, 8), (32, 64, 96)), artifact_file="pr4-probe/image.png")
            image_file = client.download_artifacts(run.info.run_id, "pr4-probe/image.png", folder)
            with Image.open(image_file) as image:
                image.load()
                assert image.size == (8, 8) and image.mode == "RGB"
                assert image.getpixel((0, 0)) == (32, 64, 96)
        client.log_param(run.info.run_id, "synthetic_sha256", digest)
        client.set_terminated(run.info.run_id)
        print(json.dumps({"passed": True, "scope": "SYNTHETIC_STAGING_TRACKING_AND_S3",
                          "run_id": run.info.run_id, "artifact_sha256": digest,
                          "unauthenticated_metadata": "REJECTED", "job_execution": "DISABLED",
                          "synthetic_image_roundtrip": True}))
        return 0
    except Exception as error:
        print(json.dumps({"passed": False, "phase": phase, "error_type": type(error).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
