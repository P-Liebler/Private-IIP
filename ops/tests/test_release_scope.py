"""Active recovery and optional services cannot escape the security gate."""
import copy
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_scope import CORE_REQUIRED, evaluate_scope, main, validate_scope
from security_ci_status import classify


class ReleaseScopeTests(unittest.TestCase):
    def setUp(self):
        self.reference = "synthetic@sha256:" + "a" * 64
        self.scope = {"contract": "PRIVATE_CORE_SCOPE_V1", "services": {
            name: {"role": role, "enabled": True, "image": self.reference,
                   "reason": "synthetic contract"}
            for name, role in [("api", "runtime"), ("backup", "recovery")]}}
        for name in CORE_REQUIRED - self.scope["services"].keys():
            self.scope["services"][name] = {"role": "runtime", "enabled": True,
                "image": self.reference, "reason": "synthetic core dependency"}
        self.config = {"services": {name: {"image": self.reference} for name in self.scope["services"]}}
        self.inventory = {"images": [{"component": name, "image_reference": self.reference,
            "image_id": self.reference.split("@")[1], "scan_status": "SCANNED_EXACT_IMAGE",
            "sbom_sha256": "b" * 64, "findings": []} for name in self.scope["services"]]}
        self.inventory["scanner_database"] = {"UpdatedAt": datetime.now(UTC).isoformat()}

    def test_exact_scope_still_needs_runtime_review(self):
        self.assertEqual(evaluate_scope(self.scope, self.inventory, self.config), "SECURITY_REVIEW_REQUIRED")

    def test_recovery_critical_blocks_even_when_runtime_is_clean(self):
        self.inventory["images"][1]["findings"] = [{"severity": "CRITICAL"}]
        self.assertEqual(evaluate_scope(self.scope, self.inventory, self.config), "SECURITY_BLOCKED")

    def test_missing_changed_or_unscanned_started_service_fails(self):
        for mutation in ["missing", "extra", "build", "digest"]:
            config = copy.deepcopy(self.config)
            if mutation == "missing":
                del config["services"]["backup"]
            elif mutation == "extra":
                config["services"]["ollama"] = {"image": self.reference}
            elif mutation == "build":
                config["services"]["api"]["build"] = {"context": "."}
            else:
                config["services"]["api"]["image"] = "synthetic@sha256:" + "c" * 64
            with self.subTest(mutation=mutation):
                self.assertEqual(evaluate_scope(self.scope, self.inventory, config), "SCAN_INCOMPLETE")

    def test_disabled_recovery_and_active_legacy_rejected(self):
        self.scope["services"]["backup"]["enabled"] = False
        with self.assertRaisesRegex(ValueError, "REQUIRED_SERVICE_DISABLED"):
            validate_scope(self.scope)
        self.scope["services"]["backup"]["enabled"] = True
        self.scope["services"]["api"]["role"] = "migration_source"
        with self.assertRaisesRegex(ValueError, "LEGACY_SERVICE_CANNOT_BE_ACTIVE"):
            validate_scope(self.scope)

    def test_historical_blocker_preserved_without_claiming_active_scan(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / "old.json", Path(folder) / "receipt.json"
            self.inventory["images"][0]["findings"] = [{"severity": "CRITICAL"}]
            source.write_text(json.dumps(self.inventory))
            with patch("sys.argv", ["release_scope", "historical", str(source), "--output", str(output)]):
                self.assertEqual(main(), 0)
            record = json.loads(output.read_text())
            self.assertEqual(record["status"], "SECURITY_BLOCKED")
            self.assertEqual(record["kind"], "HISTORICAL_ONLY")
            self.assertEqual(record["release_status"], "NOT_APPROVED")

    def test_archived_images_are_not_a_substitute_for_active_inventory(self):
        self.scope["services"]["old"] = {"role": "archive", "enabled": False,
            "image": self.reference, "reason": "retained immutable original"}
        self.assertEqual(evaluate_scope(self.scope, self.inventory, self.config), "SECURITY_REVIEW_REQUIRED")
        self.inventory["images"] = self.inventory["images"][:1]
        self.assertEqual(evaluate_scope(self.scope, self.inventory, self.config), "SCAN_INCOMPLETE")

    def test_stale_or_future_database_cannot_clear_scope(self):
        for offset in [timedelta(days=-3), timedelta(days=1)]:
            self.inventory["scanner_database"]["UpdatedAt"] = (datetime.now(UTC) + offset).isoformat()
            self.assertEqual(evaluate_scope(self.scope, self.inventory, self.config), "SCAN_INCOMPLETE")
