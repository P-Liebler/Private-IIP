"""Restore one backup into an isolated Compose project and verify its test fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def command(project: str, file: Path, env: dict[str, str], *args: str) -> None:
    result = subprocess.run(
        ["docker", "compose", "-p", project, "-f", str(file), *args],
        env=env,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        detail = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        for name, value in env.items():
            if value and any(
                part in name.upper()
                for part in (
                    "PASSWORD",
                    "TOKEN",
                    "SECRET",
                    "API_KEY",
                    "ACCESS_KEY",
                    "ENCRYPTION_KEY",
                )
            ):
                detail = detail.replace(value, "[REDACTED]")
        diagnostic = Path(env["RESTORE_BACKUP_ROOT"]) / "runtime" / "restore-command-failure.log"
        diagnostic.parent.mkdir(parents=True, exist_ok=True)
        diagnostic.write_text("step=" + repr(args[:4]) + "\n" + detail[-16000:], encoding="utf-8")
        print(
            ("Restore step failed: " + repr(args[:4]) + "\n" + detail[-4000:])
            .encode("ascii", "backslashreplace")
            .decode(),
            file=sys.stderr,
        )
        raise RuntimeError(f"Isolated Compose step failed ({result.returncode})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("backup", type=Path)
    parser.add_argument("--username", required=True)
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--raw-id", required=True)
    parser.add_argument("--expected-value", required=True)
    parser.add_argument("--dataset-id")
    parser.add_argument("--expected-dataset-hash")
    parser.add_argument("--model-id")
    parser.add_argument("--expected-artifact-hash")
    parser.add_argument("--prediction-history-hash")
    parser.add_argument("--risk-history-hash")
    parser.add_argument("--recommendation-history-hash")
    parser.add_argument("--intelligence-history-hash")
    parser.add_argument("--collections-history-hash")
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("BACKUP_ROOT", "backups")))
    args = parser.parse_args()
    if bool(args.dataset_id) != bool(args.expected_dataset_hash):
        parser.error("Dataset ID and expected hash must be provided together")
    if bool(args.model_id) != bool(args.expected_artifact_hash):
        parser.error("Model ID and expected artifact hash must be provided together")
    password = os.environ.get("RESTORE_TEST_PASSWORD")
    if not password:
        parser.error("Set RESTORE_TEST_PASSWORD to the explicit fixture user's password")
    root = args.root.resolve()
    backup = args.backup.resolve()
    if backup.parent != (root / "sets").resolve():
        parser.error("Backup must be a direct child of BACKUP_ROOT/sets")
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("success") is not True:
        parser.error("Backup manifest is not successful")
    for name, expected_hash in manifest["checksums"].items():
        path = (backup / name).resolve()
        if not path.is_relative_to(backup) or not path.is_file() or digest(path) != expected_hash:
            parser.error(f"Backup checksum mismatch: {name}")
    project = "iip-restore-" + secrets.token_hex(5)
    compose_file = Path(__file__).with_name("docker-compose.restore.yml").resolve()
    environment = {
        **os.environ,
        "RESTORE_DB_PASSWORD": secrets.token_hex(24),
        "RESTORE_MINIO_PASSWORD": secrets.token_hex(24),
        "RESTORE_BACKUP_ROOT": str(root),
        "RESTORE_TEST_USERNAME": args.username,
        "RESTORE_TEST_PASSWORD": password,
        "RESTORE_TEST_PORTFOLIO_ID": args.portfolio_id,
        "RESTORE_TEST_RAW_ID": args.raw_id,
        "RESTORE_TEST_VALUE": args.expected_value,
        "RESTORE_TEST_DATASET_ID": args.dataset_id or "",
        "RESTORE_TEST_DATASET_HASH": args.expected_dataset_hash or "",
        "RESTORE_TEST_MODEL_ID": args.model_id or "",
        "RESTORE_TEST_ARTIFACT_HASH": args.expected_artifact_hash or "",
        "RESTORE_TEST_PREDICTION_HISTORY_HASH": args.prediction_history_hash or "",
        "RESTORE_TEST_RISK_HISTORY_HASH": args.risk_history_hash or "",
        "RESTORE_TEST_INTELLIGENCE_HISTORY_HASH": args.intelligence_history_hash or "",
        "RESTORE_TEST_COLLECTIONS_HISTORY_HASH": args.collections_history_hash or "",
        "RESTORE_TEST_RECOMMENDATION_HISTORY_HASH": args.recommendation_history_hash or "",
    }
    status: dict[str, object] = {
        "started_at": datetime.now(UTC).isoformat(),
        "success": False,
        "backup_run_id": backup.name,
    }
    try:
        command(project, compose_file, environment, "up", "-d", "--wait", "postgres", "minio")
        command(
            project,
            compose_file,
            environment,
            "cp",
            str(backup / "postgres.dump"),
            "postgres:/tmp/restore.dump",
        )
        command(
            project,
            compose_file,
            environment,
            "exec",
            "-T",
            "postgres",
            "pg_restore",
            "--exit-on-error",
            "--no-owner",
            "--no-privileges",
            "-U",
            "restore_user",
            "-d",
            "investment",
            "/tmp/restore.dump",
        )
        command(
            project,
            compose_file,
            environment,
            "--profile",
            "ops",
            "run",
            "--rm",
            "mc",
            "mb",
            "-p",
            "restored/raw-ingestions",
        )
        command(
            project,
            compose_file,
            environment,
            "--profile",
            "ops",
            "run",
            "--rm",
            "mc",
            "mirror",
            f"/backup/sets/{backup.name}/raw",
            "restored/raw-ingestions",
        )
        command(
            project, compose_file, environment, "up", "-d", "--build", "--wait", "api", "valkey"
        )
        command(
            project,
            compose_file,
            environment,
            "exec",
            "-T",
            "api",
            "python",
            "-m",
            "scripts.verify_restored_fixture",
        )
        status.update({"success": True, "completed_at": datetime.now(UTC).isoformat()})
        print("Isolated restore PASSED")
        return 0
    except (OSError, RuntimeError) as error:
        status.update(
            {"completed_at": datetime.now(UTC).isoformat(), "error": type(error).__name__}
        )
        print(f"Isolated restore FAILED: {type(error).__name__}", file=sys.stderr)
        return 1
    finally:
        target = root / "runtime" / "restore-status.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        try:
            command(project, compose_file, environment, "down", "-v", "--remove-orphans")
        except RuntimeError:
            print("Isolated restore cleanup failed; inspect the restore project", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
