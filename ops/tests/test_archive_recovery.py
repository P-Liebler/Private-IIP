import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_archive_recovery import ARCHIVES, digest, verify


class ArchiveRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.artifact = {"contract": "internal-data-only-model-v1",
                         "training_code": {"dependencies": "example==1\n"},
                         "configuration": {"seed": 3}}
        self.body = json.dumps(self.artifact).encode()
        self.envelope = {"contract": "PR5_LEGACY_VERIFICATION_V1",
                         "artifact_base64": base64.b64encode(self.body).decode(),
                         "artifact_sha256": hashlib.sha256(self.body).hexdigest(),
                         "training_code": self.artifact["training_code"],
                         "configuration": self.artifact["configuration"]}
        self.static = {"contract": "PR9_STATIC_ARCHIVE_METADATA_V1",
                       "archive_bytes_verified": True, "historical_dependency_metadata_verified": True,
                       "historical_image_started": False, "archived_package_code_imported": False,
                       "artifact_sha256": self.envelope["artifact_sha256"],
                       "historical_image": "fixture@sha256:" + "a" * 64,
                       "historical_sbom_sha256": "b" * 64, "core_lock_sha256": "c" * 64,
                       "support_lock_sha256": "d" * 64, "metadata_manifest_sha256": "e" * 64,
                       "supporting_archive_contract": "NOT_RECORDED_IN_ARCHIVE", "checked_pins": 1}
        self.restore = {"success": True, "cleanup_success": True, "verified_backup_files": 1385,
                        "archive_contracts": {name: "f" * 64 for name in ARCHIVES},
                        "expected_value": "10180", "valuation_as_of": "2026-10-26T15:18:05Z",
                        "expected_current_issue": "STALE_PRICE"}
        self.restore["archive_contracts"]["model"] = self.envelope["artifact_sha256"]
        self.static_hash = self.write("original-static.json", self.static)
        self.restore_hash = self.write("original-restore.json", self.restore)
        self.write("restored.json", self.restore)
        self.manifest = {"restore_verification_reference": "original-restore.json",
                         "source_file_hashes": {"original-static.json": self.static_hash},
                         "artifact_hashes": {"original-restore.json": self.restore_hash}}
        self.manifest["content_sha256"] = digest(self.manifest)
        self.manifest_hash = self.write("original-manifest.json", self.manifest)

    def write(self, name, value):
        body = json.dumps(value).encode()
        (self.root / name).write_bytes(body)
        return hashlib.sha256(body).hexdigest()

    def run_verify(self, envelope=None, result=None, manifest_hash=None):
        with patch("verify_archive_recovery.from_image", return_value=result or self.static) as static:
            value = verify(json.dumps(envelope or self.envelope).encode(), self.root,
                           self.root / "original-manifest.json", manifest_hash or self.manifest_hash,
                           "original-static.json", self.root / "restored.json",
                           self.root / "inventory.json", self.root)
            return value, static

    def rejects_before_docker(self, expected, envelope=None, manifest_hash=None):
        with patch("verify_archive_recovery.from_image") as static:
            with self.assertRaisesRegex(ValueError, expected):
                verify(json.dumps(envelope or self.envelope).encode(), self.root,
                       self.root / "original-manifest.json", manifest_hash or self.manifest_hash,
                       "original-static.json", self.root / "restored.json",
                       self.root / "inventory.json", self.root)
            static.assert_not_called()

    def test_integrity_has_explicit_execution_and_approval_limits(self):
        value, call = self.run_verify()
        self.assertTrue(value["integrity_verified"])
        self.assertEqual(value["integrity_scope"], "SUPPLIED_ARTIFACT_BYTES_AND_HISTORICAL_IMAGE_METADATA_ONLY")
        self.assertEqual(value["original_archive_contracts"], self.restore["archive_contracts"])
        self.assertEqual(value["training_code_content_sha256"], digest(self.artifact["training_code"]))
        self.assertEqual(value["configuration_content_sha256"], digest(self.artifact["configuration"]))
        self.assertFalse(value["required_legacy_runtime_check_satisfied"])
        self.assertFalse(value["security_approval"])
        self.assertFalse(value["forecast_validation"])
        self.assertFalse(value["historical_image_started_by_this_verifier"])
        self.assertEqual(value["historical_numerical_reproducibility"], "NOT_EXECUTED_NOT_PROVEN")
        call.assert_called_once()

    def test_supplied_manifest_requires_independent_expected_hash(self):
        self.rejects_before_docker("INDEPENDENT_MANIFEST_HASH_REQUIRED", manifest_hash="latest")
        self.rejects_before_docker("ORIGINAL_MANIFEST_HASH_MISMATCH", manifest_hash="0" * 64)

    def test_frozen_manifest_internal_content_hash_is_checked(self):
        self.manifest["arbitrary"] = True
        altered = self.write("original-manifest.json", self.manifest)
        self.rejects_before_docker("ORIGINAL_MANIFEST_CONTENT_MISMATCH", manifest_hash=altered)

    def test_new_expected_hash_cannot_rescue_changed_original_receipt(self):
        self.static["artifact_sha256"] = "0" * 64
        self.write("original-static.json", self.static)
        self.rejects_before_docker("ORIGINAL_REFERENCE_MISMATCH")

    def test_rehashed_new_artifact_cannot_replace_original(self):
        changed = deepcopy(self.envelope)
        altered = deepcopy(self.artifact)
        altered["configuration"]["seed"] = 7
        body = json.dumps(altered).encode()
        changed["artifact_base64"] = base64.b64encode(body).decode()
        changed["artifact_sha256"] = hashlib.sha256(body).hexdigest()
        changed["configuration"] = altered["configuration"]
        self.rejects_before_docker("ORIGINAL_ARTIFACT_MISMATCH", envelope=changed)

    def test_envelope_training_and_configuration_cannot_disagree_with_pinned_artifact(self):
        for name in ("training_code", "configuration"):
            changed = deepcopy(self.envelope)
            changed[name] = {"changed": True}
            self.rejects_before_docker("ORIGINAL_MODEL_METADATA_MISMATCH", envelope=changed)

    def test_every_original_history_hash_is_required(self):
        for name in ARCHIVES:
            with self.subTest(name=name):
                changed = deepcopy(self.restore)
                changed["archive_contracts"][name] = "0" * 64
                self.write("restored.json", changed)
                self.rejects_before_docker("REPORTED_HISTORY_MISMATCH")

    def test_failed_cleanup_or_lower_file_count_is_not_a_verified_restore(self):
        for name, value in (("success", False), ("cleanup_success", False), ("verified_backup_files", 1)):
            changed = deepcopy(self.restore)
            changed[name] = value
            self.write("restored.json", changed)
            self.rejects_before_docker("REPORTED_HISTORY_MISMATCH")

    def test_golden_cutoff_and_stale_current_gate_are_preserved(self):
        for name in ("expected_value", "valuation_as_of", "expected_current_issue"):
            changed = deepcopy(self.restore)
            changed[name] = "changed"
            self.write("restored.json", changed)
            self.rejects_before_docker("REPORTED_HISTORY_MISMATCH")

    def test_changed_installed_metadata_or_sbom_is_rejected(self):
        for name in ("metadata_manifest_sha256", "historical_sbom_sha256", "core_lock_sha256",
                     "support_lock_sha256", "historical_image", "checked_pins"):
            changed = deepcopy(self.static)
            changed[name] = "changed"
            with self.assertRaisesRegex(ValueError, "ORIGINAL_METADATA_MISMATCH"):
                self.run_verify(result=changed)

    def test_old_image_start_or_package_import_cannot_be_relabelled_static(self):
        for name in ("historical_image_started", "archived_package_code_imported"):
            changed = deepcopy(self.static)
            changed[name] = True
            with self.assertRaisesRegex(ValueError, "ORIGINAL_METADATA_MISMATCH"):
                self.run_verify(result=changed)

    def test_separate_old_runtime_receipt_is_reported_without_new_execution_claim(self):
        changed = deepcopy(self.restore)
        changed["legacy_verification"] = {"verified": True}
        self.write("restored.json", changed)
        value, _ = self.run_verify()
        self.assertTrue(value["supplied_receipt_reports_separate_legacy_execution"])
        self.assertFalse(value["historical_image_started_by_this_verifier"])

    def test_original_receipt_bytecopy_is_only_a_recheck_never_a_fresh_restore(self):
        (self.root / "restored.json").write_bytes((self.root / "original-restore.json").read_bytes())
        value, _ = self.run_verify()
        self.assertEqual(value["supplied_receipt_comparison"], "ORIGINAL_RECEIPT_RECHECK_ONLY")
        self.assertEqual(value["reported_verified_backup_files"], 1385)
        self.assertNotIn("verified_backup_files", value)
        self.assertFalse(value["supplied_receipt_claims_independently_verified"])
        for name in ("fresh_restore_executed_by_this_verifier", "fresh_restore_proven_by_this_verifier",
                     "restored_database_accessed_by_this_verifier", "restored_object_store_accessed_by_this_verifier",
                     "restored_archive_bytes_checked_by_this_verifier"):
            self.assertFalse(value[name])

    def test_changed_receipt_cannot_establish_a_fresh_restore_or_independent_byte_checks(self):
        changed = deepcopy(self.restore)
        changed["completed_at"] = "2099-01-01T00:00:00Z"
        self.write("restored.json", changed)
        value, _ = self.run_verify()
        self.assertEqual(value["supplied_receipt_comparison"],
                         "DIFFERENT_RECEIPT_MATCHES_ORIGINAL_REPORTED_CONTRACTS_ONLY")
        self.assertFalse(value["fresh_restore_proven_by_this_verifier"])
        self.assertFalse(value["restored_archive_bytes_checked_by_this_verifier"])


if __name__ == "__main__":
    unittest.main()
