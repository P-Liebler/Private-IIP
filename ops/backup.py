"""Back up PostgreSQL and immutable MinIO raw objects to a configured host directory.

Run from the repository root with BACKUP_ROOT set to an independent mounted disk.
The script never copies application secrets into an artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compose(file: Path, env_file: Path | None, *args: str, stdout=None) -> bytes | None:
    command = ["docker", "compose", "-f", str(file)]
    if env_file:
        command += ["--env-file", str(env_file)]
    command += list(args)
    result = subprocess.run(command, stdout=stdout, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RuntimeError(f"Docker Compose command failed ({result.returncode})")
    return result.stdout


def atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def prune(root: Path) -> None:
    """Keep newest 7 days, 4 ISO weeks and 6 months, always within this root."""
    sets = (root / "sets").resolve()
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
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("BACKUP_ROOT", "backups")))
    parser.add_argument("--bucket", default=os.environ.get("MINIO_BUCKET_RAW", "raw-ingestions"))
    parser.add_argument("--database", default=None)
    parser.add_argument("--prune", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
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
        database_bytes = compose(
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
            compose(
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
        compose(
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
        files = [dump, *sorted((destination / "raw").rglob("*"))]
        checksums = {
            str(path.relative_to(destination)).replace("\\", "/"): sha256(path)
            for path in files
            if path.is_file()
        }
        if "postgres.dump" not in checksums or dump.stat().st_size == 0:
            raise RuntimeError("Backup lacks database artifact")
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


if __name__ == "__main__":
    sys.exit(main())
