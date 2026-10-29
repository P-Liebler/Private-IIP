"""Fail-closed Windows encrypted independent-volume guard for the existing backup engine."""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
import subprocess
import re

from core_storage import permission_status, redirected


def verify(policy_path: Path, root: Path) -> None:
    if redirected(policy_path) or permission_status(policy_path) != "PRIVATE":
        raise ValueError("BACKUP_DESTINATION_POLICY_PERMISSIONS_UNVERIFIED")
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    if (policy.get("contract") != "PRIVATE_IIP_WINDOWS_BITLOCKER_DESTINATION_V1"
            or policy.get("operator_review") != "APPROVED_FOR_BACKUP_DESTINATION"
            or not policy.get("operator") or not policy.get("reviewed_at")
            or not root.is_absolute() or not root.is_dir() or redirected(root)
            or str(root.resolve()).casefold() != str(policy.get("root", "")).casefold()
            or not policy.get("volume_serial")
            or not re.fullmatch(r"[0-9a-f]{64}", policy.get("recovery_drill_receipt_sha256", ""))
            or permission_status(root) != "PRIVATE"):
        raise ValueError("BACKUP_DESTINATION_POLICY_INVALID")
    reviewed = datetime.fromisoformat(policy["reviewed_at"])
    if reviewed.tzinfo is None or reviewed > datetime.now(UTC):
        raise ValueError("BACKUP_DESTINATION_REVIEW_TIME_INVALID")
    if os.name != "nt":
        raise ValueError("BACKUP_DESTINATION_PLATFORM_UNSUPPORTED")
    script = r"""$ErrorActionPreference='Stop'; $d=Get-Item -LiteralPath $env:IIP_BACKUP_GUARD_ROOT;
$drive=$d.PSDrive.Name + ':';
$disk=Get-CimInstance Win32_LogicalDisk -Filter ('DeviceID="'+$drive+'"');
$system=Get-CimInstance Win32_LogicalDisk -Filter ('DeviceID="'+$env:SystemDrive+'"');
$partition=Get-Partition -DriveLetter $d.PSDrive.Name;
$systemPartition=Get-Partition -DriveLetter ($env:SystemDrive.TrimEnd(':'));
$encrypted=Get-BitLockerVolume -MountPoint $drive;
[pscustomobject]@{serial=$disk.VolumeSerialNumber; systemSerial=$system.VolumeSerialNumber;
 diskNumber=$partition.DiskNumber; systemDiskNumber=$systemPartition.DiskNumber;
 protection=[string]$encrypted.ProtectionStatus; volume=[string]$encrypted.VolumeStatus;
 lock=[string]$encrypted.LockStatus; driveType=[int]$disk.DriveType} | ConvertTo-Json -Compress"""
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        env=os.environ | {"IIP_BACKUP_GUARD_ROOT": str(root)}, capture_output=True, check=False, timeout=30)
    if result.returncode:
        raise ValueError("BACKUP_DESTINATION_ENCRYPTION_OR_IDENTITY_UNVERIFIED")
    data = json.loads(result.stdout.decode("utf-8-sig"))
    if (data.get("serial") != policy["volume_serial"] or not data.get("systemSerial")
            or data["serial"] == data["systemSerial"] or data.get("driveType") not in (2, 3)
            or data.get("diskNumber") is None or data.get("systemDiskNumber") is None
            or data["diskNumber"] == data["systemDiskNumber"]
            or data.get("protection") != "On" or data.get("volume") != "FullyEncrypted"
            or data.get("lock") != "Unlocked"):
        raise ValueError("BACKUP_DESTINATION_IDENTITY_OR_ENCRYPTION_MISMATCH")
    # A separate physical device/offline-copy assessment and key-recovery drill remain operator evidence.
