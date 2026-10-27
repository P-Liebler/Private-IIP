"""Recovery/integrity tests with an in-memory S3 fixture, never a provider."""
from copy import deepcopy
import hashlib
from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import s3_migrate as migration


class StoreError(Exception):
    def __init__(self, code):
        self.response = {"Error": {"Code": code}}


class Body(BytesIO):
    def iter_chunks(self, chunk_size):
        while block := self.read(chunk_size):
            yield block


class Pages:
    def __init__(self, api, name):
        self.api, self.name = api, name

    def paginate(self, **args):
        if self.name == "list_parts":
            yield {"Parts": [{"PartNumber": n, "Size": len(b), "ETag": hashlib.md5(b).hexdigest()}
                             for n, b in self.api.uploads[args["UploadId"]][1].items()]}
            return
        rows = [(dict(Key=k, VersionId=v, IsLatest=i == len(versions) - 1), data.get("deleted", False))
                for k, versions in sorted(self.api.objects.items())
                for i, (v, data) in enumerate(versions)]
        # Deliberately split pages: inventories must consume the paginator.
        for row, deleted in rows:
            yield {"DeleteMarkers" if deleted else "Versions": [row]}


class Store:
    def __init__(self):
        self.objects = {}
        self.uploads = {}
        self.writes = 0

    def get_bucket_versioning(self, **_):
        return {"Status": "Enabled"}

    def get_object_lock_configuration(self, **_):
        raise StoreError("ObjectLockConfigurationNotFoundError")

    def get_paginator(self, name):
        return Pages(self, name)

    def data(self, args):
        for version, row in reversed(self.objects.get(args["Key"], [])):
            if args.get("VersionId", version) == version:
                return row
        raise StoreError("NoSuchKey")

    def head_object(self, **args):
        row = self.data(args)
        return {"ContentLength": len(row["Body"]), "Metadata": row.get("Metadata", {}),
                "ContentType": row.get("ContentType", "application/octet-stream"),
                "VersionId": args.get("VersionId", self.objects[args["Key"]][-1][0])}

    def get_object_tagging(self, **args):
        self.data(args)
        return {"TagSet": []}

    def get_object(self, **args):
        data = self.data(args)["Body"]
        if "Range" in args:
            start, end = map(int, args["Range"].removeprefix("bytes=").split("-"))
            data = data[start:end + 1]
        return {"Body": Body(data)}

    def put_object(self, **args):
        self.writes += 1
        versions = self.objects.setdefault(args["Key"], [])
        versions.append((str(len(versions) + 1), deepcopy(args)))
        return {}

    def create_multipart_upload(self, **args):
        self.writes += 1
        key = str(len(self.uploads) + 1)
        self.uploads[key] = (args, {})
        return {"UploadId": key}

    def upload_part(self, **args):
        self.writes += 1
        self.uploads[args["UploadId"]][1][args["PartNumber"]] = args["Body"]
        return {"ETag": hashlib.md5(args["Body"]).hexdigest()}

    def complete_multipart_upload(self, **args):
        header, parts = self.uploads[args["UploadId"]]
        self.put_object(**header, Body=b"".join(parts[n] for n in sorted(parts)))
        del self.uploads[args["UploadId"]]


