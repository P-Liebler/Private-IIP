"""Core high internal ports never widen the private public-port contract."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preflight import validate_compose


class CorePortTests(unittest.TestCase):
    def check(self, port, *, core=True):
        values = {"VPN_BIND_ADDRESS": "10.9.0.2", "APP_ENV": "production"}
        backend = {"environment": {"APP_ENV": "production", "SESSION_SECURE_COOKIE": "true"}}
        config = {"services": {"api": backend, "worker": backend, "scheduler": backend,
                               "caddy": {"ports": [port]}}}
        return validate_compose(config, values, core=core)

    def test_explicit_core_high_ports_preserve_standard_origin_and_private_bind(self):
        for target, published in ((8080, "80"), (8443, "443")):
            self.assertEqual(self.check({"target": target, "published": published,
                                         "host_ip": "10.9.0.2", "protocol": "tcp"}), [])

    def test_high_port_mapping_is_not_implicitly_enabled_for_legacy_target(self):
        port = {"target": 8443, "published": "443", "host_ip": "10.9.0.2", "protocol": "tcp"}
        self.assertIn("UNEXPECTED_PUBLISHED_PORT_CADDY", self.check(port, core=False))
        self.assertEqual(self.check(port | {"target": 443}, core=False), [])
        self.assertIn("UNEXPECTED_PUBLISHED_PORT_CADDY", self.check(port | {"target": 443}))

    def test_public_wrong_hostport_s3_udp_or_invalid_port_is_rejected(self):
        port = {"target": 8443, "published": "443", "host_ip": "10.9.0.2", "protocol": "tcp"}
        for change in ({"host_ip": "0.0.0.0"}, {"host_ip": "127.0.0.1"},
                       {"published": "9443"}, {"target": 9002}, {"protocol": "udp"},
                       {"published": "invalid"}, {"published": None}):
            self.assertIn("UNEXPECTED_PUBLISHED_PORT_CADDY", self.check(port | change))
