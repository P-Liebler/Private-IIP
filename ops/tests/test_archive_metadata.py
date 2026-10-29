import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_archive_metadata import verify_metadata, from_image, metadata_paths


class StaticArchiveTests(unittest.TestCase):
    def fixture(self, version="1", symlink=False):
        core, support = "example==1\n", "support==2\n"
        artifact = {"contract": "internal-data-only-model-v1", "training_code": {"dependencies": core}, "configuration": {"rule": "fixture"}}
        body = json.dumps(artifact).encode()
        envelope = json.dumps({"contract": "PR5_LEGACY_VERIFICATION_V1", "artifact_base64": base64.b64encode(body).decode(), "artifact_sha256": hashlib.sha256(body).hexdigest(), "training_code": artifact["training_code"], "configuration": artifact["configuration"]}).encode()
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as tar:
            for name, data in {"app/requirements.lock": core, "app/requirements-assistant.lock": support, "usr/local/lib/python3.12/site-packages/example-1.dist-info/METADATA": "Name: example\nVersion: " + version + "\n", "usr/local/lib/python3.12/site-packages/support-2.dist-info/METADATA": "Name: support\nVersion: 2\n"}.items():
                member = tarfile.TarInfo(name)
                member.size = len(data.encode())
                if symlink and name == "app/requirements.lock": member.type = tarfile.SYMTYPE
                tar.addfile(member, io.BytesIO(data.encode()))
        stream.seek(0)
        return envelope, stream

    def test_static_bytes_and_pins_do_not_claim_historical_execution(self):
        envelope, stream = self.fixture()
        result = verify_metadata(envelope, stream, "fixture@sha256:" + "a" * 64)
        self.assertTrue(result["archive_bytes_verified"])
        self.assertEqual(result["checked_pins"], 2)
        self.assertEqual(result["historical_execution_reproducibility"], "NOT_EXECUTED_NOT_PROVEN")
        self.assertFalse(result["replaces_required_legacy_runtime_check"])
        self.assertFalse(result["security_approval"])

    def test_changed_installed_pin_is_rejected(self):
        envelope, stream = self.fixture(version="3")
        with self.assertRaisesRegex(ValueError, "ARCHIVE_INSTALLED_METADATA_MISMATCH"):
            verify_metadata(envelope, stream, "fixture@sha256:" + "a" * 64)

    def test_symlink_cannot_supply_archive_lock(self):
        envelope, stream = self.fixture(symlink=True)
        with self.assertRaisesRegex(ValueError, "ARCHIVE_METADATA_FILE_REJECTED"):
            verify_metadata(envelope, stream, "fixture@sha256:" + "a" * 64)

    def test_wrong_artifact_hash_is_rejected(self):
        envelope, stream = self.fixture()
        changed = json.loads(envelope); changed["artifact_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "ARCHIVE_BYTES_MISMATCH"):
            verify_metadata(json.dumps(changed).encode(), stream, "fixture@sha256:" + "a" * 64)

    def test_tag_only_source_fails_before_any_docker_call(self):
        with patch("verify_archive_metadata.subprocess.check_output") as run:
            with self.assertRaisesRegex(ValueError, "ARCHIVE_IMMUTABLE_IMAGE_REQUIRED"):
                from_image(b"{}", "old:latest", Path.cwd())
            run.assert_not_called()

    def sbom_fixture(self, directory, *, image=None, paths=None):
        image = image or "fixture@sha256:" + "a" * 64
        paths = paths if paths is not None else ["usr/local/lib/python3.12/site-packages/example-1.dist-info/METADATA"]
        sbom = directory / "legacy-verifier.cdx.json"
        sbom.write_text(json.dumps({"components": [{"properties": [{"name": "aquasecurity:trivy:FilePath", "value": name}]} for name in paths]}))
        row = {"component": "legacy-verifier", "image_reference": image, "image_id": image.split("@")[1],
               "scan_status": "SCANNED_EXACT_IMAGE", "sbom_sha256": hashlib.sha256(sbom.read_bytes()).hexdigest()}
        inventory = directory / "inventory.json"
        inventory.write_text(json.dumps({"images": [row]}))
        return inventory, sbom, row

    def test_original_sbom_bytes_are_bound_before_any_docker_call(self):
        with tempfile.TemporaryDirectory() as folder:
            inventory, sbom, _ = self.sbom_fixture(Path(folder))
            sbom.write_bytes(sbom.read_bytes() + b" ")
            with patch("verify_archive_metadata.subprocess.check_output") as docker:
                with self.assertRaisesRegex(ValueError, "ARCHIVE_SBOM_HASH_MISMATCH"):
                    from_image(b"{}", "fixture@sha256:" + "a" * 64, Path(folder), inventory)
                docker.assert_not_called()

    def test_sbom_image_digest_or_ambiguous_source_cannot_be_substituted(self):
        with tempfile.TemporaryDirectory() as folder:
            inventory, _, row = self.sbom_fixture(Path(folder))
            row["image_id"] = "sha256:" + "b" * 64
            inventory.write_text(json.dumps({"images": [row]}))
            with self.assertRaisesRegex(ValueError, "ARCHIVE_SBOM_IDENTITY_MISMATCH"):
                metadata_paths(inventory, "fixture@sha256:" + "a" * 64)
            row["image_id"] = "sha256:" + "a" * 64
            inventory.write_text(json.dumps({"images": [row, row]}))
            with self.assertRaisesRegex(ValueError, "ARCHIVE_SBOM_IDENTITY_MISMATCH"):
                metadata_paths(inventory, "fixture@sha256:" + "a" * 64)

    def test_missing_sbom_metadata_cannot_prove_installed_dependencies(self):
        with tempfile.TemporaryDirectory() as folder:
            inventory, _, _ = self.sbom_fixture(Path(folder), paths=[])
            with self.assertRaisesRegex(ValueError, "ARCHIVE_SBOM_METADATA_MISSING"):
                metadata_paths(inventory, "fixture@sha256:" + "a" * 64)

    def test_metadata_name_cannot_escape_adjacent_sbom_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            inventory, _, row = self.sbom_fixture(Path(folder))
            row["component"] = "../unselected"
            inventory.write_text(json.dumps({"images": [row]}))
            with self.assertRaises(ValueError):
                metadata_paths(inventory, "fixture@sha256:" + "a" * 64)

    def test_unselected_package_code_never_enters_static_result(self):
        envelope, stream = self.fixture()
        selected = {}
        with tarfile.open(fileobj=stream) as original:
            for member in original:
                selected[member.name] = original.extractfile(member).read()
        selected["usr/local/lib/python3.12/site-packages/example/__init__.py"] = b"raise RuntimeError('never execute archived code')"
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w") as tar:
            for name, body in selected.items():
                member = tarfile.TarInfo(name)
                member.size = len(body)
                tar.addfile(member, io.BytesIO(body))
        archive.seek(0)
        result = verify_metadata(envelope, archive, "fixture@sha256:" + "a" * 64)
        self.assertFalse(result["archived_package_code_imported"])
        self.assertTrue(all(not name.endswith(".py") for name in result["metadata_file_hashes"]))
