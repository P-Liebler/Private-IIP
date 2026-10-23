import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_legacy_model import verify


class LegacyIsolationTests(unittest.TestCase):
    def test_digest_and_input_limits_fail_before_docker(self):
        with patch("verify_legacy_model.subprocess.run") as run:
            for data, image in ((b"{}", "legacy:latest"), (b"x" * 30_000_001, "unused")):
                with self.assertRaises(ValueError):
                    verify(data, image)
            run.assert_not_called()

    def test_isolation_flags_and_typed_hash_result(self):
        digest = "a" * 64
        result = SimpleNamespace(returncode=0, stdout=json.dumps({"verified": True, "artifact_sha256": digest}).encode())
        with patch("verify_legacy_model.subprocess.run", return_value=result) as run:
            value = verify(json.dumps({"artifact_sha256": digest}).encode(), "private-iip/backend@sha256:" + "b" * 64)
        command = run.call_args.args[0]
        for flag, expected in (("--network", "none"), ("--cap-drop", "ALL"), ("--user", "10001:10001")):
            self.assertEqual(command[command.index(flag) + 1], expected)
        self.assertIn("--read-only", command)
        self.assertNotIn("--volume", command)
        self.assertNotIn("-v", command)
        self.assertTrue(value["verified"])

    def test_failed_process_or_different_artifact_cannot_be_verified(self):
        for result in (SimpleNamespace(returncode=1, stdout=b""), SimpleNamespace(returncode=0, stdout=b'{"verified":true,"artifact_sha256":"wrong"}')):
            with patch("verify_legacy_model.subprocess.run", return_value=result):
                with self.assertRaises(ValueError):
                    verify(b'{"artifact_sha256":"expected"}', "private-iip/backend@sha256:" + "b" * 64)
