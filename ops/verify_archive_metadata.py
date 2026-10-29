"""Static archive check using a current host Python; never starts the old image.

This complements the required legacy verifier. It cannot establish historical
execution reproducibility and never grants a security or model approval.
"""
import argparse
import base64
from email.parser import BytesParser
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
from concurrent.futures import ThreadPoolExecutor

from security_audit import sha256, write_new

REFERENCE = re.compile(r"[A-Za-z0-9_./:-]+@sha256:[0-9a-f]{64}\Z")
LIMIT = 30_000_000
LOCKS = ("app/requirements.lock", "app/requirements-assistant.lock")


def canonical(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def inspect_files(archive):
    """Read only bounded regular metadata files; never extract or import code."""
    files, installed = {}, {}
    with tarfile.open(fileobj=archive, mode="r|*") as stream:
        for member in stream:
            name = member.name.removeprefix("./")
            selected = name in LOCKS or bool(re.fullmatch(
                r"usr/local/lib/python3\.12/site-packages/[^/]+\.dist-info/METADATA", name))
            if not selected:
                continue
            if (not member.isfile() or member.size > 2_000_000 or name in files
                    or ".." in PurePosixPath(name).parts or len(files) > 1500):
                raise ValueError("ARCHIVE_METADATA_FILE_REJECTED")
            body = stream.extractfile(member).read(2_000_001)
            files[name] = body
            if name not in LOCKS:
                value = BytesParser().parsebytes(body, headersonly=True)
                package, version = value.get_all("Name", []), value.get_all("Version", [])
                if len(package) != 1 or len(version) != 1 or canonical(package[0]) in installed:
                    raise ValueError("AMBIGUOUS_ARCHIVE_DISTRIBUTION")
                installed[canonical(package[0])] = version[0]
    if not set(LOCKS) <= set(files):
        raise ValueError("ARCHIVE_LOCKS_MISSING")
    return files, installed


def verify_metadata(envelope, archive, image):
    if len(envelope) > LIMIT or not REFERENCE.fullmatch(image):
        raise ValueError("ARCHIVE_INPUT_REJECTED")
    value = json.loads(envelope)
    if value.get("contract") != "PR5_LEGACY_VERIFICATION_V1":
        raise ValueError("ARCHIVE_ENVELOPE_REJECTED")
    body = base64.b64decode(value["artifact_base64"], validate=True)
    if len(body) > 20_000_000 or hashlib.sha256(body).hexdigest() != value["artifact_sha256"]:
        raise ValueError("ARCHIVE_BYTES_MISMATCH")
    artifact = json.loads(body)
    if (artifact.get("contract") != "internal-data-only-model-v1"
            or artifact.get("training_code") != value["training_code"]
            or artifact.get("configuration") != value["configuration"]):
        raise ValueError("ARCHIVE_METADATA_MISMATCH")
    files, installed = inspect_files(archive)
    core, support = (files[name].decode("utf-8") for name in LOCKS)
    if artifact["training_code"].get("dependencies") != core:
        raise ValueError("ARCHIVE_DEPENDENCY_MISMATCH")
    recorded = artifact["training_code"].get("supporting_dependencies")
    if recorded is not None and recorded != support:
        raise ValueError("ARCHIVE_SUPPORT_MISMATCH")
    checked = 0
    for lock in (core, support):
        for line in lock.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("==")
            if len(parts) != 2 or installed.get(canonical(parts[0])) != parts[1]:
                raise ValueError("ARCHIVE_INSTALLED_METADATA_MISMATCH")
            checked += 1
    manifest = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}
    return {
        "contract": "PR9_STATIC_ARCHIVE_METADATA_V1", "archive_bytes_verified": True,
        "historical_dependency_metadata_verified": True, "historical_image": image,
        "artifact_sha256": value["artifact_sha256"], "checked_pins": checked,
        "core_lock_sha256": hashlib.sha256(core.encode()).hexdigest(),
        "support_lock_sha256": hashlib.sha256(support.encode()).hexdigest(),
        "metadata_manifest_sha256": hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
        "metadata_file_hashes": manifest,
        "supporting_archive_contract": "VERIFIED" if recorded is not None else "NOT_RECORDED_IN_ARCHIVE",
        "historical_image_started": False, "archived_package_code_imported": False,
        "historical_execution_reproducibility": "NOT_EXECUTED_NOT_PROVEN",
        "replaces_required_legacy_runtime_check": False, "security_approval": False,
    }


