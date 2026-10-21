"""Compare package findings without treating CVE disappearance as exploit proof."""
import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from security_audit import sha256, write_new
from security_policy import evaluate


def keys(image):
    return {(row["cve"], row["package"]) for row in image["findings"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    before = json.loads(args.baseline.read_text(encoding="utf-8"))
    after = json.loads(args.current.read_text(encoding="utf-8"))
    old = {item["component"]: item for item in before["images"]}
    new = {item["component"]: item for item in after["images"]}
    status = evaluate(after["images"], list(old))
    if status == "SCAN_INCOMPLETE":
        raise ValueError("COMPARISON_SCAN_INCOMPLETE")
    components = []
    for name in sorted(old):
        previous, current = keys(old[name]), keys(new[name])
        def rows(values):
            return [{"cve": cve, "package": package} for cve, package in sorted(values)]
        components.append({"component": name, "baseline_digest": old[name]["image_id"],
                           "current_digest": new[name]["image_id"],
                           "baseline_counts": old[name]["severity_counts"],
                           "current_counts": new[name]["severity_counts"],
                           "no_longer_reported": rows(previous - current),
                           "newly_reported": rows(current - previous),
                           "retained_finding_count": len(previous & current)})
    write_new(args.output, {"recorded_at": datetime.now(UTC).isoformat(), "security_status": status,
                           "baseline_inventory_sha256": sha256(args.baseline),
                           "current_inventory_sha256": sha256(args.current),
                           "interpretation": "Per-component unique package/CVE comparison across image and DB changes; repeated binary paths are aggregated only for this diff. Disappearance alone does not prove remediation or non-exploitability. All exact current findings, paths and versions are in the hashed current inventory.",
                           "approved_exceptions": [], "components": components})
    print(status)


if __name__ == "__main__":
    main()
