"""A new runtime build cannot silently substitute its archived source image."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import build_candidate


class BackendRuntimeBuildTests(unittest.TestCase):
    def test_unexpected_archived_source_rejected_before_artifacts_or_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "candidate"
            with patch.object(sys, "argv", ["build", "--output", str(output)]), \
                    patch.object(build_candidate, "image_id", return_value="sha256:" + "0" * 64), \
                    patch.object(build_candidate.subprocess, "run") as docker:
                with self.assertRaisesRegex(ValueError, "UNEXPECTED_SOURCE_IMAGE"):
                    build_candidate.main()
                self.assertFalse(output.exists())
                docker.assert_not_called()

    def test_changed_alias_cannot_start_a_build_or_claim_approval(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "candidate"
            with patch.object(sys, "argv", ["build", "--output", str(output)]), \
                    patch.object(build_candidate, "image_id", side_effect=[
                        build_candidate.SOURCE_ID, "sha256:" + "0" * 64,
                    ]), patch.object(build_candidate.subprocess, "run") as docker, \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(build_candidate.main(), 1)
            self.assertEqual(docker.call_count, 1)
            record = json.loads((output / "build-receipt.json").read_text())
            self.assertEqual(record["status"], "BUILD_INCOMPLETE")
            self.assertEqual(record["release_status"], "NOT_APPROVED")
            self.assertNotIn("image_id", record)

    def test_failed_build_receipt_never_exports_command_error_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "candidate"
            failure = subprocess.CalledProcessError(
                1, ["docker", "build"], stderr="sensitive diagnostic must remain private",
            )
            with patch.object(sys, "argv", ["build", "--output", str(output)]), \
                    patch.object(build_candidate, "image_id", return_value=build_candidate.SOURCE_ID), \
                    patch.object(build_candidate.subprocess, "run", side_effect=[None, failure]), \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(build_candidate.main(), 1)
            receipt = (output / "build-receipt.json").read_text()
            self.assertNotIn("sensitive diagnostic", receipt)
            record = json.loads(receipt)
            self.assertEqual(record["status"], "BUILD_INCOMPLETE")
            self.assertEqual(record["release_status"], "NOT_APPROVED")


if __name__ == "__main__":
    unittest.main()
