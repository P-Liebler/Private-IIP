"""Append a private, manifest-bound operator test receipt; never grants host/release approval."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from core_storage import permission_status, redirected
from security_audit import sha256, write_new

STEPS = {"private_hostname", "vpn", "dns", "windows_client", "android_client", "tls_ca",
         "login_totp", "backup", "restore", "secrets_recovery", "alert_delivery", "host_reboot"}


def receipt(step, result, operator, hostname, manifest: Path, evidence: Path, output: Path, root: Path):
    if step not in STEPS or result not in {"PASS", "FAIL", "PENDING"} or not operator.strip() or not hostname.strip():
        raise ValueError("HOST_RECEIPT_INPUT_INVALID")
    if output.resolve().is_relative_to(root.resolve()) and not output.resolve().is_relative_to(root / "backups"):
        raise ValueError("HOST_RECEIPT_MUST_STAY_PRIVATE")
    if (not output.parent.is_dir() or redirected(output.parent)
            or permission_status(output.parent) != "PRIVATE"
            or permission_status(evidence.parent) != "PRIVATE"):
        raise ValueError("HOST_RECEIPT_PRIVATE_DIRECTORY_REQUIRED")
    for path in (manifest, evidence):
        if not path.is_file() or path.stat().st_size == 0 or redirected(path):
            raise ValueError("HOST_RECEIPT_EVIDENCE_MISSING_OR_UNSAFE")
    if evidence.resolve().is_relative_to(root.resolve()) and not evidence.resolve().is_relative_to(root / "backups"):
        raise ValueError("HOST_EVIDENCE_MUST_STAY_PRIVATE")
    return {"contract": "PRIVATE_CORE_HOST_CHECK_V1", "step": step, "operator_result": result,
            "operator": operator, "private_hostname": hostname, "recorded_at": datetime.now(UTC).isoformat(),
            "manifest_sha256": sha256(manifest), "evidence_sha256": sha256(evidence),
            "evidence_file": str(evidence.resolve()), "record_type": "OPERATOR_ATTESTATION_REQUIRES_REVIEW",
            "target_status": "TARGET_HOST_NOT_VERIFIED_BY_RECEIPT_TOOL", "release_status": "NOT_APPROVED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", choices=sorted(STEPS), required=True)
    parser.add_argument("--result", choices=["PASS", "FAIL", "PENDING"], required=True)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_new(args.output, receipt(args.step, args.result, args.operator, args.hostname, args.manifest,
                                  args.evidence, args.output, Path.cwd().resolve()))
    print("PRIVATE_OPERATOR_RECEIPT_RECORDED", "NOT_APPROVED")


if __name__ == "__main__":
    main()
