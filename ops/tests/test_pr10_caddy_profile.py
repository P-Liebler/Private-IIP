from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "pr10_caddy_profile_probe", Path(__file__).resolve().parents[1] / "caddy/pr10_profile_probe.py"
)
assert SPEC is not None and SPEC.loader is not None
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


class CaddyProfileReviewTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "apps": {
                "http": {"servers": {"test": {"protocols": ["h1", "h2"], "routes": [
                    {"group": "g", "match": [{"path": ["/internal/*"]}],
                     "handle": [{"handler": "static_response", "status_code": 404}]},
                    {"group": "g", "handle": [{"handler": "reverse_proxy", "upstreams": [
                        {"dial": target} for target in sorted(PROBE.UPSTREAMS)
                    ]}]},
                ]}}},
                "tls": {"automation": {"policies": [{"issuers": [{"module": "internal"}]}]}},
            }
        }

    def test_configuration_evidence_never_approves_security(self):
        result = PROBE.inspect_profile(self.config)
        self.assertFalse(result["security_approved"])
        self.assertFalse(result["whole_program_unreachability_proven"])
        self.assertEqual(result["admin"], "localhost:2019")

    def test_configured_acme_server_invalidates_narrow_review(self):
        self.config["apps"]["http"]["servers"]["test"]["routes"][0]["handle"].append(
            {"handler": "acme_server"}
        )
        with self.assertRaises(ValueError):
            PROBE.inspect_profile(self.config)

    def test_on_demand_certificates_need_new_review(self):
        self.config["apps"]["tls"]["automation"]["policies"][0]["on_demand"] = True
        with self.assertRaises(ValueError):
            PROBE.inspect_profile(self.config)

    def test_non_internal_issuer_needs_new_review(self):
        self.config["apps"]["tls"]["automation"]["policies"][0]["issuers"][0]["module"] = "acme"
        with self.assertRaises(ValueError):
            PROBE.inspect_profile(self.config)

    def test_remote_administration_needs_new_review(self):
        for admin in ({"listen": ":2019"}, {"remote": {"listen": ":2021"}},
                      {"identity": {"identifiers": ["test"]}}):
            with self.subTest(admin=admin), self.assertRaises(ValueError):
                PROBE.inspect_profile(dict(copy.deepcopy(self.config), admin=admin))

    def test_unexpected_upstream_or_app_needs_new_review(self):
        modified = copy.deepcopy(self.config)
        modified["apps"]["http"]["servers"]["test"]["routes"][1]["handle"][0]["upstreams"][0]["dial"] = "unknown:80"
        with self.assertRaises(ValueError):
            PROBE.inspect_profile(modified)
        self.config["apps"]["unknown_app"] = {}
        with self.assertRaises(ValueError):
            PROBE.inspect_profile(self.config)

    def test_old_standalone_respond_after_fallback_is_rejected(self):
        routes = self.config["apps"]["http"]["servers"]["test"]["routes"]
        routes.reverse()
        with self.assertRaises(ValueError):
            PROBE.inspect_internal_routing(self.config)

    def test_nonterminal_or_unprotected_internal_response_is_rejected(self):
        routes = self.config["apps"]["http"]["servers"]["test"]["routes"]
        routes[0]["handle"][0]["status_code"] = 200
        with self.assertRaises(ValueError):
            PROBE.inspect_internal_routing(self.config)
        routes.pop(0)
        with self.assertRaises(ValueError):
            PROBE.inspect_internal_routing(self.config)

    def test_unavailable_http3_advertisement_requires_new_review(self):
        self.config["apps"]["http"]["servers"]["test"]["protocols"].append("h3")
        with self.assertRaises(ValueError):
            PROBE.inspect_profile(self.config)


if __name__ == "__main__":
    unittest.main()
