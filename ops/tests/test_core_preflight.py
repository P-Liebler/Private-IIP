import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core_preflight import check
from release_scope import CORE_REQUIRED


class CorePreflightTests(unittest.TestCase):
    def setUp(self):
        self.ref = "synthetic@sha256:" + "a" * 64
        self.scope = {"contract": "PRIVATE_CORE_SCOPE_V1", "services": {
            name: {"role": role, "enabled": True, "image": self.ref, "reason": "test"}
            for name, role in [("api", "runtime"), ("backup", "recovery")]}}
        for name in CORE_REQUIRED - self.scope["services"].keys():
            self.scope["services"][name] = {"role": "runtime", "enabled": True,
                "image": self.ref, "reason": "synthetic core dependency"}
        self.config = {"services": {name: {"image": self.ref} for name in CORE_REQUIRED}}

    def check(self, config=None, free=6 * 1024**3):
        with patch("core_preflight.validate_config", return_value=[]), patch("core_preflight.validate_compose", return_value=[]):
            return check(self.scope, config or self.config, {}, "STAGING", {self.ref: self.ref.split("@")[1]}, free)

    def test_scope_matches_and_resources_checked_without_deployment(self):
        self.assertEqual(self.check(), [])
        self.assertIn("BACKUP_FREE_SPACE_BELOW_5_GIB", self.check(free=1024))

    def test_native_storage_port_and_original_volume_block(self):
        config = copy.deepcopy(self.config)
        config["services"]["api"].update(ports=[{"target": 9000}],
            networks={"edge": {}},
            volumes=[{"type": "volume", "source": "investment-intelligence_minio_data"}])
        errors = self.check(config)
        self.assertIn("ORIGINAL_VOLUME_FORBIDDEN", errors)
        self.assertIn("CORE_PRIVATE_PORT_REQUIRED_API", errors)
        self.assertIn("CORE_EDGE_ACCESS_FORBIDDEN_API", errors)

    def test_changed_digest_and_extra_started_service_block(self):
        self.config["services"]["api"]["image"] = "synthetic:latest"
        self.config["services"]["ollama"] = {"image": self.ref}
        self.assertIn("UNPINNED_OR_CHANGED_SERVICE_API", self.check())
        self.assertIn("RELEASE_SERVICE_SET_MISMATCH", self.check())
