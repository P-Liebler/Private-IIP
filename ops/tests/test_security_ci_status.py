import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from security_ci_status import classify


class SecurityCIStatusTests(unittest.TestCase):
    def test_download_failure_never_becomes_vulnerability_or_scan_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            steps = dict(scanner="success", database="failure")
            for state in ["VULNERABILITY_DB_UNAVAILABLE", "VULNERABILITY_DB_STALE"]:
                (root / "vulnerability-db.json").write_text(json.dumps({"status": state}))
                self.assertEqual(classify(root, steps)["status"], state)
            steps["scanner"] = "failure"
            self.assertEqual(classify(root, steps)["status"], "SCANNER_INSTALL_FAILED")

    def test_empty_missing_and_high_findings_do_not_report_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            steps = dict.fromkeys(["scanner", "database", "contracts", "dependencies", "images", "critical", "historical"], "success")
            (root / "vulnerability-db.json").write_text(json.dumps({"status": "DATABASE_READY"}))
            self.assertEqual(classify(root, steps)["status"], "SCAN_INCOMPLETE")
            (root / "pr4-images").mkdir()
            inventory = root / "pr4-images/inventory.json"
            def image(component, findings):
                return {"component": component, "image_id": "sha256:" + "a" * 64,
                        "sbom_sha256": "b" * 64, "scan_status": "SCANNED_EXACT_IMAGE", "findings": findings}
            images = [image("api", [{"severity": "HIGH"}]), image("web", [])]
            inventory.write_text(json.dumps({"images": images}))
            self.assertEqual(classify(root, steps)["status"], "IMAGE_VULNERABLE")
            images[0]["findings"] = []
            inventory.write_text(json.dumps({"images": images}))
            self.assertEqual(classify(root, steps)["status"], "SCAN_INCOMPLETE")
            (root / "pr4-core-sbom-validation.json").write_text(json.dumps({"valid": True, "records": [{"component": c, "valid": True} for c in ["api", "web"]]}))
            (root / "pr4-source").mkdir()
            (root / "pr4-source/source-security.json").write_text(json.dumps({"status": "NO_KNOWN_SECRET_FINDINGS", "finding_count": 0}))
            for name in ["core", "mlflow"]:
                (root / f"pr4-{name}-dependencies.json").write_text(json.dumps({"dependencies": [{"name": "synthetic", "version": "1", "vulns": []}]}))
            (root / "pr4-npm-dependencies.json").write_text(json.dumps({"metadata": {"vulnerabilities": {"total": 0}}}))
            self.assertEqual(classify(root, steps)["status"], "SECURITY_CHECK_PASSED")
            self.assertEqual(classify(root, steps)["release_status"], "NOT_APPROVED")
            steps["historical"] = "failure"
            current = classify(root, steps)
            self.assertEqual(current["status"], "SECURITY_CHECK_PASSED")
            self.assertEqual(current["historical_inventory_step"], "failure")
            (root / "pr4-core-dependencies.json").write_text(json.dumps({"dependencies": [{"vulns": [{"id": "SYNTHETIC"}]}]}))
            self.assertEqual(classify(root, steps)["status"], "DEPENDENCY_VULNERABLE")
