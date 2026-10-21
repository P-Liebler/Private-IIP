"""Revalidate and publish allowlisted scan evidence; never alter original attempts."""
import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from security_audit import findings, sha256, validate_scan, validate_sbom, write_new
from security_policy import evaluate


def verify_evidence(record, raw, sbom, database):
    """Publishing must not repair failed scans or relabel their bytes/database."""
    if record.get("scan_status") != "SCANNED_EXACT_IMAGE":
        raise ValueError("ORIGINAL_SCAN_INCOMPLETE")
    if record.get("scan_sha256") != sha256(raw) or record.get("sbom_sha256") != sha256(sbom):
        raise ValueError("ORIGINAL_EVIDENCE_HASH_MISMATCH")
    if not database.get("UpdatedAt") or record.get("scanner_database") != database:
        raise ValueError("SCANNER_DATABASE_BINDING_MISMATCH")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--required", nargs="+", required=True)
    parser.add_argument("--database-metadata", type=Path, required=True)
    args = parser.parse_args()
    database = json.loads(args.database_metadata.read_text())
    args.destination.mkdir(parents=True, exist_ok=False)
    images = []
    for component in args.required:
        record_path = args.source / (component + ".record.json")
        if not record_path.exists():
            images.append({"component": component, "scan_status": "SCAN_INCOMPLETE"})
            continue
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["initial_attempt_status"] = record["scan_status"]
        record.setdefault("source_transport", "DOCKER_ARCHIVE" if record.get("archive_sha256") else "UNKNOWN")
        try:
            raw = args.source / (component + ".trivy.json")
            sbom = args.source / (component + ".cdx.json")
            verify_evidence(record, raw, sbom, database)
            value = json.loads(raw.read_text(encoding="utf-8-sig"))
            validate_scan(value, record["config_digest"])
            bom = json.loads(sbom.read_text(encoding="utf-8-sig"))
            validate_sbom(bom)
            rows = findings(value, component, record["image_id"], record["image_reference"])
            record.update(scan_status="SCANNED_EXACT_IMAGE", findings=rows,
                          revalidated_at=datetime.now(UTC).isoformat(), scan_sha256=sha256(raw),
                          sbom_sha256=sha256(sbom), sbom_file=component + ".cdx.json",
                          severity_counts={s: sum(r["severity"] == s for r in rows)
                                           for s in ("UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL")})
            # SBOMs contain package metadata, not Docker Config/Env or raw scan metadata.
            with (args.destination / (component + ".cdx.json")).open("xb") as output:
                output.write(sbom.read_bytes())
        except (OSError, ValueError, KeyError):
            record["scan_status"] = "SCAN_INCOMPLETE"
            record["security_status"] = "SCAN_INCOMPLETE"
            record.pop("findings", None)
        images.append(record)
    write_new(args.destination / "inventory.json", {
        "recorded_at": datetime.now(UTC).isoformat(), "scanner": "Trivy 0.76.0",
        "scanner_database": database,
        "security_status": evaluate(images, args.required), "images": images,
        "scope": "Full image package scans; transport recorded per image. Supported package analyzers do not establish exploitability or arbitrary native binary coverage.",
    })
    status = evaluate(images, args.required)
    print(status)
    return 2 if status == "SCAN_INCOMPLETE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
