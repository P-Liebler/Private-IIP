"""An archived release reference must reject altered content and escaping paths."""
from pathlib import Path
import sys
import tempfile
import unittest
import hashlib
import json
import subprocess
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_manifest import main as create_manifest, validate_artifacts, validate_manifest, source_snapshot, validate_scoped_restore
from deploy import reviewed_images
from security_audit import sha256
from preflight import read_env, validate_config


class ReleaseManifestTests(unittest.TestCase):
    def test_core_restore_must_use_every_scoped_runtime_and_recovery_image(self):
        expected = {name: "synthetic/" + name + "@sha256:" + "a" * 64
                    for name in ("api", "postgres", "minio", "backup", "legacy-verifier")}
        restore = {"image_contract": {name: expected[service] for name, service in
                   (("api", "api"), ("postgres", "postgres"), ("object_store", "minio"), ("s3_client", "backup"))},
                   "legacy_verification": {"verified": True, "image": expected["legacy-verifier"],
                                           "network": "none", "read_only": True}}
        validate_scoped_restore(expected, restore)
        for field in restore["image_contract"]:
            for replacement in (None, "synthetic/old@sha256:" + "b" * 64):
                changed = json.loads(json.dumps(restore))
                if replacement is None:
                    del changed["image_contract"][field]
                else:
                    changed["image_contract"][field] = replacement
                with self.subTest(field=field, replacement=replacement), self.assertRaisesRegex(
                    ValueError, "RELEASE_SCOPE_RESTORE_MISMATCH"
                ):
                    validate_scoped_restore(expected, changed)
        for field, replacement in (("verified", False), ("image", "synthetic/old@sha256:" + "b" * 64),
                                   ("network", "platform"), ("read_only", False)):
            changed = json.loads(json.dumps(restore))
            changed["legacy_verification"][field] = replacement
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError, "RELEASE_SCOPE_LEGACY_RESTORE_MISMATCH"
            ):
                validate_scoped_restore(expected, changed)
        del restore["legacy_verification"]
        with self.assertRaisesRegex(ValueError, "RELEASE_SCOPE_LEGACY_RESTORE_MISMATCH"):
            validate_scoped_restore(expected, restore)

    def test_generated_ci_environment_passes_production_configuration_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "ci.env"
            script = Path(__file__).resolve().parents[1] / "create_security_ci_env.py"
            subprocess.run([sys.executable, str(script), str(target)], check=True, capture_output=True)
            self.assertEqual(validate_config(read_env(target), "PRODUCTION"), [])
            self.assertTrue((Path(folder) / "security-backup").is_dir())

    def test_successful_restore_without_cleanup_cannot_create_rc(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            inventory = root / "inventory.json"
            restore = root / "restore.json"
            output = root / "rc.json"
            inventory.write_text('{"images": []}', encoding="utf-8")
            restore.write_text('{"success": true, "cleanup_success": false}', encoding="utf-8")
            arguments = ["release_manifest", "--id", "synthetic", "--inventory", str(inventory),
                         "--security-report", str(inventory), "--test-report", str(inventory),
                         "--restore-status", str(restore), "--migration-head", "0019_validation",
                         "--output", str(output)]
            with patch("sys.argv", arguments), self.assertRaisesRegex(ValueError, "RESTORE_NOT_VERIFIED"):
                create_manifest()
            self.assertFalse(output.exists())

    def test_operator_status_cannot_substitute_an_unaudited_service_digest(self):
        digest = "sha256:" + "a" * 64
        names = ("api", "worker", "scheduler", "ml-worker", "web", "postgres", "valkey", "minio", "backup", "caddy", "ca-export", "prometheus", "grafana", "mlflow", "ollama")
        components = ("backend", "web", "postgres", "valkey", "minio", "caddy", "prometheus", "grafana", "mlflow", "ollama")
        manifest = {"security_status": "SECURITY_REMEDIATED", "target_status": "TARGET_HOST_VERIFIED",
                    "release_status": "OPERATOR_APPROVED", "operator_approval_reference": "synthetic-review",
                    "service_image_digests": {name: "synthetic@" + digest for name in names},
                    "image_digests": {name: {"image_id": digest} for name in components}}
        manifest["service_image_digests"]["worker"] = "synthetic@sha256:" + "b" * 64
        with patch("deploy.validate_manifest"), self.assertRaisesRegex(ValueError, "RELEASE_SERVICE_DIGEST_MISMATCH"):
            reviewed_images(manifest, Path.cwd())

    def test_source_and_manifest_tampering_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.py"
            source.write_bytes(b"original")
            with patch("release_manifest.subprocess.check_output", return_value=b"source.py\0"):
                sources = source_snapshot(root)
            manifest = {"artifact_hashes": {}, "source_file_hashes": sources}
            manifest["content_sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            with patch("release_manifest.source_snapshot", return_value=sources):
                validate_manifest(manifest, root)
                with self.assertRaisesRegex(ValueError, "RELEASE_GATES_OPEN"):
                    reviewed_images(manifest, root)
            source.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "RELEASE_SOURCE_MISMATCH"):
                validate_manifest(manifest, root)
            manifest["release_status"] = "OPERATOR_APPROVED"
            with self.assertRaisesRegex(ValueError, "RELEASE_MANIFEST_MISMATCH"):
                validate_manifest(manifest, root)

    def test_tampered_or_outside_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            artifact = root / "safe.json"
            artifact.write_bytes(b"verified fixture")
            manifest = {"artifact_hashes": {"safe.json": sha256(artifact)}}
            validate_artifacts(manifest, root)
            artifact.write_bytes(b"changed fixture")
            with self.assertRaisesRegex(ValueError, "RELEASE_ARTIFACT_MISMATCH"):
                validate_artifacts(manifest, root)
            with self.assertRaisesRegex(ValueError, "RELEASE_ARTIFACT_MISMATCH"):
                validate_artifacts({"artifact_hashes": {"../outside": "synthetic"}}, root)
