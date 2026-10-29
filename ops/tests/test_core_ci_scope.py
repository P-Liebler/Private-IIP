"""Offline evidence fixtures; never build/pull images or contact a provider."""
import copy
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ci_full_image_audit
from release_scope import CORE_REQUIRED
from security_audit import sha256
from security_ci_status import classify


CONFIG_FILES = ("docker-compose.prod.yml", "ops/docker-compose.core.yml", "ops/caddy/Core.Caddyfile",
                "ops/prometheus/prometheus.yml", "ops/prometheus/alerts.yml")


class CoreCIScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.steps = dict.fromkeys(("scanner", "database", "contracts", "dependencies", "images", "critical", "historical", "full"), "success")
        self.scope = {"contract": "PRIVATE_CORE_SCOPE_V1", "services": {
            name: {"enabled": True, "role": "recovery" if name in {"backup", "legacy-verifier", "storage-init"} else "runtime",
                   "reason": "offline evidence fixture only", "image": "fixture/" + name + "@sha256:" + hashlib.sha256(name.encode()).hexdigest()}
            for name in sorted(CORE_REQUIRED)}}
        self.scope["services"]["ollama"] = {"enabled": False, "role": "optional", "reason": "fixture disabled",
                                                "image": "fixture/ollama@sha256:" + "f" * 64}
        self.write("pr4-release-scope.json", self.scope)
        images = [{"component": name, "image_reference": row["image"], "image_id": row["image"].split("@")[1],
                   "scan_status": "SCANNED_EXACT_IMAGE", "sbom_sha256": "b" * 64, "findings": []}
                  for name, row in self.scope["services"].items() if row["enabled"]]
        self.inventory = {"images": images, "database": {"UpdatedAt": (datetime.now(UTC) - timedelta(hours=1)).isoformat()}}
        self.write("pr4-images/inventory.json", {"images": [row for row in images if row["component"] in {"api", "web"}]})
        self.write("pr4-full-images/inventory.json", self.inventory)
        self.proof = {"status": "EXACT_CONFIG_AND_IMAGE_SCOPE_VERIFIED",
            "scope_sha256": sha256(self.root / "pr4-release-scope.json"),
            "configuration_sha256": "c" * 64,
            "selected_config_files_sha256": {name: sha256(Path(name)) for name in CONFIG_FILES},
            "verified_service_images": {row["component"]: row["image_reference"] for row in images},
            "release_status": "NOT_APPROVED"}
        self.write("pr4-full-images/release-scope-audit.json", self.proof)
        self.write("vulnerability-db.json", {"status": "DATABASE_READY"})
        self.write("pr4-core-sbom-validation.json", {"valid": True, "records": [{"component": name, "valid": True} for name in ["api", "web"]]})
        self.write("pr4-full-sbom-validation.json", {"valid": True, "records": [{"component": row["component"], "valid": True} for row in images]})
        self.write("pr4-source/source-security.json", {"status": "NO_KNOWN_SECRET_FINDINGS", "finding_count": 0})
        for name in ("core", "mlflow"):
            self.write(f"pr4-{name}-dependencies.json", {"dependencies": [{"name": "fixture", "version": "1", "vulns": []}]})
        self.write("pr4-npm-dependencies.json", {"metadata": {"vulnerabilities": {"total": 0}}})

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def full(self):
        return classify(self.root, self.steps, full=True)

    def test_api_web_success_explicitly_cannot_prove_full_release(self):
        state = classify(self.root, self.steps)
        self.assertEqual(state["status"], "SECURITY_CHECK_PASSED")
        self.assertEqual(state["core_release_scope_status"], "NOT_REQUESTED_NOT_VERIFIED")
        self.assertEqual(state["release_status"], "NOT_APPROVED")
        (self.root / "pr4-full-images/inventory.json").unlink()
        self.assertEqual(self.full()["status"], "SCAN_INCOMPLETE")

    def test_exact_full_automated_scope_never_grants_operator_release(self):
        self.steps["historical"] = "failure"
        state = self.full()
        self.assertEqual(state["status"], "SECURITY_CHECK_PASSED")
        self.assertEqual(state["core_release_scope_status"], "SECURITY_REVIEW_REQUIRED")
        self.assertEqual(state["historical_inventory_step"], "failure")
        self.assertEqual(state["release_status"], "NOT_APPROVED")

    def test_recovery_omission_or_digest_substitution_is_incomplete(self):
        original = copy.deepcopy(self.inventory)
        for name in ("backup", "legacy-verifier"):
            with self.subTest(name=name, mutation="omitted"):
                self.inventory = copy.deepcopy(original)
                self.inventory["images"] = [row for row in self.inventory["images"] if row["component"] != name]
                self.write("pr4-full-images/inventory.json", self.inventory)
                self.assertEqual(self.full()["status"], "SCAN_INCOMPLETE")
            with self.subTest(name=name, mutation="substituted"):
                self.inventory = copy.deepcopy(original)
                row = next(row for row in self.inventory["images"] if row["component"] == name)
                row["image_id"] = "sha256:" + "0" * 64
                self.write("pr4-full-images/inventory.json", self.inventory)
                self.assertEqual(self.full()["status"], "SCAN_INCOMPLETE")

    def test_missing_or_stale_scope_proof_is_incomplete(self):
        path = self.root / "pr4-full-images/release-scope-audit.json"
        path.unlink()
        self.assertEqual(self.full()["status"], "SCAN_INCOMPLETE")
        for change in ({"scope_sha256": "0" * 64}, {"verified_service_images": {}},
                       {"configuration_sha256": ""}, {"configuration_sha256": "z" * 64}):
            with self.subTest(change=change):
                self.write("pr4-full-images/release-scope-audit.json", {**self.proof, **change})
                self.assertEqual(self.full()["status"], "SCAN_INCOMPLETE")

    def test_missing_changed_or_extra_configuration_source_proof_is_incomplete(self):
        for change in ({}, {**self.proof["selected_config_files_sha256"], CONFIG_FILES[0]: "0" * 64},
                       {**self.proof["selected_config_files_sha256"], "ops/prometheus/alerts.yml": "0" * 64},
                       {**self.proof["selected_config_files_sha256"], "unselected.yml": "0" * 64}):
            with self.subTest(change=change):
                self.write("pr4-full-images/release-scope-audit.json", {**self.proof, "selected_config_files_sha256": change})
                self.assertEqual(self.full()["status"], "SCAN_INCOMPLETE")

    def test_recovery_high_or_critical_cannot_hide_behind_clean_web_api(self):
        for severity in ("HIGH", "CRITICAL"):
            row = next(row for row in self.inventory["images"] if row["component"] == "legacy-verifier")
            row["findings"] = [{"severity": severity, "cve": "FIXTURE_ONLY"}]
            self.write("pr4-full-images/inventory.json", self.inventory)
            state = self.full()
            self.assertEqual(state["status"], "IMAGE_VULNERABLE")
            self.assertEqual(state["core_release_scope_status"], "SECURITY_BLOCKED")

    def test_raw_database_metadata_normalization_keeps_age_and_future_checks(self):
        self.assertEqual(self.full()["status"], "SECURITY_CHECK_PASSED")
        for age in (timedelta(hours=49), timedelta(hours=-1)):
            self.inventory["database"]["UpdatedAt"] = (datetime.now(UTC) - age).isoformat()
            self.write("pr4-full-images/inventory.json", self.inventory)
            self.assertEqual(self.full()["status"], "SCAN_INCOMPLETE")

    def test_unscanned_or_enabled_optional_image_never_inherits_approval(self):
        self.inventory["images"].append({**self.inventory["images"][0], "component": "ollama"})
        self.write("pr4-full-images/inventory.json", self.inventory)
        self.assertEqual(self.full()["status"], "SCAN_INCOMPLETE")
        self.inventory["images"].pop()
        self.write("pr4-full-images/inventory.json", self.inventory)
        self.scope["services"]["ollama"]["enabled"] = True
        self.write("pr4-release-scope.json", self.scope)
        self.assertEqual(self.full()["status"], "SCAN_INCOMPLETE")

    def test_exact_audit_never_builds_pulls_or_publishes_resolved_secrets(self):
        config = {"services": {name: {"image": row["image"], "environment": {"FIXTURE_SECRET": "do-not-publish"}}
                               for name, row in self.scope["services"].items() if row["enabled"]}}
        calls, writes = [], []

        def output(command, **kwargs):
            calls.append(command)
            if command[-3:] == ["config", "--format", "json"]:
                return json.dumps(config).encode()
            if command[:3] == ["docker", "image", "inspect"]:
                return command[3].split("@")[1].encode()
            raise AssertionError("Unexpected command")

        def run(command, **kwargs):
            calls.append(command)
            self.assertEqual(command[1], "ops/security_audit.py")
            return subprocess.CompletedProcess(command, 0)

        args = ["ci_full_image_audit.py", "--env-file", "fixture.env", "--scanner", "fixture-trivy",
                "--scanner-sha256", "0" * 64, "--cache", str(self.root), "--output", str(self.root / "audit-output"),
                "--release-scope", str(self.root / "pr4-release-scope.json")]
        with patch.object(sys, "argv", args), patch.object(ci_full_image_audit, "read_env", return_value={}), \
                patch.object(ci_full_image_audit, "compose_environment", return_value={}), \
                patch.object(ci_full_image_audit.subprocess, "check_output", side_effect=output), \
                patch.object(ci_full_image_audit.subprocess, "run", side_effect=run), \
                patch.object(ci_full_image_audit, "write_new", side_effect=lambda path, value: writes.append((path, value))):
            self.assertEqual(ci_full_image_audit.main(), 0)
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][1]["verified_service_images"], self.proof["verified_service_images"])
        self.assertEqual(writes[0][1]["configuration_scope"], "CI_GENERATED_CONFIG_ONLY_NOT_TARGET")
        self.assertEqual(writes[0][1]["selected_config_files_sha256"], self.proof["selected_config_files_sha256"])
        self.assertNotIn("do-not-publish", json.dumps(writes[0][1]))
        self.assertFalse(any("build" in command or "pull" in command or "up" in command for command in calls))

    def test_exact_audit_missing_local_image_changed_config_and_scanner_failure_do_not_emit_proof(self):
        original = {"services": {name: {"image": row["image"]} for name, row in self.scope["services"].items() if row["enabled"]}}
        args = ["ci_full_image_audit.py", "--env-file", "fixture.env", "--scanner", "fixture-trivy",
                "--scanner-sha256", "0" * 64, "--cache", str(self.root), "--output", str(self.root / "audit-output"),
                "--release-scope", str(self.root / "pr4-release-scope.json")]
        for mutation in ("local-image-missing", "local-image-mismatch", "recovery-missing", "image-changed", "build-configured", "scanner-failed"):
            with self.subTest(mutation=mutation):
                config = copy.deepcopy(original)
                if mutation == "recovery-missing":
                    config["services"].pop("legacy-verifier")
                elif mutation == "image-changed":
                    config["services"]["backup"]["image"] = "fixture/other@sha256:" + "a" * 64
                elif mutation == "build-configured":
                    config["services"]["api"]["build"] = {"context": "."}

                def output(command, **kwargs):
                    if command[-3:] == ["config", "--format", "json"]:
                        return json.dumps(config).encode()
                    if mutation == "local-image-missing":
                        raise subprocess.CalledProcessError(1, command, stderr=b"fixture absent")
                    if mutation == "local-image-mismatch":
                        return ("sha256:" + "0" * 64).encode()
                    return command[3].split("@")[1].encode()

                with patch.object(sys, "argv", args), patch.object(ci_full_image_audit, "read_env", return_value={}), \
                        patch.object(ci_full_image_audit, "compose_environment", return_value={}), \
                        patch.object(ci_full_image_audit.subprocess, "check_output", side_effect=output), \
                        patch.object(ci_full_image_audit.subprocess, "run", return_value=subprocess.CompletedProcess([], 2)) as scan, \
                        patch.object(ci_full_image_audit, "write_new") as write:
                    self.assertEqual(ci_full_image_audit.main(), 2)
                write.assert_not_called()
                if mutation != "scanner-failed":
                    scan.assert_not_called()


if __name__ == "__main__":
    unittest.main()
