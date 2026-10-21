"""Scan Git-visible source files, excluding ignored operator secrets and backups.

Never publish scanner matches. A nonzero finding count needs explicit review;
failed scans retain null counts and cannot become a successful security check.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from security_audit import run, sha256, write_new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scanner", type=Path, required=True)
    parser.add_argument("--scanner-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scanner = args.scanner.resolve()
    if sha256(scanner) != args.scanner_sha256.lower():
        raise ValueError("SCANNER_CHECKSUM_MISMATCH")
    args.output.mkdir(parents=True, exist_ok=False)
    root = Path(run(["git", "rev-parse", "--show-toplevel"]).strip()).resolve()
    paths = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                           cwd=root, check=True, capture_output=True).stdout.decode("utf-8").split("\0")
    result = {"status": "SECURITY_SCAN_INCOMPLETE", "finding_count": None, "findings": [], "source_files": {}}
    with tempfile.TemporaryDirectory(prefix="iip-source-security-") as folder:
        exported = Path(folder)
        for name in sorted(set(paths) - {""}):
            source = root / name
            if source.is_symlink() or not source.resolve().is_relative_to(root):
                raise ValueError("SOURCE_EXPORT_PATH_REJECTED")
            if not source.is_file():
                continue
            target = exported / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            result["source_files"][name] = sha256(target)
        raw = args.output.resolve() / "private-secret-scan.json"
        try:
            run([str(scanner), "fs", "--scanners", "secret", "--format", "json", "--output", str(raw), "--quiet", str(exported)], timeout=300)
            report = json.loads(raw.read_text(encoding="utf-8-sig"))
            if report.get("SchemaVersion") != 2 or not isinstance(report.get("Results", []), list):
                raise ValueError("INVALID_SECRET_SCAN")
            for entry in report.get("Results", []):
                for secret in entry.get("Secrets", []):
                    result["findings"].append({
                        "file": entry.get("Target", "").replace(str(exported), "SOURCE"),
                        "rule_id": secret.get("RuleID"), "severity": secret.get("Severity"),
                        "line": secret.get("StartLine"),
                        "match_sha256": hashlib.sha256(secret.get("Match", "").encode()).hexdigest(),
                        "review_status": "REQUIRES_OPERATOR_REVIEW",
                    })
            result.update(finding_count=len(result["findings"]),
                          status="SECRETS_REVIEW_REQUIRED" if result["findings"] else "NO_KNOWN_SECRET_FINDINGS")
        except (subprocess.SubprocessError, ValueError, OSError):
            pass
        finally:
            # Matches may contain credentials; retain only the safe finding index.
            raw.unlink(missing_ok=True)
    write_new(args.output / "source-security.json", result)
    print(result["status"])
    return 0 if result["status"] == "NO_KNOWN_SECRET_FINDINGS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
