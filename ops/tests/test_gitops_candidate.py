"""Read-only tests of the opt-in Argo CD startup candidate."""
from pathlib import Path
import subprocess
import shutil
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

    def test_render_if_kubectl_is_available(self):
        kubectl = shutil.which("kubectl")
        if kubectl is None:
            self.skipTest("kubectl unavailable: no Kustomize binary in runner")
        result = subprocess.run(
            [kubectl, "kustomize", "ops/openshift/overlays/gitops-demo"],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("name: postgres", result.stdout)
        self.assertIn("name: iip-wait-postgres-4f3b", result.stdout)
        self.assertIn("name: iip-caddy-retry-1", result.stdout)
        self.assertIn("name: iip-wait-caddy-4f3b", result.stdout)
        self.assertIn("name: privat-iip", result.stdout)


if __name__ == "__main__":
    unittest.main()
