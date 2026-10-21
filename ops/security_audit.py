"""Scan exact local images without mounting a Docker socket into the scanner.

Raw scanner outputs stay in the selected private output directory. Public reports
contain an explicit allowlist of fields; container environments are never exported.
Requires a separately verified Trivy 0.76.0 executable and a current vulnerability DB.
"""
import argparse
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
from redact_test_artifacts import redact

SCANNER_VERSION = "0.76.0"
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(arguments, timeout=600):
    return subprocess.run(arguments, check=True, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout).stdout


def write_new(path, value):
    """Do not overwrite completed evidence or an existing RC manifest."""
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def validate_sbom(value):
    if value.get("bomFormat") != "CycloneDX" or value.get("specVersion") not in {"1.5", "1.6", "1.7"}:
        raise ValueError("UNSUPPORTED_SBOM")
    components = value.get("components")
    if not isinstance(components, list) or not components:
        raise ValueError("EMPTY_SBOM")
    if any(not item.get("name") or not item.get("type") for item in components):
        raise ValueError("INVALID_SBOM_COMPONENT")


def validate_scan(value, image_id):
    if value.get("SchemaVersion") != 2 or value.get("ArtifactType") != "container_image":
        raise ValueError("UNSUPPORTED_IMAGE_SCAN")
    if value.get("Metadata", {}).get("ImageID") != image_id:
        raise ValueError("DIGEST_MISMATCH")
    results = value.get("Results")
    if not isinstance(results, list) or not results:
        raise ValueError("EMPTY_SCAN")


def archive_config_digest(path):
    # Docker's containerd store may expose a manifest digest as inspect.Id.
    # Trivy Metadata.ImageID is the config digest. Bind these through the exact
    # exported archive, and verify the config bytes rather than equating the two.
    with tarfile.open(path) as archive:
        manifests = json.load(archive.extractfile("manifest.json"))
        if len(manifests) != 1:
            raise ValueError("AMBIGUOUS_IMAGE_ARCHIVE")
        config_path = manifests[0]["Config"]
        config = archive.extractfile(config_path).read()
        digest = hashlib.sha256(config).hexdigest()
        if digest not in config_path:
            raise ValueError("ARCHIVE_CONFIG_CHECKSUM_MISMATCH")
        return "sha256:" + digest


def findings(value, component, image_id, reference):
    records = []
    tagged = reference.split("@")[0]
    repository, tag = (tagged.rsplit(":", 1) if ":" in tagged.rsplit("/", 1)[-1] else (tagged, None))
    for result in value["Results"]:
        for item in result.get("Vulnerabilities", []):
            records.append({
                "component": component, "image_reference": reference, "image_id": image_id,
                "image_repository": repository, "image_tag": tag, "image_digest": image_id,
                "package": item.get("PkgName"),
                "package_path": item.get("PkgPath") or (result.get("Target") if result.get("Class") == "lang-pkgs" else None),
                "package_type": result.get("Type"),
                "installed_version": item.get("InstalledVersion"),
                "cve": item.get("VulnerabilityID"), "severity": item.get("Severity"),
                "fixed_version": item.get("FixedVersion") or None,
                "advisory": item.get("PrimaryURL"),
                "official_advisory": next((url for url in item.get("References", [])
                    if any(host in url for host in ("security-tracker.debian.org/", "pkg.go.dev/vuln/", 
                        "/security/advisories/", "github.com/advisories/", "nvd.nist.gov/vuln/detail/"))), None),
                "status": "FIX_AVAILABLE" if item.get("FixedVersion") else "FIX_UNAVAILABLE",
                "remediation_status": "REQUIRES_OPERATOR_REVIEW",
                "exploitability_status": "REQUIRES_OPERATOR_REVIEW",
                "reachability_status": "REQUIRES_OPERATOR_REVIEW",
                "exploitability": "NOT_ESTABLISHED", "reachability": "REQUIRES_OPERATOR_REVIEW",
                "runtime_usage": "Not dismissed from package presence alone",
                "exposure": "See component remediation matrix; network isolation is not a patch",
                "proposed_remediation": "Evaluate supported patch/rebuild, rescan and run compatibility gates",
                "residual_risk": "Unreviewed findings remain open; no approved exception",
                "reviewer": None, "review_date": None, "reviewed_at": None,
            })
    return records