class MigrationTests(unittest.TestCase):
    def test_brief_windows_sharing_lock_keeps_atomic_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "journal.json"
            migration.save(path, {"old": True})
            replace = Path.replace
            attempts = []
            def locked_then_released(source, target):
                attempts.append(1)
                if len(attempts) < 3:
                    raise PermissionError("synthetic sharing violation")
                return replace(source, target)
            with patch.object(Path, "replace", locked_then_released), patch("s3_migrate.time.sleep"):
                migration.save(path, {"new": True})
            self.assertEqual(len(attempts), 3)
            self.assertEqual(path.read_bytes(), migration.canonical({"new": True}) + b"\n")

    def test_permanent_checkpoint_lock_fails_without_losing_previous_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "journal.json"
            migration.save(path, {"old": True})
            original = path.read_bytes()
            with patch.object(Path, "replace", side_effect=PermissionError("synthetic permanent lock")), patch("s3_migrate.time.sleep"):
                with self.assertRaises(PermissionError):
                    migration.save(path, {"new": True})
            self.assertEqual(path.read_bytes(), original)

    def test_manifest_creation_never_overwrites_existing_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "manifest.json"
            migration.save(path, {"original": True}, new=True)
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                migration.save(path, {"replacement": True}, new=True)
            self.assertEqual(path.read_bytes(), original)

    def setUp(self):
        self.source, self.target = Store(), Store()
        self.source.put_object(Bucket="original", Key="document", Body=b"OLD ORIGINAL", Metadata={"evidence": "synthetic"})
        self.source.put_object(Bucket="original", Key="document", Body=b"CURRENT ORIGINAL", Metadata={"evidence": "synthetic"})
        self.source.put_object(Bucket="original", Key="model", Body=b"synthetic model" * 700000)
        self.source.writes = 0
        self.manifest = migration.inventory(self.source, ["original"], [
            {"bucket": "original", "key": "document", "sha256": hashlib.sha256(b"CURRENT ORIGINAL").hexdigest()}],
            "https://source")
        self.journal = {}
        self.saves = []

    def run_copy(self, **kwargs):
        migration.copy(self.manifest, self.source, self.target, {"original": "isolated"}, self.journal,
                       lambda: self.saves.append(deepcopy(self.journal)), **kwargs)

    def test_inventory_versions_and_read_only_reference_validation(self):
        self.assertEqual(len(self.manifest["payload"]["records"]), 3)
        self.assertEqual(self.source.writes, 0)
        with self.assertRaisesRegex(RuntimeError, "DB_REFERENCE_MISMATCH"):
            migration.check_references(self.manifest["payload"]["records"], [{"bucket": "original", "key": "missing"}])

    def test_source_client_disallows_every_write_operation(self):
        reader = migration.ReadOnlySource(self.source)
        for operation in ("put_object", "delete_object", "create_bucket", "upload_part"):
            with self.assertRaisesRegex(RuntimeError, "SOURCE_OPERATION_NOT_READ_ONLY"):
                getattr(reader, operation)
        self.assertEqual(reader.get_bucket_versioning(Bucket="original")["Status"], "Enabled")

    def test_interrupted_copy_new_process_journal_and_idempotency(self):
        with self.assertRaises(InterruptedError):
            self.run_copy(stop_after_parts=1)
        self.journal = deepcopy(self.saves[-1])  # Simulate reload after process loss.
        self.run_copy()
        writes = self.target.writes
        self.run_copy()
        self.assertEqual(self.target.writes, writes)
        self.assertEqual(self.source.writes, 0)
        self.assertEqual(self.journal["status"], "COPY_VERIFIED_NO_APPLICATION_CUTOVER")
        self.assertEqual(len(self.target.objects), 5)  # 3 archived versions + 2 live keys.

    def test_target_tamper_is_rejected_on_replay(self):
        self.run_copy()
        self.target.objects["document"][-1][1]["Body"] = b"corrupted"
        with self.assertRaisesRegex(RuntimeError, "TARGET_COLLISION_OR_HASH_MISMATCH"):
            self.run_copy()
        self.assertEqual(self.journal["status"], "COPY_FAILED")
        self.assertEqual(self.journal["failure"], "TARGET_COLLISION_OR_HASH_MISMATCH")
        self.assertIn("sha256", self.journal["differences"][0]["fields"])

    def test_changed_source_and_manifest_never_silently_replaced(self):
        self.manifest["payload"]["references"] = []
        with self.assertRaisesRegex(RuntimeError, "MANIFEST_HASH_MISMATCH"):
            self.run_copy()

    def test_source_new_version_rejected_before_copy(self):
        self.source.put_object(Bucket="original", Key="document", Body=b"later correction")
        with self.assertRaisesRegex(RuntimeError, "SOURCE_VERSION_SET_CHANGED"):
            self.run_copy()
        self.assertEqual(self.target.writes, 0)

    def test_source_new_version_during_copy_prevents_success_receipt(self):
        changed = False
        def persist():
            nonlocal changed
            if not changed and any(row.get("verified") for row in self.journal.get("objects", {}).values()):
                self.source.put_object(Bucket="original", Key="later", Body=b"new observation during copy")
                changed = True
        with self.assertRaisesRegex(RuntimeError, "SOURCE_VERSION_SET_CHANGED"):
            migration.copy(self.manifest, self.source, self.target, {"original": "isolated"}, self.journal, persist)
        self.assertEqual(self.journal["status"], "COPY_FAILED")

    def test_lost_completion_receipt_recovered_without_duplicate_version(self):
        self.run_copy()
        for state in self.journal["objects"].values():
            state.pop("verified", None)
        writes = self.target.writes
        self.run_copy()
        self.assertEqual(self.target.writes, writes)

    def test_unknown_target_object_and_same_bucket_are_rejected(self):
        self.target.put_object(Bucket="isolated", Key="foreign", Body=b"unrelated")
        with self.assertRaisesRegex(RuntimeError, "NEW_TARGET_MUST_BE_EMPTY"):
            self.run_copy()
        with self.assertRaisesRegex(RuntimeError, "SEPARATE_EXACT_TARGET_BUCKETS_REQUIRED"):
            migration.copy(self.manifest, self.source, self.target, {"original": "original"}, {}, lambda: None)

    def test_delete_marker_keeps_old_bytes_without_resurrecting_live_key(self):
        self.source.put_object(Bucket="original", Key="withdrawn", Body=b"old original")
        self.source.objects["withdrawn"].append(("2", {"deleted": True}))
        self.manifest = migration.inventory(self.source, ["original"], [], "https://source")
        self.run_copy()
        self.assertNotIn("withdrawn", self.target.objects)
        markers = [r for r in self.manifest["payload"]["records"] if r["deleted"]]
        self.assertEqual(len(markers), 1)
        self.assertTrue(markers[0]["latest"])


if __name__ == "__main__":
    unittest.main()
