"""Fail-closed release evaluation, separate from successful scanner execution."""
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import argparse
import re

REQUIRED_EXCEPTION_FIELDS = {
    "cve", "component", "digest", "technical_reason", "reachability_evidence",
    "mitigations", "reviewer", "approval_reference", "approved_at", "expires_at",
    "re_review_trigger",
}


def approved_exception(exception, finding, now):
    if any(not exception.get(field) for field in REQUIRED_EXCEPTION_FIELDS):
        return False
    if any(exception[key] != finding[key] for key in ("cve", "component")):
        return False
    if exception["digest"] != finding["image_id"]:
        return False
    try:
        approved = datetime.fromisoformat(exception["approved_at"].replace("Z", "+00:00"))
        expires = datetime.fromisoformat(exception["expires_at"].replace("Z", "+00:00"))
        return approved.tzinfo is not None and expires.tzinfo is not None and approved <= now < expires <= approved + timedelta(days=90)
    except (ValueError, TypeError):
        return False


def evaluate(images, required, exceptions=(), now=None):
    now = now or datetime.now(UTC)
    by_component = {image["component"]: image for image in images}
    if len(by_component) != len(images) or set(required) != set(by_component):
        return "SCAN_INCOMPLETE"
    for image in images:
        if image.get("scan_status") != "SCANNED_EXACT_IMAGE" or not image.get("sbom_sha256"):
            return "SCAN_INCOMPLETE"
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", image.get("image_id", "")):
            return "SCAN_INCOMPLETE"
        if not isinstance(image.get("findings"), list):
            return "SCAN_INCOMPLETE"
    for image in images:
        for finding in image["findings"]:
            approved = any(approved_exception(item, finding, now) for item in exceptions)
            if finding["severity"] in {"HIGH", "CRITICAL"} and not approved:
                return "SECURITY_BLOCKED"
    # Zero package CVEs is not proof that every manual/runtime gate passed.
    return "SECURITY_REVIEW_REQUIRED"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--required", nargs="+", required=True)
    parser.add_argument("--critical-only", action="store_true", help="CI critical-package gate only; never release approval")
    args = parser.parse_args()
    try:
        value = json.loads(args.inventory.read_text(encoding="utf-8"))
        status = evaluate(value["images"], args.required)
    except (OSError, ValueError, KeyError, TypeError):
        status = "SCAN_INCOMPLETE"
    print(status)
    if args.critical_only and status != "SCAN_INCOMPLETE":
        return 1 if any(f["severity"] == "CRITICAL" for image in value["images"] for f in image["findings"]) else 0
    return 2 if status == "SCAN_INCOMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
