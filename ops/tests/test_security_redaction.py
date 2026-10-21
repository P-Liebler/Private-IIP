"""Exercise the actual CI log-file entry point with synthetic credentials."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class RedactionTests(unittest.TestCase):
    def test_ci_log_extension_is_redacted_before_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "e2e.log"
            log.write_text("cookie: investment_session=fixture-token\nfixture-password\n21 passed\n")
            subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parents[1] / "redact_test_artifacts.py"), str(log)],
                check=True, env=os.environ | {"E2E_PASSWORD": "fixture-password"},
            )
            result = log.read_text()
            self.assertNotIn("fixture-token", result)
            self.assertNotIn("fixture-password", result)
            self.assertIn("21 passed", result)
