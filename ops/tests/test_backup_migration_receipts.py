"""Migration replay metadata must survive backup without copying private configs."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backup import migration_evidence
import backup
from s3_migrate import digest


def fixture(folder):
    payload = {"contract": "PR7_S3_MANIFEST_V2", "records": [], "references": []}
    checksum = digest(payload)
    documents = {
        "migration-manifest.json": {"payload": payload, "sha256": checksum},
        "migration-journal.json": {"identity": {"manifest": checksum}, "status": "COPY_VERIFIED_NO_APPLICATION_CUTOVER"},
        "references.json": [],
    }
    for name, value in documents.items():
        (folder / name).write_text(json.dumps(value) + "\n", encoding="utf-8")
    return documents


class BackupMigrationReceiptTests(unittest.TestCase):
    def test_post_qa_checkpoint_cannot_rewrite_protected_archive_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            fixture(folder)
            baseline = {'dataset_hash': 'a' * 64, 'collections_history_hash': 'b' * 64}
            later = {**baseline, 'collections_history_hash': 'c' * 64}
            delta = {'status': 'FROZEN_COLLECTION_ROWS_PRESERVED_WITH_EXPLICIT_QA_ADDITIONS',
                     'source_collections_hash': 'b' * 64, 'post_qa_collections_hash': 'c' * 64}
            for name, value in [('source-checkpoint', baseline), ('target-checkpoint', baseline),
                                ('target-post-qa-checkpoint', later), ('target-qa-collection-delta', delta)]:
                (folder / (name + '.json')).write_text(json.dumps(value))
            self.assertEqual(len(migration_evidence(folder)), 7)
            later['dataset_hash'] = 'd' * 64
            (folder / 'target-post-qa-checkpoint.json').write_text(json.dumps(later))
            with self.assertRaisesRegex(RuntimeError, 'archive baseline changed'):
                migration_evidence(folder)

    def test_only_explicit_exact_receipts_are_archived(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            documents = fixture(folder)
            (folder / "private.env").write_text("SYNTHETIC EXCLUDED CONFIG")
            result = migration_evidence(folder)
            self.assertEqual(set(result), set(documents))
            self.assertEqual(result["migration-manifest.json"], (folder / "migration-manifest.json").read_bytes())

    def test_tampering_or_incomplete_copy_never_becomes_backup_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            documents = fixture(folder)
            documents["migration-manifest.json"]["sha256"] = "0" * 64
            (folder / "migration-manifest.json").write_text(json.dumps(documents["migration-manifest.json"]))
            with self.assertRaisesRegex(RuntimeError, "MANIFEST_HASH_MISMATCH"):
                migration_evidence(folder)
            documents = fixture(folder)
            documents["migration-journal.json"]["status"] = "COPY_INTERRUPTED"
            (folder / "migration-journal.json").write_text(json.dumps(documents["migration-journal.json"]))
            with self.assertRaisesRegex(RuntimeError, "completion mismatch"):
                migration_evidence(folder)
            (folder / 'migration-manifest.json').write_text('{ malformed SYNTHETIC PRIVATE CONFIG')
            target = folder / 'backup'
            with patch.object(sys, 'argv', ['backup.py', '--root', str(target), '--migration-evidence-dir', str(folder)]), patch.object(backup, 'compose') as docker:
                self.assertEqual(backup.main(), 1)
            docker.assert_not_called()
            status = json.loads((target / 'runtime/backup-status.json').read_text())
            self.assertFalse(status['success'])
            self.assertNotIn('SYNTHETIC PRIVATE CONFIG', json.dumps(status))


if __name__ == "__main__":
    unittest.main()
