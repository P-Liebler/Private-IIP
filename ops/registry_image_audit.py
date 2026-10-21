"""Rescan an unchanged, previously export-verified image by immutable registry digest.

Useful when a local Docker export fails. The failed export remains incomplete;
this is a separate complete registry scan, bound to the old verified config digest.
"""
import argparse
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import subprocess
import re
from security_audit import DIGEST, SCANNER_VERSION, findings, run, sha256, validate_scan, validate_sbom, write_new


def verify_binding(prior, local, reference):
    if (prior["scan_status"] != "SCANNED_EXACT_IMAGE" or prior["image_id"] != local["Id"]
            or local["Id"] != reference.split("@")[-1] or not prior.get("archive_sha256")
            or prior["architecture"] != local["Architecture"] or prior["os"] != local["Os"]
            or not DIGEST.fullmatch(prior["config_digest"])):
        raise ValueError("PRIOR_EXACT_EXPORT_BINDING_REQUIRED")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scanner", type=Path, required=True)
    parser.add_argument("--scanner-sha256", required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--binding-inventory", type=Path, required=True)
    parser.add_argument("--component", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,40}", args.component):
        parser.error("Invalid component")
    if not re.fullmatch(r"[a-z0-9][A-Za-z0-9_./:-]*@sha256:[0-9a-f]{64}", args.reference):
        parser.error("Immutable registry reference required")
    args.output.mkdir(parents=True, exist_ok=False)
    record = {"component": args.component, "image_reference": args.reference,
              "scan_status": "SCAN_INCOMPLETE", "security_status": "SCAN_INCOMPLETE"}
    try:
        if sha256(args.scanner) != args.scanner_sha256 or f"Version: {SCANNER_VERSION}" not in run([str(args.scanner), "--version"]):
            raise ValueError("SCANNER_NOT_VERIFIED")
        if "@" not in args.reference or not DIGEST.fullmatch(args.reference.split("@")[-1]):
            raise ValueError("IMMUTABLE_REGISTRY_REFERENCE_REQUIRED")
        database = json.loads((args.cache / "db/metadata.json").read_text())
        stamp = datetime.fromisoformat(database["UpdatedAt"].replace("Z", "+00:00"))
        if not timedelta(0) <= datetime.now(UTC) - stamp <= timedelta(hours=48):
            raise ValueError("STALE_SCANNER_DATABASE")
        local = json.loads(run(["docker", "image", "inspect", args.reference]))[0]
        prior = next(item for item in json.loads(args.binding_inventory.read_text(encoding="utf-8"))["images"] if item["component"] == args.component)
        verify_binding(prior, local, args.reference)
        record.update(image_id=local["Id"], config_digest=prior["config_digest"],
                      architecture=local["Architecture"], os=local["Os"],
                      configured_user=local["Config"].get("User") or "root (image default)",
                      source_transport="REGISTRY_PINNED_DIGEST_FULL_IMAGE",
                      prior_archive_sha256=prior["archive_sha256"],
                      binding_inventory_sha256=sha256(args.binding_inventory),
                      scanner_version=SCANNER_VERSION, scanner_sha256=args.scanner_sha256,
                      scanner_database=database, scanner_database_sha256=sha256(args.cache / "db/trivy.db"))
        common = [str(args.scanner), "image", "--image-src", "remote", "--cache-dir", str(args.cache),
                  "--platform", local["Os"] + "/" + local["Architecture"],
                  "--skip-db-update", "--cache-backend", "memory", "--parallel", "2", "--scanners", "vuln",
                  "--timeout", "15m", "--quiet"]
        raw, sbom = args.output / (args.component + ".trivy.json"), args.output / (args.component + ".cdx.json")
        run(common + ["--format", "json", "--output", str(raw), args.reference], timeout=960)
        value = json.loads(raw.read_text(encoding="utf-8-sig"))
        validate_scan(value, prior["config_digest"])
        run(common + ["--format", "cyclonedx", "--output", str(sbom), args.reference], timeout=960)
        validate_sbom(json.loads(sbom.read_text(encoding="utf-8-sig")))
        rows = findings(value, args.component, local["Id"], args.reference)
        record.update(scan_status="SCANNED_EXACT_IMAGE", findings=rows, scan_sha256=sha256(raw),
                      sbom_sha256=sha256(sbom), sbom_file=sbom.name,
                      severity_counts={s: sum(row["severity"] == s for row in rows) for s in ("UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL")},
                      security_status="SECURITY_BLOCKED" if any(row["severity"] in {"HIGH", "CRITICAL"} for row in rows) else "SECURITY_REVIEW_REQUIRED")
    except (OSError, ValueError, KeyError, StopIteration, subprocess.SubprocessError) as error:
        record["failure_type"] = type(error).__name__
    write_new(args.output / (args.component + ".record.json"), record)
    print(record["scan_status"])
    return 0 if record["scan_status"] == "SCANNED_EXACT_IMAGE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
