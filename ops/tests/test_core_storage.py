from datetime import UTC, datetime
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core_storage import measure, path_errors
from core_install_plan import configuration_hashes, readiness
from record_host_check import receipt
from security_audit import sha256


class CoreStorageTests(unittest.TestCase):
    def test_private_local_path_is_not_independent_recovery_and_growth_needs_distinct_days(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "sets" / "a").mkdir(parents=True)
            (root / "sets" / "a" / "manifest.json").write_text(json.dumps(
                {"success": True, "size_bytes": 100, "completed_at": "2026-10-27T01:00:00+00:00"}))
            measured = measure(root)
            self.assertGreater(measured["total_bytes"], 0)
            self.assertEqual(measured["retained_full_set_bytes_upper_bound"], 1700)
            self.assertIsNone(measured["observed_daily_growth_bytes"])
            self.assertEqual(measured["independence_status"], "NOT_VERIFIED")

    def test_backup_root_and_permissions_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            backup = root / "backups"
            backup.mkdir()
            with patch("core_storage.permission_status", return_value="BROAD_ACCESS"):
                self.assertIn("PERMISSIONS_BROAD_ACCESS", path_errors(backup, directory=True, root=root, mode="STAGING"))
            self.assertIn("PRODUCTION_BACKUP_INSIDE_CHECKOUT", path_errors(backup, directory=True, root=root, mode="PRODUCTION"))
            self.assertIn("BACKUP_ROOT_TOO_BROAD", path_errors(root, directory=True, root=root, mode="STAGING"))
            self.assertEqual(path_errors(Path("relative"), directory=True, root=root, mode="STAGING"), ["PATH_MUST_BE_ABSOLUTE"])

    def test_junction_or_symlink_content_never_scanned(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch("core_storage.redirected", return_value=True):
                with self.assertRaisesRegex(ValueError, "CONTENT_LINK"):
                    measure(root)

    def test_planner_rejects_stale_changed_preflight_and_has_no_apply(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder) / name for name in ("scope", "inventory", "environment")]
            for path in paths:
                path.write_bytes(b"fixture")
            identity = Path(folder) / 's3.json'
            identity.write_text('{"identities":[]}')
            paths[2].write_text('CORE_S3_CONFIG=' + str(identity) + '\n')
            p = {"executed": False, "status": "TECHNICAL_CONFIGURATION_VALID", "mode": "STAGING",
                 "generated_at": "2026-10-28T00:00:00+00:00", "configuration_file_hashes": configuration_hashes(),
                 "s3_identity_sha256": sha256(identity)}
            p.update(zip(("scope_sha256", "inventory_sha256", "environment_sha256"), map(sha256, paths)))
            self.assertEqual(readiness(p, *paths, "STAGING", now=datetime(2026, 10, 28, tzinfo=UTC)), [])
            identity.write_text('{"identities":[{"name":"changed-fixture"}]}')
            self.assertIn('PREFLIGHT_S3_IDENTITY_CHANGED_OR_NOT_BOUND',
                          readiness(p, *paths, 'STAGING', now=datetime(2026, 10, 28, tzinfo=UTC)))
            paths[2].write_bytes(b"changed secret")
            errors = readiness(p, *paths, "PRODUCTION", now=datetime(2026, 10, 30, tzinfo=UTC))
            self.assertIn("PREFLIGHT_INPUT_CHANGED_ENVIRONMENT_SHA256", errors)
            self.assertIn("PREFLIGHT_MODE_MISMATCH", errors)
            self.assertIn("PREFLIGHT_EXPIRED_OR_FUTURE", errors)
            with patch('core_install_plan.configuration_hashes', return_value={'changed': 'configuration'}):
                self.assertIn('PREFLIGHT_CONFIGURATION_CHANGED_OR_NOT_BOUND',
                              readiness(p, *paths, 'STAGING', now=datetime(2026, 10, 28, tzinfo=UTC)))

    def test_host_attestation_is_private_manifest_bound_and_never_host_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            backup = root / "backups"
            backup.mkdir()
            manifest, evidence = root / "manifest.json", backup / "proof.txt"
            manifest.write_bytes(b"manifest")
            evidence.write_bytes(b"actual command output, fixture only")
            with patch("record_host_check.permission_status", return_value="PRIVATE"):
                result = receipt("vpn", "PASS", "fixture-operator", "private.test", manifest, evidence, backup / "receipt.json", root)
            self.assertEqual(result["manifest_sha256"], sha256(manifest))
            self.assertEqual(result["release_status"], "NOT_APPROVED")
            self.assertEqual(result["target_status"], "TARGET_HOST_NOT_VERIFIED_BY_RECEIPT_TOOL")
            with self.assertRaisesRegex(ValueError, "MUST_STAY_PRIVATE"):
                receipt("vpn", "PASS", "fixture", "private.test", manifest, evidence, root / "public.json", root)


if __name__ == "__main__":
    unittest.main()
