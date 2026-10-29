"""Verify archived JSON model bytes in their exact, networkless legacy image.

This operator-only process never exposes Docker to the API. It does not load a
model into the patched API, run collectors, promote models or write archive data.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from uuid import uuid4

from security_audit import write_new

MAX_ENVELOPE = 30_000_000

# Deliberately standard-library-only: no application, provider or executable
# serialization imports. The legacy image's installed package pins are checked.
VERIFIER = r'''
import base64, hashlib, importlib.metadata, json, pathlib, sys
body = sys.stdin.buffer.read(30000001)
assert len(body) <= 30000000, "LEGACY_INPUT_LIMIT"
envelope = json.loads(body)
assert envelope["contract"] == "PR5_LEGACY_VERIFICATION_V1"
data = base64.b64decode(envelope["artifact_base64"], validate=True)
assert len(data) <= 20000000
assert hashlib.sha256(data).hexdigest() == envelope["artifact_sha256"]
artifact = json.loads(data)
assert artifact["contract"] == "internal-data-only-model-v1"
assert artifact["training_code"] == envelope["training_code"]
assert artifact["configuration"] == envelope["configuration"]
core = pathlib.Path("/app/requirements.lock").read_text(encoding="utf-8")
support = pathlib.Path("/app/requirements-assistant.lock").read_text(encoding="utf-8")
assert artifact["training_code"]["dependencies"] == core, "LEGACY_DEPENDENCY_MISMATCH"
recorded_support = artifact["training_code"].get("supporting_dependencies")
if recorded_support is not None:
    assert recorded_support == support, "LEGACY_SUPPORT_MISMATCH"
for lock in (core, support):
    for line in lock.splitlines():
        pin = line.strip()
        if not pin or pin.startswith("#"):
            continue
        name, version = pin.split("==", 1)
        assert importlib.metadata.version(name) == version, "LEGACY_INSTALLED_PACKAGE_MISMATCH"
assert not pathlib.Path("/var/run/docker.sock").exists()
print(json.dumps({"contract":"PR5_LEGACY_VERIFICATION_V1", "verified":True,
    "artifact_sha256":envelope["artifact_sha256"],
    "core_lock_sha256":hashlib.sha256(core.encode()).hexdigest(),
    "support_lock_sha256":hashlib.sha256(support.encode()).hexdigest(),
    "supporting_archive_contract":"VERIFIED" if recorded_support is not None else "NOT_RECORDED_IN_ARCHIVE",
    "scope":"ARCHIVED_BYTES_AND_EXACT_INSTALLED_CONTRACT_ONLY_NO_FORECAST_VALIDATION"}))
'''


def _containers(label: str) -> list[str]:
    result = subprocess.run(
        ["docker", "container", "ls", "--all", "--quiet", "--no-trunc", "--filter", label],
        capture_output=True, timeout=30, check=False,
    )
    if result.returncode or len(result.stdout) > 16000:
        raise ValueError("LEGACY_CONTAINER_CLEANUP_UNCONFIRMED")
    ids = result.stdout.decode("ascii").split()
    if len(ids) > 1 or any(not re.fullmatch(r"[0-9a-f]{64}", item) for item in ids):
        raise ValueError("LEGACY_CONTAINER_CLEANUP_UNCONFIRMED")
    return ids


def _cleanup(session: str, identity: str | None) -> None:
    """Remove only this attempt's labelled container; prove daemon-side absence."""
    owned = "label=iip.legacy-verifier-session=" + session
    try:
        ids = _containers(owned)
        if identity is not None and any(item != identity for item in ids):
            raise ValueError("LEGACY_CONTAINER_CLEANUP_UNCONFIRMED")
        for container in ids:
            # A force-remove kills the daemon-side process, including when the
            # attached Docker client has already timed out or disconnected.
            subprocess.run(["docker", "container", "rm", "--force", container],
                           capture_output=True, timeout=30, check=False)
        if _containers(owned):
            raise ValueError("LEGACY_CONTAINER_CLEANUP_UNCONFIRMED")
        if identity is not None and _containers("id=" + identity):
            raise ValueError("LEGACY_CONTAINER_CLEANUP_UNCONFIRMED")
    except (subprocess.SubprocessError, OSError, UnicodeError) as error:
        raise ValueError("LEGACY_CONTAINER_CLEANUP_UNCONFIRMED") from error


def verify(envelope: bytes, image: str) -> dict:
    if len(envelope) > MAX_ENVELOPE:
        raise ValueError("LEGACY_INPUT_LIMIT")
    if not re.fullmatch(r"[A-Za-z0-9_./:-]+@sha256:[0-9a-f]{64}", image):
        raise ValueError("LEGACY_IMMUTABLE_IMAGE_REQUIRED")
    # Create first so the exact daemon-side identity is known before execution.
    # No env propagation, mounts, host networking, sockets or writable root.
    session, identity = uuid4().hex, None
    try:
        created = subprocess.run(
            ["docker", "create", "--pull", "never", "--network", "none",
             "--name", "iip-legacy-verify-" + session,
             "--label", "iip.legacy-verifier-session=" + session,
             "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
             "--user", "10001:10001", "--pids-limit", "32", "--memory", "512m",
             "--cpus", "1", "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
             "-i", image, "python", "-I", "-B", "-c", VERIFIER],
            capture_output=True, timeout=30, check=False,
        )
        if created.returncode or not re.fullmatch(rb"[0-9a-f]{64}\s*", created.stdout):
            raise ValueError("LEGACY_CONTAINER_CREATE_FAILED")
        identity = created.stdout.decode("ascii").strip()
        result = subprocess.run(
            ["docker", "start", "--attach", "--interactive", identity],
            input=envelope, capture_output=True, timeout=90, check=False,
        )
    except (subprocess.SubprocessError, OSError) as error:
        raise ValueError("LEGACY_VERIFICATION_FAILED") from error
    finally:
        _cleanup(session, identity)
    if result.returncode or len(result.stdout) > 16000:
        # Never print model bytes or archive metadata from a failed process.
        raise ValueError("LEGACY_VERIFICATION_FAILED")
    value = json.loads(result.stdout)
    expected = json.loads(envelope)
    if value.get("verified") is not True or value.get("artifact_sha256") != expected["artifact_sha256"]:
        raise ValueError("LEGACY_RESULT_MISMATCH")
    return value | {"image": image, "network": "none", "read_only": True,
                    "verifier_sha256": hashlib.sha256(VERIFIER.encode()).hexdigest(),
                    "container_cleanup_verified": True,
                    "container_isolation_contract": "PR10_OWNED_LEGACY_CONTAINER_V1"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--envelope", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Read bounded input; require the caller to store private exports outside Git.
    with args.envelope.open("rb") as source:
        body = source.read(MAX_ENVELOPE + 1)
    value = verify(body, args.image)
    write_new(args.output, value)
    print("Legacy verification PASSED; no network, archive writes or promotion")


if __name__ == "__main__":
    main()
