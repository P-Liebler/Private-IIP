"""Build the reduced PR9 runtime from the exact locally archived PR8 image.

Docker's local image store can resolve a tagged local image while attempting a
registry lookup for its synthetic RepoDigest. Bind a dedicated alias only after
checking the real source image ID. Never pull an unreviewed replacement.
"""

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


SOURCE = "private-iip/backend@sha256:610dd6f6821c86bcaf870680a8bc623ab7947875529b833605cbfc67140831a6"
SOURCE_ID = "sha256:610dd6f6821c86bcaf870680a8bc623ab7947875529b833605cbfc67140831a6"
ALIAS = "private-iip/pr9-runtime-source:610dd6f6821c86bcaf870680a8bc623ab7947875529b833605cbfc67140831a6"


def image_id(reference: str) -> str:
    result = subprocess.run(
        ["docker", "image", "inspect", reference, "--format", "{{.Id}}"],
        capture_output=True, text=True, check=True, timeout=60,
    )
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--tag", default="private-iip/backend:pr9-runtime-candidate")
    args = parser.parse_args()
    if not re.fullmatch(r"private-iip/backend:pr(?:9|10)-[a-z0-9-]+", args.tag):
        parser.error("Use a dedicated private-iip/backend:pr9-... or pr10-... candidate tag")
    if image_id(SOURCE) != SOURCE_ID:
        raise ValueError("UNEXPECTED_SOURCE_IMAGE")
    root = Path(__file__).resolve().parents[2]
    args.output.mkdir(parents=True, exist_ok=False)
    log = args.output.resolve() / "build.log"
    record = {
        "started_at": datetime.now(UTC).isoformat(),
        "source_reference": SOURCE,
        "source_image_id": SOURCE_ID,
        "candidate_tag": args.tag,
        "status": "BUILD_INCOMPLETE",
        "release_status": "NOT_APPROVED",
        "inputs": {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ("ops/backend/Dockerfile.pr9", "ops/backend/assemble_runtime.py",
                         "backend/requirements.lock", "backend/requirements-assistant.lock")
        },
    }
    try:
        # This task-owned alias does not alter the historical tag or image.
        subprocess.run(["docker", "image", "tag", SOURCE, ALIAS], check=True, timeout=60)
        if image_id(ALIAS) != SOURCE_ID:
            raise ValueError("SOURCE_ALIAS_CHANGED")
        with log.open("xb") as stream:
            subprocess.run(
                ["docker", "build", "--progress", "plain", "--pull=false", "--build-arg",
                 "BASE_IMAGE=" + ALIAS, "--file", "ops/backend/Dockerfile.pr9",
                 "--target", "production", "--tag", args.tag, "."],
                cwd=root, stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=1800,
            )
        result_id = image_id(args.tag)
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", result_id):
            raise ValueError("INVALID_CANDIDATE_IMAGE_ID")
        record.update(status="BUILT_NOT_APPROVED", image_id=result_id)
    except (subprocess.SubprocessError, ValueError) as error:
        record["failure_type"] = type(error).__name__
    finally:
        record["finished_at"] = datetime.now(UTC).isoformat()
        if log.exists():
            record["build_log_sha256"] = hashlib.sha256(log.read_bytes()).hexdigest()
        (args.output / "build-receipt.json").write_text(json.dumps(record, indent=2) + "\n")
    print(record["status"])
    return 0 if record["status"] == "BUILT_NOT_APPROVED" else 1


if __name__ == "__main__":
    sys.exit(main())
