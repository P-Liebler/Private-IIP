"""Offline deployment goldens; no Docker daemon, financial network or real secrets."""
import base64
import json
import secrets
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preflight import read_env, validate_compose, validate_config
from operation_lock import acquire
from backup import prune
import backup
import restore_verify
from redact_test_artifacts import redact


class PreflightTests(unittest.TestCase):
    def test_backup_keeps_stage_overrides_and_private_environment_in_command(self):
        with patch("backup.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = b"synthetic dump"
            result = backup.compose([Path("base.yml"), Path("stage.yml")], Path("private.env"), "exec", "-T", "postgres", "pg_dump")
        self.assertEqual(run.call_args.args[0], ["docker", "compose", "-f", "base.yml", "-f", "stage.yml", "--env-file", "private.env", "exec", "-T", "postgres", "pg_dump"])
        self.assertEqual(result, b"synthetic dump")

    def test_browser_diagnostics_redact_session_and_auth_headers(self):
        value = "cookie: investment_session=private-token\nauthorization: Bearer private-token\nnormal result"
        self.assertNotIn("private-token", redact(value))
        self.assertIn("normal result", redact(value))

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.values = dict(
            APP_DOMAIN="iip.private.test", VPN_BIND_ADDRESS="10.9.0.2", APP_ENV="production",
            COMPOSE_PROJECT_NAME="iip-production", POSTGRES_DB="iip", POSTGRES_USER="iip",
            POSTGRES_PASSWORD=secrets.token_hex(24), MINIO_ACCESS_KEY="iip",
            MINIO_SECRET_KEY=secrets.token_hex(24), GRAFANA_ADMIN_USER="operator",
            GRAFANA_ADMIN_PASSWORD=secrets.token_hex(24),
            TOTP_ENCRYPTION_KEY=base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
            BACKUP_ROOT=self.folder.name,
        )

    def test_valid_configuration_is_not_target_acceptance(self):
        self.assertEqual(validate_config(self.values, "PRODUCTION"), [])

    def test_missing_placeholders_and_development_secrets(self):
        for key in self.values:
            with self.subTest(key=key):
                self.assertTrue(validate_config(self.values | {key: ""}, "PRODUCTION"))
        for value in ("dev-only-secret", "REPLACE_WITH_LONG_RANDOM_PASSWORD", "changeme"):
            self.assertTrue(validate_config(self.values | {"POSTGRES_PASSWORD": value}, "PRODUCTION"))

    def test_public_loopback_and_invalid_bindings(self):
        for address in ("0.0.0.0", "::", "127.0.0.1", "::1", "8.8.8.8", "garbage"):
            with self.subTest(address=address):
                self.assertTrue(validate_config(self.values | {"VPN_BIND_ADDRESS": address}, "PRODUCTION"))

    def test_wrong_domain_cookie_key_and_test_assistant(self):
        for key, value in (("APP_DOMAIN", "https://wrong/"), ("FRONTEND_ORIGIN", "https://wrong.test"),
                           ("SESSION_SECURE_COOKIE", "false"), ("MINIO_SECURE", "false"),
                           ("TOTP_ENCRYPTION_KEY", "not-a-key"), ("ASSISTANT_TEST_MODE", "true"),
                           ("APP_DEBUG", "true"), ("BACKUP_ROOT", "./backups")):
            with self.subTest(key=key):
                errors = validate_config(self.values | {key: value}, "PRODUCTION")
                self.assertTrue(errors)
                self.assertNotIn(self.values["POSTGRES_PASSWORD"], json.dumps(errors))

    def test_staging_has_separate_project_and_secure_requirements(self):
        self.assertTrue(validate_config(self.values, "STAGING"))
        values = self.values | {"APP_ENV": "staging", "COMPOSE_PROJECT_NAME": "iip-staging"}
        self.assertEqual(validate_config(values, "STAGING"), [])

    def test_unexpected_public_database_and_socket(self):
        config = {"services": {"postgres": {"ports": [{"target": 5432, "host_ip": "0.0.0.0"}]}}}
        self.assertIn("UNEXPECTED_PUBLISHED_PORT_POSTGRES", validate_compose(config, self.values))
        config["services"]["postgres"] = {"volumes": [{"source": "/var/run/docker.sock"}]}
        self.assertIn("DOCKER_SOCKET_FORBIDDEN", validate_compose(config, self.values))

    def test_duplicate_env_keys_fail(self):
        target = Path(self.folder.name) / "duplicate.env"
        target.write_text("APP_ENV=production\nAPP_ENV=staging\n")
        with self.assertRaises(ValueError):
            read_env(target)

    def test_backup_and_restore_cannot_overlap(self):
        root = Path(self.folder.name)
        first = acquire(root)
        try:
            with self.assertRaises(RuntimeError):
                acquire(root)
        finally:
            first.close()
        acquire(root).close()

    def test_retention_preserves_failed_and_last_good(self):
        root = Path(self.folder.name)
        for index in range(40):
            item = root / "sets" / str(index)
            item.mkdir(parents=True)
            (item / "manifest.json").write_text(json.dumps({"success": index != 39, "completed_at": f"2026-09-{index % 28 + 1:02}T00:00:00+00:00"}))
        prune(root)
        self.assertTrue((root / "sets" / "39").is_dir())
        self.assertTrue(any(json.loads(p.read_text())["success"] for p in (root / "sets").glob("*/manifest.json")))

    def test_failed_backup_is_visible_and_does_not_prune(self):
        root = Path(self.folder.name)
        with patch.object(sys, "argv", ["backup.py", "--root", str(root), "--prune"]), patch.object(backup, "compose", side_effect=RuntimeError("password must never appear")), patch.object(backup, "prune") as pruning:
            self.assertEqual(backup.main(), 1)
        status = json.loads((root / "runtime/backup-status.json").read_text())
        self.assertFalse(status["success"])
        self.assertNotIn("password must never appear", json.dumps(status))
        pruning.assert_not_called()

    def test_restore_hash_mismatch_fails_before_docker_and_is_visible(self):
        root = Path(self.folder.name)
        item = root / "sets" / "tampered"
        item.mkdir(parents=True)
        (item / "postgres.dump").write_bytes(b"modified")
        (item / "manifest.json").write_text(json.dumps({"success": True, "checksums": {"postgres.dump": "0" * 64}}))
        command = ["restore_verify.py", str(item), "--root", str(root), "--username", "synthetic", "--portfolio-id", "synthetic", "--raw-id", "synthetic", "--expected-value", "10180"]
        with patch.object(sys, "argv", command), patch.dict("os.environ", {"RESTORE_TEST_PASSWORD": "synthetic-fixture-only"}), patch.object(restore_verify, "command") as docker:
            self.assertEqual(restore_verify.main(), 1)
        docker.assert_not_called()
        self.assertFalse(json.loads((root / "runtime/restore-status.json").read_text())["success"])


if __name__ == "__main__":
    unittest.main()