def metadata_paths(inventory, image):
    evidence = json.loads(inventory.read_text(encoding="utf-8"))
    rows = [r for r in evidence["images"] if r.get("image_reference") == image]
    if (len(rows) != 1 or rows[0].get("scan_status") != "SCANNED_EXACT_IMAGE"
            or rows[0].get("image_id") != image.split("@")[1]):
        raise ValueError("ARCHIVE_SBOM_IDENTITY_MISMATCH")
    row = rows[0]
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,40}", row.get("component", "")):
        raise ValueError("ARCHIVE_SBOM_COMPONENT_REJECTED")
    sbom = inventory.parent / (row["component"] + ".cdx.json")
    if sha256(sbom) != row["sbom_sha256"]:
        raise ValueError("ARCHIVE_SBOM_HASH_MISMATCH")
    paths = set(LOCKS)
    for component in json.loads(sbom.read_text(encoding="utf-8"))["components"]:
        for prop in component.get("properties", []):
            name = prop.get("value", "")
            if prop.get("name") == "aquasecurity:trivy:FilePath" and re.fullmatch(
                    r"usr/local/lib/python3\.12/site-packages/[^/]+\.dist-info/METADATA", name):
                paths.add(name)
    if not 2 < len(paths) <= 1500:
        raise ValueError("ARCHIVE_SBOM_METADATA_MISSING")
    return sorted(paths), row["sbom_sha256"]


def from_image(envelope, image, workdir, inventory=None):
    if len(envelope) > LIMIT:
        raise ValueError("ARCHIVE_INPUT_REJECTED")
    if not REFERENCE.fullmatch(image):
        raise ValueError("ARCHIVE_IMMUTABLE_IMAGE_REQUIRED")
    if inventory is None:
        raise ValueError("ARCHIVE_BOUND_SBOM_REQUIRED")
    paths, sbom_hash = metadata_paths(inventory, image)
    identity = subprocess.check_output(["docker", "image", "inspect", image, "--format", "{{.Id}}"], timeout=30).decode().strip()
    if identity != image.split("@")[1]:
        raise ValueError("ARCHIVE_IMAGE_IDENTITY_MISMATCH")
    container = subprocess.check_output([
        "docker", "create", "--pull", "never", "--network", "none", "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--user", "10001:10001",
        "--entrypoint", "/iip-never-start-this-container", image], timeout=30).decode().strip()
    if not re.fullmatch(r"[0-9a-f]{64}", container):
        raise ValueError("ARCHIVE_CONTAINER_ID_REJECTED")
    try:
        def read_file(name):
            # Docker copies only exact allowlisted files out of a never-started
            # container. No old Python, shell, package or model code executes.
            result = subprocess.run(["docker", "cp", container + ":/" + name, "-"],
                                    capture_output=True, timeout=60, check=True)
            if len(result.stdout) > 2_100_000:
                raise ValueError("ARCHIVE_METADATA_FILE_REJECTED")
            with tarfile.open(fileobj=io.BytesIO(result.stdout)) as tar:
                members = tar.getmembers()
                if len(members) != 1 or not members[0].isfile() or members[0].size > 2_000_000:
                    raise ValueError("ARCHIVE_METADATA_FILE_REJECTED")
                return name, tar.extractfile(members[0]).read(2_000_001)
        stream = io.BytesIO()
        total = 0
        with tarfile.open(fileobj=stream, mode="w") as tar, ThreadPoolExecutor(max_workers=4) as pool:
            for offset in range(0, len(paths), 4):
                for name, body in pool.map(read_file, paths[offset:offset + 4]):
                    total += len(body)
                    if total > 64 * 1024**2:
                        raise ValueError("ARCHIVE_METADATA_TOTAL_LIMIT")
                    member = tarfile.TarInfo(name); member.size = len(body)
                    tar.addfile(member, io.BytesIO(body))
        stream.seek(0)
        result = verify_metadata(envelope, stream, image)
        return result | {"historical_sbom_sha256": sbom_hash,
                         "filesystem_access": "EXACT_SBOM_ALLOWLIST_FILES_ONLY_NO_IMAGE_EXECUTION"}
    finally:
        subprocess.run(["docker", "rm", container], check=True, capture_output=True, timeout=30)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--envelope", required=True, type=Path)
    parser.add_argument("--workdir", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path,
                        help="Digest-bound inventory and adjacent original SBOM for the archive image")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with args.envelope.open("rb") as stream:
        body = stream.read(LIMIT + 1)
    if len(body) > LIMIT or not args.workdir.is_dir():
        raise ValueError("ARCHIVE_INPUT_REJECTED")
    result = from_image(body, args.image, args.workdir, args.inventory)
    result["verifier_sha256"] = sha256(Path(__file__))
    write_new(args.output, result)
    print("STATIC_ARCHIVE_METADATA_VERIFIED; historical execution and security approval NOT_PROVEN")


if __name__ == "__main__":
    main()
