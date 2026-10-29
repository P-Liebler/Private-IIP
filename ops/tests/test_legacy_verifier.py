import hashlib
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_legacy_model import VERIFIER, verify


class LegacyIsolationTests(unittest.TestCase):
    def runner(self, start=None, *, create_timeout=False, remove_fails=False, list_fails=False,
               unexpected_id=False):
        state = {"exists": False}
        identity = "c" * 64
        start = start or SimpleNamespace(returncode=0, stdout=b'{"verified":true,"artifact_sha256":"expected"}')

        def call(command, **kwargs):
            if command[1] == "create":
                state["exists"] = True
                if create_timeout:
                    raise subprocess.TimeoutExpired(command, 30)
                return SimpleNamespace(returncode=0, stdout=identity.encode() + b"\n")
            if command[1] == "start":
                if isinstance(start, Exception):
                    raise start
                return start
            if command[1:3] == ["container", "ls"]:
                if list_fails:
                    return SimpleNamespace(returncode=1, stdout=b"")
                actual = "d" * 64 if unexpected_id else identity
                return SimpleNamespace(returncode=0, stdout=actual.encode() + b"\n" if state["exists"] else b"")
            if command[1:3] == ["container", "rm"]:
                self.assertEqual(command, ["docker", "container", "rm", "--force", identity])
                if not remove_fails:
                    state["exists"] = False
                return SimpleNamespace(returncode=1 if remove_fails else 0, stdout=b"")
            self.fail("Unexpected Docker operation")

        return call, state

    def test_digest_and_input_limits_fail_before_docker(self):
        with patch("verify_legacy_model.subprocess.run") as run:
            for data, image in ((b"{}", "legacy:latest"), (b"x" * 30_000_001, "unused")):
                with self.assertRaises(ValueError):
                    verify(data, image)
            run.assert_not_called()

    def test_isolation_flags_and_typed_hash_result(self):
        runner, state = self.runner()
        with patch("verify_legacy_model.subprocess.run", side_effect=runner) as run:
            value = verify(b'{"artifact_sha256":"expected"}', "private-iip/backend@sha256:" + "b" * 64)
        command = run.call_args_list[0].args[0]
        for flag, expected in (("--network", "none"), ("--cap-drop", "ALL"), ("--user", "10001:10001")):
            self.assertEqual(command[command.index(flag) + 1], expected)
        self.assertIn("--read-only", command)
        self.assertNotIn("--volume", command)
        self.assertNotIn("-v", command)
        self.assertTrue(value["verified"])
        self.assertFalse(state["exists"])
        self.assertTrue(value["container_cleanup_verified"])
        self.assertEqual(run.call_args_list[1].args[0], ["docker", "start", "--attach", "--interactive", "c" * 64])
        self.assertEqual(run.call_args_list[1].kwargs["input"], b'{"artifact_sha256":"expected"}')
        self.assertNotIn("input", run.call_args_list[0].kwargs)
        self.assertIn("--label", command)

    def test_failed_process_or_different_artifact_cannot_be_verified(self):
        for result in (SimpleNamespace(returncode=1, stdout=b""), SimpleNamespace(returncode=0, stdout=b'{"verified":true,"artifact_sha256":"wrong"}')):
            runner, state = self.runner(start=result)
            with patch("verify_legacy_model.subprocess.run", side_effect=runner):
                with self.assertRaises(ValueError):
                    verify(b'{"artifact_sha256":"expected"}', "private-iip/backend@sha256:" + "b" * 64)
            self.assertFalse(state["exists"])

    def test_attached_client_timeout_force_removes_daemon_container(self):
        runner, state = self.runner(start=subprocess.TimeoutExpired("docker start", 90))
        with patch("verify_legacy_model.subprocess.run", side_effect=runner) as run:
            with self.assertRaisesRegex(ValueError, "LEGACY_VERIFICATION_FAILED"):
                verify(b"{}", "fixture@sha256:" + "b" * 64)
        self.assertFalse(state["exists"])
        self.assertTrue(any(call.args[0][1:3] == ["container", "rm"] for call in run.call_args_list))

    def test_create_timeout_discovers_only_labelled_owned_container(self):
        runner, state = self.runner(create_timeout=True)
        with patch("verify_legacy_model.subprocess.run", side_effect=runner) as run:
            with self.assertRaisesRegex(ValueError, "LEGACY_VERIFICATION_FAILED"):
                verify(b"{}", "fixture@sha256:" + "b" * 64)
        self.assertFalse(state["exists"])
        self.assertFalse(any(call.args[0][1] == "start" for call in run.call_args_list))
        owned = run.call_args_list[1].args[0][-1]
        self.assertTrue(owned.startswith("label=iip.legacy-verifier-session="))

    def test_remaining_container_never_returns_verified_result(self):
        runner, state = self.runner(remove_fails=True)
        with patch("verify_legacy_model.subprocess.run", side_effect=runner):
            with self.assertRaisesRegex(ValueError, "CLEANUP_UNCONFIRMED"):
                verify(b'{"artifact_sha256":"expected"}', "fixture@sha256:" + "b" * 64)
        self.assertTrue(state["exists"])

    def test_unavailable_daemon_is_not_reported_as_no_containers(self):
        runner, _ = self.runner(list_fails=True)
        with patch("verify_legacy_model.subprocess.run", side_effect=runner):
            with self.assertRaisesRegex(ValueError, "CLEANUP_UNCONFIRMED"):
                verify(b'{"artifact_sha256":"expected"}', "fixture@sha256:" + "b" * 64)

    def test_unexpected_identity_is_not_removed(self):
        runner, _ = self.runner(unexpected_id=True)
        with patch("verify_legacy_model.subprocess.run", side_effect=runner) as run:
            with self.assertRaisesRegex(ValueError, "CLEANUP_UNCONFIRMED"):
                verify(b'{"artifact_sha256":"expected"}', "fixture@sha256:" + "b" * 64)
        self.assertFalse(any(call.args[0][1:3] == ["container", "rm"] for call in run.call_args_list))

    def test_embedded_historical_program_bytes_are_unchanged(self):
        self.assertEqual(hashlib.sha256(VERIFIER.encode()).hexdigest(),
                         "c8e41f8a48a5cdc9faaf320b35c0791b2521dcc04d7364d8895427b7ee337799")
