"""Read-only tests of the opt-in Argo CD startup candidate."""
from pathlib import Path
import subprocess
import sys
import unittest


REPO = Path(__file__).resolve().parents[2]


class GitOpsStartupCandidateTests(unittest.TestCase):
    def test_opt_in_overlay_contract(self):
        checker = REPO / "ops/openshift/overlays/gitops-demo/namespace-contract-test.py"
        result = subprocess.run(
            [sys.executable, str(checker)],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CLUSTER START NOT VERIFIED", result.stdout)


if __name__ == "__main__":
    unittest.main()
