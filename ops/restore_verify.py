"""Restore one backup into an isolated Compose project and verify its test fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from operation_lock import acquire


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def command(project: str, file: Path, env: dict[str, str], *args: str) -> bytes:
    files = ["-f", str(file)]
    if env.get("RESTORE_OBJECT_STORE_KIND") == "seaweed-synthetic":
        files += ["-f", str(file.with_name("docker-compose.restore-seaweed.yml"))]
    result = subprocess.run(
        ["docker", "compose", "-p", project, *files, *args],
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
    return result.stdout


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
    parser.add_argument("--legacy-image", help="Explicit exact archive runtime; verified separately with network none")
    parser.add_argument("--expected-artifact-hash")
    parser.add_argument("--prediction-history-hash")
    parser.add_argument("--risk-history-hash")
    parser.add_argument("--recommendation-history-hash")
    parser.add_argument("--intelligence-history-hash")
    parser.add_argument("--collections-history-hash")
    parser.add_argument("--validation-history-hash")
    parser.add_argument("--api-image", help="Prebuilt immutable image reference, including @sha256 digest")
    parser.add_argument("--postgres-image", help="Reviewed PostgreSQL 17 candidate, including @sha256 digest")
    parser.add_argument("--object-store-image", help="Reviewed MinIO image, including @sha256 digest")
    parser.add_argument("--object-store-kind", choices=["minio", "seaweed-synthetic"], default="minio")
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("BACKUP_ROOT", "backups")))
    args = parser.parse_args()
    if args.object_store_kind == "seaweed-synthetic" and (
        not args.username.startswith("restore_") or not (args.object_store_image or "").startswith("chrislusf/seaweedfs")
    ):
        parser.error("Seaweed candidate requires explicit synthetic restore fixture and image")
    for image in (args.api_image, args.postgres_image, args.object_store_image, args.legacy_image):
        if image and not re.fullmatch(r"[A-Za-z0-9_./:-]+@sha256:[0-9a-f]{64}", image):
            parser.error("Restore image overrides require an immutable digest")
    if bool(args.dataset_id) != bool(args.expected_dataset_hash):
        parser.error("Dataset ID and expected hash must be provided together")
    if bool(args.model_id) != bool(args.expected_artifact_hash):
        parser.error("Model ID and expected artifact hash must be provided together")
    if args.legacy_image and not args.model_id:
        parser.error("Legacy verification requires an explicit archived model")
    password = os.environ.get("RESTORE_TEST_PASSWORD")
    if not password:
        parser.error("Set RESTORE_TEST_PASSWORD to the explicit fixture user's password")
    root = args.root.resolve()
    try:
        operation_lock = acquire(root)
    except RuntimeError:
        parser.error("Another backup or restore is active")
    backup = args.backup.resolve()
    if (root / "sets").resolve().parent != root:
        operation_lock.close()
        parser.error("Backup sets must remain inside the selected root")
    if backup.parent != (root / "sets").resolve():
        parser.error("Backup must be a direct child of BACKUP_ROOT/sets")
    try:
        manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("success") is not True or "postgres.dump" not in manifest["checksums"]:
            raise ValueError("Incomplete backup")
        for name, expected_hash in manifest["checksums"].items():
            path = (backup / name).resolve()
            if not path.is_relative_to(backup) or not path.is_file() or digest(path) != expected_hash:
                raise ValueError("Backup integrity failed")
    except (OSError, ValueError, KeyError, TypeError):
        stamp = datetime.now(UTC).isoformat()
        target = root / "runtime" / "restore-status.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"success": False, "started_at": stamp, "completed_at": stamp,
                                      "backup_run_id": backup.name, "error": "BACKUP_INTEGRITY_FAILED"}) + "\n", encoding="utf-8")
        operation_lock.close()
        print("Restore rejected: backup integrity failed", file=sys.stderr)
        return 1
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
        "RESTORE_TEST_LEGACY_MODEL": "true" if args.legacy_image else "false",
        "RESTORE_TEST_ARTIFACT_HASH": args.expected_artifact_hash or "",
        "RESTORE_TEST_PREDICTION_HISTORY_HASH": args.prediction_history_hash or "",
        "RESTORE_TEST_RISK_HISTORY_HASH": args.risk_history_hash or "",
        "RESTORE_TEST_INTELLIGENCE_HISTORY_HASH": args.intelligence_history_hash or "",
        "RESTORE_TEST_COLLECTIONS_HISTORY_HASH": args.collections_history_hash or "",
        "RESTORE_TEST_VALIDATION_HISTORY_HASH": args.validation_history_hash or "",
        "RESTORE_TEST_RECOMMENDATION_HISTORY_HASH": args.recommendation_history_hash or "",
        "RESTORE_OBJECT_STORE_KIND": args.object_store_kind,
    }
    s3_config = None
    environment.pop("RESTORE_S3_CONFIG", None)
    if args.object_store_kind == "seaweed-synthetic":
        s3_config = root / "runtime" / (project + "-synthetic-s3.json")
        s3_config.parent.mkdir(parents=True, exist_ok=True)
        with s3_config.open("x", encoding="utf-8") as stream:
            json.dump({"identities": [{"name": "synthetic-restore",
                "credentials": [{"accessKey": "restore_user", "secretKey": environment["RESTORE_MINIO_PASSWORD"]}],
                "actions": ["Admin", "Read", "Write", "List", "Tagging"]}]}, stream)
        environment["RESTORE_S3_CONFIG"] = str(s3_config)
    for key, value in (("RESTORE_API_IMAGE", args.api_image), ("RESTORE_POSTGRES_IMAGE", args.postgres_image), ("RESTORE_OBJECT_STORE_IMAGE", args.object_store_image)):
        if value:
            environment[key] = value
        else:
            environment.pop(key, None)
    status: dict[str, object] = {
        "started_at": datetime.now(UTC).isoformat(),
        "success": False,
        "object_store_kind": args.object_store_kind,
        "backup_run_id": backup.name,
        "image_contract": {"api": args.api_image, "postgres": args.postgres_image, "object_store": args.object_store_image},
        "verified_backup_files": len(manifest["checksums"]),
        "expected_value": args.expected_value,
        "archive_contracts": {"dataset": args.expected_dataset_hash, "model": args.expected_artifact_hash,
                              "predictions": args.prediction_history_hash, "risk": args.risk_history_hash,
                              "recommendations": args.recommendation_history_hash, "intelligence": args.intelligence_history_hash,
                              "collections": args.collections_history_hash, "validation": args.validation_history_hash},
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
        if args.dataset_id:
            probe = command(project, compose_file, environment, "exec", "-T", "postgres",
                            "psql", "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-U", "restore_user",
                            "-d", "investment", "-c",
                            Path(__file__).with_name("postgres").joinpath("restore_contract.sql").read_text(encoding="utf-8"))
            status["postgres_environment"] = next(json.loads(line) for line in probe.decode().splitlines() if line.startswith("{"))
            status["postgres_contract_probe"] = "PASS"
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
            project, compose_file, environment, "up", "-d", "--no-build" if args.api_image else "--build", "--wait", "api", "valkey"
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
        if args.legacy_image:
            from verify_legacy_model import verify
            envelope = command(project, compose_file, environment, "exec", "-T", "api",
                               "python", "-m", "scripts.export_legacy_model", "--model-id",
                               args.model_id, "--username", args.username)
            try:
                status["legacy_verification"] = verify(envelope, args.legacy_image)
            except (ValueError, subprocess.SubprocessError) as error:
                raise RuntimeError("ISOLATED_LEGACY_VERIFICATION_FAILED") from error
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
        try:
            command(project, compose_file, environment, "down", "-v", "--remove-orphans")
            status["cleanup_success"] = True
            if s3_config is not None:
                if s3_config.resolve().parent != (root / "runtime").resolve():
                    raise RuntimeError("UNSAFE_SYNTHETIC_CONFIG_PATH")
                s3_config.unlink()
        except RuntimeError:
            status["cleanup_success"] = False
            print("Isolated restore cleanup failed; inspect the restore project", file=sys.stderr)
        status["cleanup_completed_at"] = datetime.now(UTC).isoformat()
        target.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        operation_lock.close()


if __name__ == "__main__":
    sys.exit(main())
