"""Read-only local backup path, permission and capacity checks; no recovery approval."""
from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import stat
import subprocess


def redirected(path: Path) -> bool:
    """Reject links and Windows junctions in every existing ancestor."""
    return any(part.is_symlink() or (part.exists() and bool(getattr(part.lstat(), "st_file_attributes", 0)
               & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
               ) for part in (path, *path.parents))


def permission_status(path: Path) -> str:
    if os.name != "nt":
        return "PRIVATE" if not path.stat().st_mode & 0o077 else "BROAD_ACCESS"
    # The path is data in the environment, never interpolated into PowerShell code.
    script = r"""$ErrorActionPreference='Stop'; $a=Get-Acl -LiteralPath $env:IIP_ACL_CHECK_PATH;
$rows=@($a.Access | ForEach-Object {
 [pscustomobject]@{sid=$_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value;
 allow=($_.AccessControlType -eq 'Allow'); rights=[int64]$_.FileSystemRights}});
ConvertTo-Json -InputObject $rows -Compress"""
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        env=os.environ | {"IIP_ACL_CHECK_PATH": str(path)}, capture_output=True, timeout=30, check=False)
    if result.returncode:
        return "UNVERIFIED"
    try:
        rows = json.loads(result.stdout.decode("utf-8-sig"))
        broad = {"S-1-1-0", "S-1-5-11", "S-1-5-32-545", "S-1-5-7"}
        if not isinstance(rows, list):
            return "UNVERIFIED"
        if any(row["allow"] and (row["sid"] in broad or row["sid"].endswith("-513"))
               and int(row["rights"]) for row in rows):
            return "BROAD_ACCESS"
        return "PRIVATE" if rows else "UNVERIFIED"
    except (ValueError, KeyError, TypeError, UnicodeError):
        return "UNVERIFIED"


def path_errors(path: Path, *, directory: bool, root: Path, mode: str) -> list[str]:
    if not path.is_absolute():
        return ["PATH_MUST_BE_ABSOLUTE"]
    if not path.exists() or (not path.is_dir() if directory else not path.is_file()):
        return ["DIRECTORY_NOT_AVAILABLE" if directory else "FILE_NOT_AVAILABLE"]
    if redirected(path):
        return ["LINK_OR_REPARSE_POINT_FORBIDDEN"]
    resolved = path.resolve()
    if directory and (resolved == Path(resolved.anchor) or root.resolve().is_relative_to(resolved)):
        return ["BACKUP_ROOT_TOO_BROAD"]
    if directory and mode == "PRODUCTION" and resolved.is_relative_to(root.resolve()):
        return ["PRODUCTION_BACKUP_INSIDE_CHECKOUT"]
    if directory and resolved.is_relative_to(root.resolve()) and not resolved.is_relative_to(root / "backups"):
        return ["BACKUP_OVERLAPS_SOURCE"]
    errors = []
    if not os.access(path, os.R_OK | (os.W_OK | os.X_OK if directory else 0)):
        errors.append("PATH_ACCESS_UNAVAILABLE")
    status = permission_status(path)
    if status != "PRIVATE":
        errors.append("PERMISSIONS_" + status)
    return errors


def measure(root: Path, *, max_files: int = 250_000) -> dict:
    """Count exact local bytes, skip no redirected content, and never prune."""
    count = total = 0
    if redirected(root):
        raise ValueError("BACKUP_CONTENT_LINK_FORBIDDEN")
    for folder, directories, names in os.walk(root, followlinks=False):
        if any((Path(folder) / name).is_symlink() or bool(getattr((Path(folder) / name).lstat(),
               "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
               for name in [*directories, *names]):
            raise ValueError("BACKUP_CONTENT_LINK_FORBIDDEN")
        for name in names:
            total += (Path(folder) / name).stat().st_size
            count += 1
            if count > max_files:
                raise ValueError("BACKUP_MEASUREMENT_LIMIT")
    observations = []
    incomplete_manifests = 0
    for path in sorted((root / "sets").glob("*/manifest.json")):
        if path.stat().st_size > 16 * 1024 * 1024:
            incomplete_manifests += 1
            continue
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            incomplete_manifests += 1
            continue
        if not isinstance(item, dict):
            incomplete_manifests += 1
            continue
        if item.get("success") is True:
            try:
                stamp = datetime.fromisoformat(item["completed_at"])
            except (ValueError, KeyError, TypeError):
                incomplete_manifests += 1
                continue
            if stamp.tzinfo is None or type(item.get("size_bytes")) is not int or item["size_bytes"] < 0:
                incomplete_manifests += 1
                continue
            observations.append((stamp.astimezone(UTC), item["size_bytes"]))
    observations.sort()
    daily = {}
    for stamp, size in observations:
        daily[stamp.date()] = max(size, daily.get(stamp.date(), 0))
    days = sorted(daily)
    daily_growth = max((max(0, (daily[b] - daily[a] + (b-a).days - 1) // (b-a).days)
                        for a, b in zip(days, days[1:])), default=None)
    peak = max((size for _, size in observations), default=None)
    # 7 daily + 4 weekly + 6 monthly full sets; overlaps reduce actual use.
    # No deduplication/compression saving is assumed. Real production growth is unknown.
    retained = None if peak is None else peak * 17
    reserve = None if retained is None else (retained * 12 + 9) // 10 + 5 * 1024**3
    return {"file_count": count, "total_bytes": total, "successful_sets_with_size_and_time": len(observations),
            "manifests_excluded_from_growth_estimate": incomplete_manifests,
            "peak_full_set_bytes": peak, "observed_daily_growth_bytes": daily_growth,
            "growth_status": "LOCAL_OBSERVATIONS_ONLY" if daily_growth is not None else "INSUFFICIENT_DISTINCT_DAYS",
            "retention_full_set_upper_bound": 17, "retained_full_set_bytes_upper_bound": retained,
            "minimum_capacity_with_20_percent_reserve_and_5_gib_bytes": reserve,
            "production_growth_status": "UNKNOWN_REQUIRES_REAL_ARCHIVE_MEASUREMENT",
            "independence_status": "NOT_VERIFIED", "encryption_status": "NOT_VERIFIED"}
