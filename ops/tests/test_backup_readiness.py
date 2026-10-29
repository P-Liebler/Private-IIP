import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backup import compose, main
from backup_destination import verify


class BackupReadinessTests(unittest.TestCase):
    def test_mismatched_backup_roots_fail_before_any_write_or_service_request(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            requested, configured = root / 'requested', root / 'configured'
            env = root / 'private.env'
            env.write_text('BACKUP_ROOT=' + str(configured) + '\n')
            with patch.object(sys, 'argv', ['backup.py', '--env-file', str(env), '--root', str(requested)]), patch('backup.compose') as compose_call, patch('backup_destination.verify') as destination:
                self.assertEqual(main(), 2)
            self.assertFalse(requested.exists())
            self.assertFalse(configured.exists())
            compose_call.assert_not_called()
            destination.assert_not_called()

    def test_core_overlay_uses_exact_env_file_and_never_ambient_target_or_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            base, overlay, env = [root / name for name in ("base.yml", "core.yml", "private.env")]
            base.write_text("name: ${COMPOSE_PROJECT_NAME}\n")
            overlay.write_text("identity: ${CORE_S3_CONFIG}\nbackup: ${BACKUP_ROOT}\noptional: ${OPTIONAL_UNSET}\n")
            env.write_text("COMPOSE_PROJECT_NAME=isolated-staging\nCORE_S3_CONFIG=private-file\nBACKUP_ROOT=expected-target\n")
            with patch.dict(os.environ, {"CORE_S3_CONFIG": "wrong-identity", "BACKUP_ROOT": "wrong-target", "OPTIONAL_UNSET": "injected"}), patch("backup.subprocess.run") as run:
                run.return_value = subprocess.CompletedProcess([], 0, stdout=b"ok")
                compose([base, overlay], env, "config")
            actual = run.call_args.kwargs["env"]
            self.assertEqual(actual["CORE_S3_CONFIG"], "private-file")
            self.assertEqual(actual["BACKUP_ROOT"], "expected-target")
            self.assertNotIn("OPTIONAL_UNSET", actual)
            self.assertEqual(run.call_args.args[0].count("-f"), 2)

    def test_missing_operator_destination_review_cannot_become_backup_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            policy = root / "destination.json"
            policy.write_text(json.dumps({"contract": "PRIVATE_IIP_WINDOWS_BITLOCKER_DESTINATION_V1", "operator_review": "NOT_APPROVED"}))
            with patch("backup_destination.permission_status", return_value="PRIVATE"):
                with self.assertRaisesRegex(ValueError, "POLICY_INVALID"):
                    verify(policy, root)

    def test_encryption_probe_failure_never_returns_success(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            policy = root / "destination.json"
            policy.write_text(json.dumps({"contract": "PRIVATE_IIP_WINDOWS_BITLOCKER_DESTINATION_V1", "root": str(root.resolve()),
                "volume_serial": "external", "operator_review": "APPROVED_FOR_BACKUP_DESTINATION", "operator": "fixture",
                "reviewed_at": "2026-10-28T00:00:00+00:00", "recovery_drill_receipt_sha256": "a" * 64}))
            with patch("backup_destination.permission_status", return_value="PRIVATE"), patch("backup_destination.os.name", "nt"), patch("backup_destination.subprocess.run", return_value=subprocess.CompletedProcess([], 1)):
                with self.assertRaisesRegex(ValueError, "ENCRYPTION_OR_IDENTITY_UNVERIFIED"):
                    verify(policy, root)

    def test_system_disk_and_unencrypted_volume_rejected_before_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            policy = root / "destination.json"
            policy.write_text(json.dumps({"contract": "PRIVATE_IIP_WINDOWS_BITLOCKER_DESTINATION_V1", "root": str(root.resolve()),
                "volume_serial": "external", "operator_review": "APPROVED_FOR_BACKUP_DESTINATION", "operator": "fixture",
                "reviewed_at": "2026-10-28T00:00:00+00:00", "recovery_drill_receipt_sha256": "a" * 64}))
            data = {"serial": "external", "systemSerial": "source", "driveType": 3, "diskNumber": 0, "systemDiskNumber": 0,
                    "protection": "On", "volume": "FullyEncrypted", "lock": "Unlocked"}
            with patch("backup_destination.permission_status", return_value="PRIVATE"), patch("backup_destination.os.name", "nt"), patch("backup_destination.subprocess.run", return_value=subprocess.CompletedProcess([], 0, stdout=json.dumps(data).encode())):
                with self.assertRaisesRegex(ValueError, "IDENTITY_OR_ENCRYPTION_MISMATCH"):
                    verify(policy, root)
                data["diskNumber"] = 1
                data["protection"] = "Off"
                with self.assertRaisesRegex(ValueError, "IDENTITY_OR_ENCRYPTION_MISMATCH"):
                    verify(policy, root)


if __name__ == "__main__":
    unittest.main()