def scan_image(scanner, cache, output, component, reference, audit_metadata=None):
    record = {"component": component, "image_reference": reference,
              "scan_status": "SCAN_INCOMPLETE", "security_status": "SCAN_INCOMPLETE"}
    record.update(audit_metadata or {})
    archive = output / (component + ".tar")
    raw = output / (component + ".trivy.json")
    sbom = output / (component + ".cdx.json")
    created_archive = False
    try:
        inspected = json.loads(run(["docker", "image", "inspect", reference]))[0]
        image_id = inspected["Id"]
        if not DIGEST.fullmatch(image_id):
            raise ValueError("INVALID_IMAGE_DIGEST")
        record.update(image_id=image_id, repo_digests=inspected.get("RepoDigests", []),
                      architecture=inspected["Architecture"], os=inspected["Os"],
                      configured_user=inspected["Config"].get("User") or "root (image default)")
        if any(p.exists() for p in (archive, raw, sbom)):
            raise ValueError("EVIDENCE_ALREADY_EXISTS")
        created_archive = True
        run(["docker", "image", "save", image_id, "-o", str(archive)], timeout=900)
        config_digest = archive_config_digest(archive)
        record["config_digest"] = config_digest
        record["archive_sha256"] = sha256(archive)
        common = [str(scanner), "image", "--input", str(archive), "--cache-dir", str(cache),
                  "--skip-db-update", "--cache-backend", "memory", "--parallel", "2",
                  "--scanners", "vuln", "--timeout", "10m", "--quiet"]
        run(common + ["--format", "json", "--output", str(raw)], timeout=660)
        value = json.loads(raw.read_text(encoding="utf-8-sig"))
        validate_scan(value, config_digest)
        run(common + ["--format", "cyclonedx", "--output", str(sbom)], timeout=660)
        validate_sbom(json.loads(sbom.read_text(encoding="utf-8-sig")))
        records = findings(value, component, image_id, reference)
        record.update(scan_status="SCANNED_EXACT_IMAGE", sbom_sha256=sha256(sbom),
                      sbom_file=sbom.name, scan_sha256=sha256(raw), findings=records,
                      severity_counts={s: sum(v["severity"] == s for v in records)
                                       for s in ("UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL")},
                      security_status="SECURITY_BLOCKED" if any(v["severity"] in {"HIGH", "CRITICAL"}
                                                                for v in records) else "SECURITY_REVIEW_REQUIRED")
    except (subprocess.SubprocessError, ValueError, OSError, KeyError) as error:
        # Exception text can include command/registry/container details; do not export it.
        record["failure_type"] = type(error).__name__
        if isinstance(error, ValueError) and re.fullmatch(r"[A-Z_]+", str(error)):
            record["failure_code"] = str(error)
        if isinstance(error, subprocess.CalledProcessError):
            (output / (component + ".failure.log")).write_text(redact(error.stderr or ""), encoding="utf-8")
    finally:
        # Only the exact file this invocation created inside the selected output root.
        if created_archive and archive.is_file() and archive.parent.resolve() == output.resolve():
            archive.unlink()
    write_new(output / (component + ".record.json"), record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scanner", required=True, type=Path)
    parser.add_argument("--scanner-sha256", required=True)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--image", action="append", required=True, help="component=exact local image reference")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    if sha256(args.scanner) != args.scanner_sha256.lower():
        raise ValueError("SCANNER_CHECKSUM_MISMATCH")
    version = run([str(args.scanner), "--version"])
    if f"Version: {SCANNER_VERSION}" not in version:
        raise ValueError("UNSUPPORTED_SCANNER")
    database = json.loads((args.cache / "db/metadata.json").read_text())
    updated = datetime.fromisoformat(database["UpdatedAt"].replace("Z", "+00:00"))
    if not timedelta(0) <= datetime.now(UTC) - updated <= timedelta(hours=48):
        raise ValueError("STALE_SCANNER_DATABASE")
    inventory = []
    audit_metadata = {"scanner_version": SCANNER_VERSION, "scanner_sha256": args.scanner_sha256.lower(),
                      "scanner_database": database, "scanner_database_sha256": sha256(args.cache / "db/trivy.db")}
    write_new(args.output / "audit-run.json", audit_metadata)
    for specification in args.image:
        component, reference = specification.split("=", 1)
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,40}", component):
            raise ValueError("INVALID_COMPONENT_NAME")
        print(f"Scanning {component}", flush=True)
        record = scan_image(args.scanner.resolve(), args.cache.resolve(), args.output.resolve(), component, reference, audit_metadata)
        inventory.append(record)
        print(f'{component}: {record["scan_status"]}', flush=True)
    write_new(args.output / "inventory.json", {
        "recorded_at": datetime.now(UTC).isoformat(), "scanner_version": SCANNER_VERSION,
        "scanner_sha256": args.scanner_sha256.lower(), "database": database,
        "scope": "Full image; supported OS/language package analyzers; no proof of exploitability or arbitrary native binary coverage",
        "security_status": "SCAN_INCOMPLETE" if any(r["scan_status"] == "SCAN_INCOMPLETE" for r in inventory)
                           else "SECURITY_BLOCKED" if any(r["security_status"] == "SECURITY_BLOCKED" for r in inventory)
                           else "SECURITY_REVIEW_REQUIRED", "images": inventory,
    })
    return 2 if any(r["scan_status"] == "SCAN_INCOMPLETE" for r in inventory) else 0


if __name__ == "__main__":
    sys.exit(main())
