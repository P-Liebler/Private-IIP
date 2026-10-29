"""Back up PostgreSQL and immutable MinIO raw objects to a configured host directory.

Run from the repository root with BACKUP_ROOT set to an independent mounted disk.
The script never copies application secrets into an artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from operation_lock import acquire


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compose(file: Path | list[Path], env_file: Path | None, *args: str, stdout=None) -> bytes | None:
    files = file if isinstance(file, list) else [file]
    command = ["docker", "compose", *[item for path in files for item in ("-f", str(path))]]
    if env_file:
        command += ["--env-file", str(env_file)]
    command += list(args)
    environment = None
    if env_file:
        from preflight import compose_environment, read_env
        values = read_env(env_file)
        # Overlay-only variables must also be protected from ambient overrides.
        environment = compose_environment(values, files[0])
        for path in files:
            for key in re.findall(r"\$\{([A-Z][A-Z0-9_]*)", path.read_text(encoding="utf-8")):
                if key not in values:
                    environment.pop(key, None)
    result = subprocess.run(command, env=environment, stdout=stdout, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RuntimeError(f"Docker Compose command failed ({result.returncode})")
    return result.stdout


def atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def migration_evidence(folder: Path) -> dict[str, bytes]:
    """Read explicit receipts; never sweep configs/credentials into backups."""
    from s3_migrate import validate_manifest

    names = ["migration-manifest.json", "migration-journal.json", "references.json"]
    optional = ("migration-result.json", "source-checkpoint.json", "target-checkpoint.json",
                "target-post-qa-checkpoint.json", "target-qa-collection-delta.json")
    names.extend(name for name in optional if (folder / name).exists())
    payloads = {}
    for name in names:
        path = folder / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
            raise RuntimeError("Migration evidence file unavailable or unsafe")
        payloads[name] = path.read_bytes()
    parsed = {name: json.loads(data) for name, data in payloads.items()}
    manifest = parsed["migration-manifest.json"]
    contract = validate_manifest(manifest)
    journal = parsed["migration-journal.json"]
    result = parsed.get("migration-result.json")
    if (journal.get("status") != "COPY_VERIFIED_NO_APPLICATION_CUTOVER"
            or journal.get("identity", {}).get("manifest") != manifest["sha256"]
            or (result is not None and result.get("manifest_sha256") != manifest["sha256"])
            or contract["references"] != parsed["references.json"]):
        raise RuntimeError("Migration evidence identity or completion mismatch")
    baseline = parsed.get("source-checkpoint.json")
    initial = parsed.get("target-checkpoint.json")
    later = parsed.get("target-post-qa-checkpoint.json")
    delta = parsed.get("target-qa-collection-delta.json")
    if baseline and initial:
        if any(initial.get(key) != value for key, value in baseline.items() if key.endswith('_hash')):
            raise RuntimeError("Initial migration archive baseline mismatch")
    if later is not None:
        if not baseline or not delta or delta.get('status') != 'FROZEN_COLLECTION_ROWS_PRESERVED_WITH_EXPLICIT_QA_ADDITIONS':
            raise RuntimeError("Post-QA checkpoint lacks its reviewed baseline delta")
        if (delta.get('source_collections_hash') != baseline['collections_history_hash']
                or delta.get('post_qa_collections_hash') != later['collections_history_hash']
                or any(later.get(key) != value for key, value in baseline.items()
                       if key.endswith('_hash') and key != 'collections_history_hash')):
            raise RuntimeError("Post-QA archive baseline changed")
    return payloads


def prune(root: Path) -> None:
    """Keep newest 7 days, 4 ISO weeks and 6 months, always within this root."""
    sets = (root / "sets").resolve()
    if sets.parent != root.resolve():
        raise RuntimeError("Backup sets must remain inside the selected root")
    runs: list[tuple[datetime, Path]] = []
    for item in sets.iterdir():
        if not item.is_dir() or item.resolve().parent != sets:
            continue
        manifest = item / "manifest.json"
        if manifest.exists():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                if data.get("success") is True:
                    runs.append((datetime.fromisoformat(data["completed_at"]), item))
            except (ValueError, KeyError, OSError):
                continue
    runs.sort(reverse=True)
    keep: set[Path] = set()
    daily: set[str] = set()
    weekly: set[str] = set()
    monthly: set[str] = set()
    for stamp, item in runs:
        week = stamp.isocalendar()
        keys = [
            (daily, stamp.strftime("%Y-%m-%d"), 7),
            (weekly, f"{week.year}-W{week.week:02d}", 4),
            (monthly, stamp.strftime("%Y-%m"), 6),
        ]
        for seen, key, limit in keys:
            if key not in seen and len(seen) < limit:
                seen.add(key)
                keep.add(item)
    for _, item in runs:
        resolved = item.resolve()
        if item not in keep and resolved.parent == sets and resolved != root.resolve():
            shutil.rmtree(resolved)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compose-file", type=Path, default=Path("docker-compose.yml"))
    parser.add_argument("--compose-override", type=Path, action="append", default=[])
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("BACKUP_ROOT", "backups")))
    parser.add_argument("--bucket", default=os.environ.get("MINIO_BUCKET_RAW", "raw-ingestions"))
    parser.add_argument("--database", default=None)
    parser.add_argument("--migration-evidence-dir", type=Path)
    parser.add_argument("--destination-policy", type=Path,
                        help="Fail-closed Windows independent BitLocker destination policy")
    parser.add_argument("--openshift-config", type=Path,
                        help="Explicit reviewed oc transport; no Docker fallback or cluster mutation")
    parser.add_argument("--prune", action="store_true")
    args = parser.parse_args()
    transport = compose
    adapter = None
    if args.openshift_config:
        if (args.env_file or args.compose_override or args.destination_policy
                or args.compose_file != Path("docker-compose.yml")):
            print("Backup not started: OpenShift and Compose inputs cannot be mixed", file=sys.stderr)
            return 2
        from openshift_backup import OpenShiftBackupTransport
        try:
            adapter = OpenShiftBackupTransport.from_file(args.openshift_config, engine_root=args.root)
            if (adapter.config.bucket != args.bucket
                    or args.database is not None and adapter.config.database != args.database):
                raise RuntimeError("OPENSHIFT_BACKUP_SCOPE_MISMATCH")
            transport = adapter.compose
        except (OSError, RuntimeError, ValueError, TypeError):
            print("Backup not started: reviewed OpenShift scope and destination were not verified", file=sys.stderr)
            return 2
    if args.compose_override:
        args.compose_file = [args.compose_file, *args.compose_override]
    # SQL, raw mirror, destination review and checksums must refer to the same
    # host root. The protected env file wins over ambient Compose variables.
    if args.env_file:
        from preflight import read_env
        try:
            configured = read_env(args.env_file).get("BACKUP_ROOT")
            if not configured or Path(configured).resolve() != args.root.resolve():
                raise ValueError("BACKUP_ROOT_MISMATCH")
        except (OSError, ValueError, TypeError):
            print("Backup not started: --root must match protected BACKUP_ROOT", file=sys.stderr)
            return 2
    if args.destination_policy:
        from backup_destination import verify
        try:
            verify(args.destination_policy, args.root)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            print("Backup not started: independent encrypted destination was not verified", file=sys.stderr)
            return 2
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if (root / "sets").exists() and (root / "sets").resolve().parent != root:
        raise RuntimeError("Backup sets must remain inside the selected root")
    try:
        operation_lock = acquire(root)
    except RuntimeError:
        print("Backup not started: operation already active", file=sys.stderr)
        return 1
    os.environ["BACKUP_ROOT"] = str(root)
    started = datetime.now(UTC)
    run_id = started.strftime("%Y%m%dT%H%M%SZ") + f"-{os.getpid()}"
    destination = root / "sets" / run_id
    destination.mkdir(parents=True)
    (destination / "raw").mkdir()
    dump = destination / "postgres.dump"
    status: dict[str, object] = {
        "started_at": started.isoformat(),
        "success": False,
        "database": args.database,
        "run_id": run_id,
    }
    try:
        if args.migration_evidence_dir:
            try:
                receipts = migration_evidence(args.migration_evidence_dir)
            except (ValueError, KeyError, TypeError, AttributeError):
                raise RuntimeError("Migration evidence schema invalid") from None
            evidence_root = destination / "migration-evidence"
            evidence_root.mkdir()
            for name, data in receipts.items():
                (evidence_root / name).write_bytes(data)
            status["migration_evidence_files"] = len(receipts)
        database_bytes = transport(
            args.compose_file,
            args.env_file,
            "exec",
            "-T",
            "postgres",
            "printenv",
            "POSTGRES_DB",
            stdout=subprocess.PIPE,
        )
        actual_database = database_bytes.decode().strip() if database_bytes else None
        if not actual_database or (args.database is not None and args.database != actual_database):
            raise RuntimeError(
                "Database name is unavailable or differs from the supplied expectation"
            )
        status["database"] = actual_database
        with dump.open("wb") as output:
            transport(
                args.compose_file,
                args.env_file,
                "exec",
                "-T",
                "postgres",
                "sh",
                "-c",
                'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc',
                stdout=output,
            )
        transport(
            args.compose_file,
            args.env_file,
            "--profile",
            "ops",
            "run",
            "--rm",
            "backup",
            "mirror",
            f"local/{args.bucket}",
            f"/backup/sets/{run_id}/raw",
        )
        files = [dump, *sorted((destination / "raw").rglob("*")),
                 *sorted((destination / "migration-evidence").glob("*.json"))]
        if any(path.is_symlink() or not path.resolve().is_relative_to(destination) for path in files):
            raise RuntimeError("Backup artifact escaped its set")
        checksums = {
            str(path.relative_to(destination)).replace("\\", "/"): sha256(path)
            for path in files
            if path.is_file()
        }
        status["size_bytes"] = sum(path.stat().st_size for path in files if path.is_file())
        if "postgres.dump" not in checksums or dump.stat().st_size == 0:
            raise RuntimeError("Backup lacks database artifact")
        if adapter is not None:
            adapter.verify_scope()
        completed = datetime.now(UTC)
        status.update(
            {
                "success": True,
                "completed_at": completed.isoformat(),
                "completed_timestamp": int(completed.timestamp()),
                "duration_seconds": (completed - started).total_seconds(),
                "database_artifact": "postgres.dump",
                "raw_prefix": "raw/",
                "raw_object_count": sum(key.startswith("raw/") for key in checksums),
                "source_bucket": args.bucket,
                "checksums": checksums,
            }
        )
        atomic_json(destination / "manifest.json", status)
        atomic_json(
            root / "runtime" / "backup-status.json",
            {key: value for key, value in status.items() if key != "checksums"},
        )
        atomic_json(root / "runtime" / "last-successful-backup.json",
                    {key: value for key, value in status.items() if key != "checksums"})
        if args.prune:
            prune(root)
        print(f"Backup complete: {destination}")
        return 0
    except (OSError, RuntimeError) as error:
        completed = datetime.now(UTC)
        status.update(
            {
                "completed_at": completed.isoformat(),
                "completed_timestamp": int(completed.timestamp()),
                "duration_seconds": (completed - started).total_seconds(),
                "error": type(error).__name__,
            }
        )
        atomic_json(destination / "manifest.json", status)
        atomic_json(root / "runtime" / "backup-status.json", status)
        print(f"Backup failed: {type(error).__name__}", file=sys.stderr)
        return 1
    finally:
        operation_lock.close()


if __name__ == "__main__":
    sys.exit(main())
