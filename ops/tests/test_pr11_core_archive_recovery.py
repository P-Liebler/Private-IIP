"""A real Core restore must retain archive integrity without executing old code."""
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import os
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_manifest import validate_scoped_restore
from release_scope import CORE_REQUIRED_V2, active_services, validate_scope
from restore_verify import main as restore_main, readback_user, verify_raw_readback
from verify_archive_metadata import LOCKS, verify_metadata
from verify_archive_recovery import (ARCHIVES, CORE_RECOVERY, core_anchors, core_expectations,
                                     current_expectations, digest, metadata_bundle, verify_core_archive)


def sha(body):
    return hashlib.sha256(body).hexdigest()


class CoreArchiveRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.image = "synthetic/archive@sha256:" + "a" * 64
        self.files = {}
        for index in range(66):
            self.files[f"usr/local/lib/python3.12/site-packages/pkg{index}-1.0.dist-info/METADATA"] = (
                f"Name: pkg{index}\nVersion: 1.0\n\nSynthetic metadata\n".encode())
        self.files[LOCKS[0]] = "".join(f"pkg{index}==1.0\n" for index in range(33)).encode()
        self.files[LOCKS[1]] = "".join(f"pkg{index}==1.0\n" for index in range(33, 66)).encode()
        artifact = {"contract": "internal-data-only-model-v1", "training_code": {
            "dependencies": self.files[LOCKS[0]].decode(), "supporting_dependencies": self.files[LOCKS[1]].decode()},
            "configuration": {"synthetic": True}}
        body = json.dumps(artifact).encode()
        self.envelope = json.dumps({"contract": "PR5_LEGACY_VERIFICATION_V1",
            "artifact_base64": base64.b64encode(body).decode(), "artifact_sha256": sha(body),
            "training_code": artifact["training_code"], "configuration": artifact["configuration"]}).encode()
        self.bundle = self.root / "metadata.tar"
        self.bundle_hash = self.write_tar()
        self.static = verify_metadata(self.envelope, io.BytesIO(self.bundle.read_bytes()), self.image)
        sbom = {"components": [{"properties": [{"name": "aquasecurity:trivy:FilePath", "value": name}]} for name in self.files if name not in LOCKS]}
        self.static["historical_sbom_sha256"] = self.write("legacy-verifier.cdx.json", sbom)
        self.inventory = {"images": [{"component": "legacy-verifier", "image_reference": self.image,
            "image_id": self.image.split("@")[1], "scan_status": "SCANNED_EXACT_IMAGE",
            "sbom_sha256": self.static["historical_sbom_sha256"]}]}
        self.restore = {"success": True, "cleanup_success": True, "verified_backup_files": 1387,
            "recorded_at": "2026-10-29T00:00:00+00:00", "started_at": "2026-10-29T01:00:00+00:00",
            "raw_object_count": 1378, "backup_manifest_sha256": "f" * 64,
            "backup_run_id": "synthetic-backup", "archive_contracts": {name: "b" * 64 for name in ARCHIVES},
            "expected_value": "10180", "valuation_as_of": "2026-10-26T15:18:05.987683+00:00",
            "expected_current_issue": "STALE_PRICE"}
        self.restore["archive_contracts"]["model"] = sha(body)
        self.manifest = {"restore_verification_reference": "original-restore.json", "artifact_hashes": {
            "original-restore.json": self.write("original-restore.json", self.restore)}, "source_file_hashes": {
            "original-static.json": self.write("original-static.json", self.static),
            "inventory.json": self.write("inventory.json", self.inventory)}}
        self.manifest["content_sha256"] = digest(self.manifest)
        self.manifest_hash = self.write("original-manifest.json", self.manifest)

    def write(self, name, value):
        body = json.dumps(value).encode()
        (self.root / name).write_bytes(body)
        return sha(body)

    def write_tar(self, files=None, extra=None):
        with tarfile.open(self.bundle, "w", format=tarfile.USTAR_FORMAT) as archive:
            for name, body in (files or self.files).items():
                member = tarfile.TarInfo(name)
                member.size = len(body)
                archive.addfile(member, io.BytesIO(body))
            if extra:
                archive.addfile(extra[0], io.BytesIO(extra[1]))
        return sha(self.bundle.read_bytes())

    def anchors(self, expected=None):
        return core_anchors(self.root, self.root / "original-manifest.json", expected or self.manifest_hash,
                            "original-static.json", self.root / "inventory.json")

    def scope(self):
        return {"contract": "PRIVATE_CORE_SCOPE_V2", "services": {
            **{name: {"enabled": True, "role": "recovery" if name == "backup" else "runtime",
                "image": self.image, "reason": "synthetic contract"} for name in CORE_REQUIRED_V2},
            "legacy-verifier": {"enabled": False, "role": "archive", "image": self.image,
                                "reason": "Immutable optional archive, not Core execution"}},
            "archive_recovery": {"contract": CORE_RECOVERY, "original_manifest_reference": "original-manifest.json",
                "current_expectations_contract": "PRIVATE_CORE_RESTORE_EXPECTATIONS_V1",
                "original_manifest_sha256": self.manifest_hash, "original_static_reference": "original-static.json",
                "historical_inventory_reference": "inventory.json", "metadata_bundle_sha256": self.bundle_hash,
                "checked_pins": 66, "historical_runtime_execution": "NOT_EXECUTED_NOT_PROVEN",
                "optional_dynamic_legacy_status": "SECURITY_BLOCKED"}}

    def proof(self):
        baseline, _, anchors = self.anchors()
        return verify_core_archive(self.envelope, baseline, anchors, self.bundle, self.bundle_hash)

    def test_original_66_pins_verified_without_docker_or_historical_import(self):
        with patch("subprocess.run") as run, patch("subprocess.check_output") as output:
            proof = self.proof()
        self.assertEqual(proof["checked_pins"], 66)
        self.assertFalse(proof["historical_image_started"])
        self.assertEqual(proof["optional_dynamic_legacy_status"], "SECURITY_BLOCKED")
        self.assertNotIn("fresh_restore_proven_by_this_verifier", proof)
        self.assertFalse(proof["security_approval"])
        run.assert_not_called()
        output.assert_not_called()

    def test_independently_retained_manifest_hash_is_required(self):
        for value in ("not-a-hash", "0" * 64):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "MANIFEST_HASH"):
                self.anchors(value)

    def test_rehashed_static_inventory_or_original_restore_cannot_replace_anchor(self):
        for name in ("original-static.json", "inventory.json", "original-restore.json"):
            path = self.root / name
            previous = path.read_bytes()
            path.write_bytes(previous + b" ")
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "ORIGINAL_REFERENCE_MISMATCH"):
                self.anchors()
            path.write_bytes(previous)

    def test_original_sbom_bytes_remain_required(self):
        self.write("legacy-verifier.cdx.json", {"components": []})
        with self.assertRaisesRegex(ValueError, "SBOM_HASH_MISMATCH"):
            self.anchors()

    def test_mutated_model_cannot_supply_its_own_expected_hash(self):
        changed = json.loads(self.envelope)
        artifact = json.loads(base64.b64decode(changed["artifact_base64"]))
        artifact["configuration"] = {"changed": True}
        body = json.dumps(artifact).encode()
        changed.update(artifact_base64=base64.b64encode(body).decode(), artifact_sha256=sha(body),
                       configuration=artifact["configuration"])
        baseline, _, anchors = self.anchors()
        with self.assertRaisesRegex(ValueError, "CORE_ORIGINAL_METADATA_MISMATCH"):
            verify_core_archive(json.dumps(changed).encode(), baseline, anchors, self.bundle, self.bundle_hash)

    def test_all_history_golden_and_backup_expectations_bound_before_restore(self):
        core_expectations(self.restore, self.restore)
        for name in ARCHIVES:
            changed = copy.deepcopy(self.restore)
            changed["archive_contracts"][name] = "0" * 64
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "EXPECTATION_MISMATCH"):
                core_expectations(self.restore, changed)

    def test_new_pinned_backup_and_append_only_history_checkpoint_are_allowed(self):
        current = copy.deepcopy(self.restore) | {
            "contract": "PRIVATE_CORE_RESTORE_EXPECTATIONS_V1", "recorded_at": "2026-10-29T00:00:00+00:00",
            "original_manifest_sha256": self.manifest_hash, "backup_run_id": "legitimate-next-backup",
            "verified_backup_files": 1390, "raw_object_count": 1381, "backup_manifest_sha256": "1" * 64}
        current["archive_contracts"]["predictions"] = "2" * 64
        current["archive_contracts"]["collections"] = "3" * 64
        expected_hash = self.write("current-expectations.json", current)
        loaded = current_expectations(self.root / "current-expectations.json", expected_hash,
                                      self.manifest_hash, self.static["artifact_sha256"])
        core_expectations(loaded, current)
        self.assertNotEqual(loaded["archive_contracts"], self.restore["archive_contracts"])
        self.assertEqual(loaded["archive_contracts"]["model"], self.static["artifact_sha256"])

    def test_changed_unpinned_checkpoint_and_new_model_hash_are_rejected(self):
        current = copy.deepcopy(self.restore) | {
            "contract": "PRIVATE_CORE_RESTORE_EXPECTATIONS_V1", "recorded_at": "2026-10-29T00:00:00+00:00",
            "original_manifest_sha256": self.manifest_hash}
        expected_hash = self.write("current-expectations.json", current)
        current["archive_contracts"]["collections"] = "0" * 64
        self.write("current-expectations.json", current)
        with self.assertRaisesRegex(ValueError, "CURRENT_EXPECTATIONS_HASH_MISMATCH"):
            current_expectations(self.root / "current-expectations.json", expected_hash,
                                 self.manifest_hash, self.static["artifact_sha256"])
        current["archive_contracts"]["model"] = "0" * 64
        new_hash = self.write("current-expectations.json", current)
        with self.assertRaisesRegex(ValueError, "CURRENT_EXPECTATIONS_CONTRACT_REJECTED"):
            current_expectations(self.root / "current-expectations.json", new_hash,
                                 self.manifest_hash, self.static["artifact_sha256"])
        for name in ("expected_value", "valuation_as_of", "expected_current_issue", "verified_backup_files", "backup_run_id"):
            changed = copy.deepcopy(self.restore)
            changed[name] = "changed"
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "EXPECTATION_MISMATCH"):
                core_expectations(self.restore, changed)

    def test_metadata_tar_hash_is_not_derived_from_new_input(self):
        with self.assertRaisesRegex(ValueError, "BUNDLE_HASH_MISMATCH"):
            metadata_bundle(self.bundle, "0" * 64, self.static)

    def test_traversal_symlink_hardlink_duplicate_and_unallowlisted_tar_members_rejected(self):
        for name, kind in (("../escape", tarfile.REGTYPE), ("/absolute", tarfile.REGTYPE),
                           (LOCKS[0], tarfile.SYMTYPE), (LOCKS[0], tarfile.LNKTYPE),
                           (LOCKS[0], tarfile.REGTYPE), ("app/executable.py", tarfile.REGTYPE)):
            member = tarfile.TarInfo(name)
            member.type = kind
            member.linkname = "../escape" if kind != tarfile.REGTYPE else ""
            member.size = 0
            value = self.write_tar(extra=(member, b""))
            with self.subTest(name=name, kind=kind), self.assertRaisesRegex(ValueError, "BUNDLE_MEMBER_REJECTED"):
                metadata_bundle(self.bundle, value, self.static)

    def test_missing_pin_metadata_and_mutated_original_lock_rejected_even_with_new_tar_hash(self):
        changed = dict(self.files)
        del changed[next(name for name in changed if name not in LOCKS)]
        value = self.write_tar(changed)
        with self.assertRaisesRegex(ValueError, "BUNDLE_FILES_MISSING"):
            metadata_bundle(self.bundle, value, self.static)
        changed = dict(self.files)
        changed[LOCKS[0]] += b"unknown==0\n"
        value = self.write_tar(changed)
        with self.assertRaisesRegex(ValueError, "BUNDLE_FILE_MISMATCH"):
            metadata_bundle(self.bundle, value, self.static)

    def test_oversized_metadata_member_rejected_before_read(self):
        with tarfile.open(self.bundle, "w") as archive:
            member = tarfile.TarInfo(LOCKS[0])
            member.size = 2_000_001
            archive.fileobj.write(member.tobuf())
        with self.assertRaisesRegex(ValueError, "BUNDLE_MEMBER_REJECTED"):
            metadata_bundle(self.bundle, sha(self.bundle.read_bytes()), self.static)

    def test_readback_hashes_actual_restored_object_bytes_and_rejects_extra_missing_or_corrupt(self):
        directory = self.root / "readback"
        directory.mkdir()
        (directory / "one").write_bytes(b"original raw bytes")
        checksums = {"postgres.dump": "c" * 64, "raw/one": sha(b"original raw bytes")}
        self.assertEqual(verify_raw_readback(directory, checksums)["objects"], 1)
        for change in ("corrupt", "extra", "missing"):
            (directory / "one").write_bytes(b"changed" if change == "corrupt" else b"original raw bytes")
            if change == "extra":
                (directory / "extra").write_bytes(b"extra")
            if change == "missing":
                (directory / "one").unlink()
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "RAW_BYTES_MISMATCH"):
                verify_raw_readback(directory, checksums)
            (directory / "extra").unlink(missing_ok=True)

    def test_linux_readback_uses_nonroot_directory_owner_without_permission_widening(self):
        with patch("restore_verify.os.getuid", return_value=1000, create=True), \
                patch("restore_verify.os.getgid", return_value=1000, create=True):
            self.assertEqual(readback_user(), "1000:1000")
        with patch("restore_verify.os.getuid", return_value=0, create=True), \
                patch("restore_verify.os.getgid", return_value=0, create=True), \
                self.assertRaisesRegex(ValueError, "REQUIRES_NONROOT_OPERATOR"):
            readback_user()

    def test_scope_v2_requires_12_services_and_explicit_original_recovery_anchors(self):
        scope = self.scope()
        self.assertEqual(len(active_services(scope)), 12)
        for name in CORE_REQUIRED_V2:
            changed = copy.deepcopy(scope)
            del changed["services"][name]
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_scope(changed)
        for name in scope["archive_recovery"]:
            changed = copy.deepcopy(scope)
            del changed["archive_recovery"][name]
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_scope(changed)
        scope["services"]["legacy-verifier"]["enabled"] = True
        with self.assertRaisesRegex(ValueError, "LEGACY_SERVICE_CANNOT_BE_ACTIVE"):
            validate_scope(scope)

    def test_release_gate_requires_actual_replay_readback_and_static_integrity(self):
        scope = self.scope()
        expected = {name: row["image"] for name, row in active_services(scope).items()}
        restored = copy.deepcopy(self.restore) | {"recovery_contract": CORE_RECOVERY,
            "restore_expectations_contract": "PRIVATE_CORE_RESTORE_EXPECTATIONS_V1",
            "restore_expectations_sha256": "1" * 64,
            "image_contract": {"api": self.image, "postgres": self.image, "object_store": self.image, "s3_client": self.image},
            "archive_integrity": self.proof(), "restored_raw_verification": {"objects": 1378, "content_sha256": "d" * 64},
            "restored_contract_verification": {"database_restored": True, "object_store_restored": True,
                "database_and_object_store_checks_executed": True, "all_archive_contracts_verified": sorted(ARCHIVES),
                "model_envelope_origin": "THIS_RESTORED_DATABASE_AND_OBJECT_STORE",
                "fixture_verifier_output_sha256": "e" * 64, "supplied_restore_receipt_used_as_fresh_evidence": False}}
        validate_scoped_restore(expected, restored, scope, self.restore)
        for name in ("archive_integrity", "restored_raw_verification", "restored_contract_verification", "recovery_contract"):
            changed = copy.deepcopy(restored)
            del changed[name]
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "CORE_ARCHIVE_RESTORE_MISMATCH"):
                validate_scoped_restore(expected, changed, scope, self.restore)
        for group, name, value in (("archive_integrity", "checked_pins", 65),
                ("archive_integrity", "metadata_bundle_sha256", "0" * 64),
                ("archive_integrity", "original_manifest_sha256", "0" * 64),
                ("archive_integrity", "historical_image_started", True),
                ("restored_contract_verification", "database_and_object_store_checks_executed", False),
                ("restored_contract_verification", "supplied_restore_receipt_used_as_fresh_evidence", True),
                ("restored_contract_verification", "all_archive_contracts_verified", []),
                ("restored_raw_verification", "objects", 0)):
            changed = copy.deepcopy(restored)
            changed[group][name] = value
            with self.subTest(group=group, name=name), self.assertRaisesRegex(ValueError, "CORE_ARCHIVE_RESTORE_MISMATCH"):
                validate_scoped_restore(expected, changed, scope, self.restore)
        with self.assertRaisesRegex(ValueError, "CURRENT_EXPECTATIONS_REQUIRED"):
            validate_scoped_restore(expected, restored, scope)
        changed = copy.deepcopy(self.restore)
        changed["recorded_at"] = "2026-10-29T02:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "EXPECTATIONS_NOT_PRE_RESTORE"):
            validate_scoped_restore(expected, restored, scope, changed)

    def producer(self, fail=None):
        backup_root = self.root / "backup"
        backup = backup_root / "sets" / "synthetic-backup"
        backup.joinpath("raw").mkdir(parents=True)
        backup.joinpath("postgres.dump").write_bytes(b"synthetic dump")
        backup.joinpath("raw", "one").write_bytes(b"original raw")
        checksums = {"postgres.dump": sha(b"synthetic dump"), "raw/one": sha(b"original raw")}
        backup.joinpath("manifest.json").write_text(json.dumps({"success": True, "checksums": checksums}))
        original = copy.deepcopy(self.restore)
        original["verified_backup_files"] = 2
        original["raw_object_count"] = 1
        original["backup_manifest_sha256"] = sha(backup.joinpath("manifest.json").read_bytes())
        original["contract"] = "PRIVATE_CORE_RESTORE_EXPECTATIONS_V1"
        original["original_manifest_sha256"] = self.manifest_hash
        original["recorded_at"] = "2026-10-29T00:00:00+00:00"
        expectation_hash = self.write("current-expectations.json", original)
        baseline, _, anchors = self.anchors()
        values = ["--dataset-id", "synthetic-dataset", "--expected-dataset-hash", original["archive_contracts"]["dataset"],
            "--model-id", "synthetic-model", "--expected-artifact-hash", original["archive_contracts"]["model"]]
        for key, flag in (("predictions", "prediction"), ("risk", "risk"), ("recommendations", "recommendation"),
                          ("intelligence", "intelligence"), ("document_removals", "document-removal"),
                          ("ui_requests", "ui-request"), ("collections", "collections"), ("validation", "validation")):
            values.extend(["--" + flag + "-history-hash", original["archive_contracts"][key]])
        arguments = ["restore_verify", str(backup), "--root", str(backup_root), "--username", "synthetic",
            "--portfolio-id", "synthetic-portfolio", "--raw-id", "synthetic-raw", "--expected-value", "10180",
            "--valuation-as-of", original["valuation_as_of"], "--expect-current-issue", "STALE_PRICE",
            "--recovery-contract", CORE_RECOVERY, "--original-manifest", str(self.root / "original-manifest.json"),
            "--archive-anchor-root", str(self.root),
            "--expected-original-manifest-sha256", self.manifest_hash, "--original-static-reference", "original-static.json",
            "--historical-inventory", str(self.root / "inventory.json"), "--archive-metadata-bundle", str(self.bundle),
            "--expected-metadata-bundle-sha256", self.bundle_hash, *values]
        arguments += ["--expected-restore-contract", str(self.root / "current-expectations.json"),
                      "--expected-restore-contract-sha256", expectation_hash]
        for flag in ("api", "postgres", "object-store", "client"):
            arguments.extend(["--" + flag + "-image", self.image])
        commands = []

        def command(project, file, environment, *args):
            commands.append(args)
            if "psql" in args:
                return b'{"server_version":"synthetic"}\n'
            if "mirror" in args and args[-1] == "/readback":
                mount = args[args.index("--volume") + 1]
                target = Path(mount.removesuffix(":/readback:rw"))
                target.joinpath("one").write_bytes(b"original raw")
            if "scripts.verify_restored_fixture" in args:
                if fail == "fixture":
                    raise RuntimeError("SYNTHETIC_FIXTURE_HASH_MISMATCH")
                return b"synthetic fixture verification output"
            if "scripts.export_legacy_model" in args:
                if fail == "export":
                    raise ValueError("SYNTHETIC_EXPORT_REJECTED")
                return self.envelope
            return b""

        with patch("sys.argv", arguments), patch.dict(os.environ, {"RESTORE_TEST_PASSWORD": "synthetic-only"}), \
                patch("restore_verify.acquire", return_value=Mock()), \
                patch("verify_archive_recovery.core_anchors", return_value=(baseline, original, anchors)), \
                patch("restore_verify.command", side_effect=command), \
                patch("verify_legacy_model.verify") as legacy:
            code = restore_main()
            legacy.assert_not_called()
        result = json.loads((backup_root / "runtime" / "restore-status.json").read_text())
        return code, result, commands

    def test_producer_requires_actual_ordered_restore_replay_export_and_cleanup(self):
        code, result, commands = self.producer()
        self.assertEqual(code, 0)
        self.assertTrue(result["success"])
        self.assertTrue(result["cleanup_success"])
        self.assertNotIn("legacy_verification", result)
        upload = next(i for i, args in enumerate(commands) if "mirror" in args and args[-1] == "restored/raw-ingestions")
        readback = next(i for i, args in enumerate(commands) if "mirror" in args and args[-1] == "/readback")
        self.assertIn("--volume", commands[readback])
        self.assertTrue(commands[readback][commands[readback].index("--volume") + 1].endswith(":/readback:rw"))
        self.assertFalse(any(":/backup:rw" in part for args in commands for part in args))
        replay = next(i for i, args in enumerate(commands) if "scripts.verify_restored_fixture" in args)
        export = next(i for i, args in enumerate(commands) if "scripts.export_legacy_model" in args)
        self.assertLess(upload, readback)
        self.assertLess(readback, replay)
        self.assertLess(replay, export)
        self.assertEqual(commands[-1], ("down", "-v", "--remove-orphans"))
        self.assertEqual(result["restored_contract_verification"]["fixture_verifier_output_sha256"],
                         sha(b"synthetic fixture verification output"))

    def test_failed_real_fixture_or_export_cannot_be_reported_as_success(self):
        for failure in ("fixture", "export"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as folder:
                previous = self.root
                self.root = Path(folder)
                # The mocked producer anchor is already independently checked
                # by this test's original fixture. Keep those references local.
                for name in ("original-manifest.json", "original-static.json", "original-restore.json",
                             "inventory.json", "legacy-verifier.cdx.json"):
                    (self.root / name).write_bytes((previous / name).read_bytes())
                code, result, commands = self.producer(failure)
                self.root = previous
                self.assertEqual(code, 1)
                self.assertFalse(result["success"])
                self.assertTrue(result["cleanup_success"])
                self.assertNotIn("archive_integrity", result)
                self.assertEqual(commands[-1], ("down", "-v", "--remove-orphans"))


if __name__ == "__main__":
    unittest.main()
