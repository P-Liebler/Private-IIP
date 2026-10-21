"""Audit contract tests use synthetic image metadata only; no network or Docker."""
from datetime import UTC, datetime, timedelta
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
import subprocess
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from security_audit import archive_config_digest, findings, scan_image, validate_scan, validate_sbom, write_new
from registry_image_audit import verify_binding


class SecurityAuditTests(unittest.TestCase):
    def test_registry_fallback_rejects_same_index_on_another_platform(self):
        digest = "sha256:" + "a" * 64
        prior = {"scan_status": "SCANNED_EXACT_IMAGE", "image_id": digest, "config_digest": digest,
                 "archive_sha256": "b" * 64, "architecture": "amd64", "os": "linux"}
        local = {"Id": digest, "Architecture": "amd64", "Os": "linux"}
        verify_binding(prior, local, "synthetic@" + digest)
        local["Architecture"] = "arm64"
        with self.assertRaisesRegex(ValueError, "PRIOR_EXACT_EXPORT_BINDING_REQUIRED"):
            verify_binding(prior, local, "synthetic@" + digest)

    def test_unavailable_image_is_recorded_incomplete_without_aborting_inventory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch("security_audit.run", side_effect=subprocess.CalledProcessError(1, "docker", stderr="unavailable")):
                record = scan_image(root / "scanner", root / "cache", root, "missing", "synthetic:missing")
            self.assertEqual(record["scan_status"], "SCAN_INCOMPLETE")
            self.assertNotIn("findings", record)
            self.assertTrue((root / "missing.record.json").is_file())

    def test_publishing_preserves_exact_sbom_bytes_and_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source"
            source.mkdir()
            digest = "sha256:" + "a" * 64
            (source / "test.record.json").write_text(json.dumps({"component": "test", "image_id": digest, "config_digest": digest, "image_reference": "synthetic:1", "scan_status": "SCANNED_EXACT_IMAGE"}), encoding="utf-8")
            (source / "test.trivy.json").write_text(json.dumps({"SchemaVersion": 2, "ArtifactType": "container_image", "Metadata": {"ImageID": digest}, "Results": [{}]}), encoding="utf-8")
            original = b'{ "bomFormat": "CycloneDX", "specVersion": "1.7", "components": [{"name":"synthetic", "type":"library"}] }\n'
            (source / "test.cdx.json").write_bytes(original)
            metadata = root / "database.json"
            metadata.write_text("{}")
            destination = root / "published"
            subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "publish_security_audit.py"), str(source), str(destination), "--database-metadata", str(metadata), "--required", "test"], check=True, capture_output=True)
            published = (destination / "test.cdx.json").read_bytes()
            inventory = json.loads((destination / "inventory.json").read_text(encoding="utf-8"))
            self.assertEqual(published, original)
            self.assertEqual(inventory["images"][0]["sbom_sha256"], hashlib.sha256(published).hexdigest())

    def test_digest_mismatch_and_unsupported_scan_rejected(self):
        value = {"SchemaVersion": 2, "ArtifactType": "container_image", "Metadata": {"ImageID": "sha256:old"}, "Results": [{}]}
        with self.assertRaisesRegex(ValueError, "DIGEST_MISMATCH"):
            validate_scan(value, "sha256:new")
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_IMAGE_SCAN"):
            validate_scan(value | {"ArtifactType": "filesystem"}, "sha256:old")
        with self.assertRaisesRegex(ValueError, "EMPTY_SCAN"):
            validate_scan(value | {"Results": []}, "sha256:old")

    def test_sbom_requires_actual_package_inventory(self):
        value = {"bomFormat": "CycloneDX", "specVersion": "1.6", "components": [{"name": "synthetic", "type": "library"}]}
        validate_sbom(value)
        for invalid in ({}, value | {"components": []}, value | {"components": [{}]}):
            with self.assertRaises(ValueError):
                validate_sbom(invalid)

    def test_manifest_digest_and_config_digest_have_explicit_binding(self):
        config = b'{"synthetic":true}'
        digest = hashlib.sha256(config).hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "image.tar"
            with tarfile.open(path, "w") as archive:
                for name, value in (("manifest.json", json.dumps([{"Config": "blobs/sha256/" + digest}]).encode()), ("blobs/sha256/" + digest, config)):
                    member = tarfile.TarInfo(name)
                    member.size = len(value)
                    archive.addfile(member, io.BytesIO(value))
            self.assertEqual(archive_config_digest(path), "sha256:" + digest)

    def test_immutable_evidence_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "rc.json"
            write_new(target, {"commit": "first"})
            before = target.read_bytes()
            with self.assertRaises(FileExistsError):
                write_new(target, {"commit": "second"})
            self.assertEqual(before, target.read_bytes())

    def test_missing_fix_does_not_create_exception_or_false_pass(self):
        value = {"Results": [{"Vulnerabilities": [{"PkgName": "synthetic", "VulnerabilityID": "CVE-TEST", "Severity": "CRITICAL"}]}]}
        record = findings(value, "test", "sha256:test", "test:1")[0]
        self.assertEqual(record["status"], "FIX_UNAVAILABLE")
        self.assertEqual(record["reachability"], "REQUIRES_OPERATOR_REVIEW")
        self.assertIsNone(record["reviewer"])
