"""Offline contracts for the optional oc transport; never contact a cluster."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import backup
from openshift_backup import (
    Config, MIRROR, OpenShiftBackupTransport, PG_DUMP, Pod, extract_ustar, verify_reviews,
)

NOW = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
RUN = "20261028T120000Z-123"


def archive(entries):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as stream:
        for name, content, kind in entries:
            item = tarfile.TarInfo(name)
            item.type = kind
            item.size = len(content)
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                item.linkname = "../../outside"
            stream.addfile(item, io.BytesIO(content))
    return output.getvalue()


def make_config(root):
    pod = lambda name: Pod(name, name + "-uid", name,
                           "private-iip/" + name + "@sha256:" + "a" * 64,
                           "registry.invalid/" + name + "@sha256:" + "a" * 64,
                           "cri-o://" + name + "-container")
    return Config(context="fixture-context", namespace="investment", namespace_uid="namespace-uid",
                  session="fixture-backup-session", lease_name="backup-lock", lease_uid="lock-uid",
                  writer_selector="app.kubernetes.io/part-of=investment,investment.local/backup-writer=true",
                  writer_deployments={name: name for name in ("api", "web", "worker", "scheduler")},
                  postgres=pod("postgres"), backup_agent=pod("backup-agent"),
                  database="investment", bucket="raw-ingestions", root=root,
                  operator_receipt=root / "operator.json", operator_receipt_sha256="b" * 64,
                  destination_policy=root / "destination.json", destination_policy_sha256="c" * 64)


def metadata(config, overrides=None):
    values = {
        ("namespace", config.namespace): config.namespace_uid,
        ("lease", config.lease_name): "\n".join((config.lease_uid, config.session,
                                                   NOW.isoformat(), "60")),
        ("deployments", None): "".join(name + "\t0\t0\t0\t0\n"
                                      for name in config.writer_deployments.values()),
        ("pods", None): "",
        ("jobs", None): "",
    }
    for pod in (config.postgres, config.backup_agent):
        values[("pod", pod.name)] = "\n".join((config.namespace, pod.uid, "Running", pod.image,
                                                 pod.image_id, pod.container_id, "true", NOW.isoformat()))
    values.update(overrides or {})
    return lambda kind, name, template, **kwargs: values[(kind, name)]


class OpenShiftBackupTests(unittest.TestCase):
    def transport(self, config, overrides=None):
        with patch.object(OpenShiftBackupTransport, "_get", side_effect=metadata(config, overrides)):
            return OpenShiftBackupTransport(config, engine_root=config.root,
                                            verify_preconditions=lambda config, now: None,
                                            now=lambda: NOW)

    def test_config_root_mismatch_fails_before_cluster_or_artifact_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            other = root / "other"
            other.mkdir()
            config = make_config(root)
            with patch.object(OpenShiftBackupTransport, "_get") as get:
                with self.assertRaisesRegex(RuntimeError, "ROOT_MISMATCH"):
                    OpenShiftBackupTransport(config, engine_root=other)
                get.assert_not_called()
            self.assertEqual(list(other.iterdir()), [])

    def test_default_review_requires_exact_scope_and_real_destination_verifier(self):
        with tempfile.TemporaryDirectory() as directory:
            config = make_config(Path(directory).resolve())
            config.destination_policy.write_bytes(b'{"synthetic":"policy-only"}')
            config = replace(config, destination_policy_sha256=hashlib.sha256(config.destination_policy.read_bytes()).hexdigest())
            review = {"contract": "OPENSHIFT_BACKUP_OPERATOR_SCOPE_V1",
                      "status": "OPERATOR_REVIEWED_BACKUP_SCOPE", "operator": "synthetic-operator",
                      "reviewed_at": (NOW - timedelta(minutes=1)).isoformat(),
                      "expires_at": (NOW + timedelta(minutes=10)).isoformat(),
                      "scope": config.operator_scope()}
            config.operator_receipt.write_text(json.dumps(review))
            config = replace(config, operator_receipt_sha256=hashlib.sha256(config.operator_receipt.read_bytes()).hexdigest())
            with patch("backup_destination.verify") as verify:
                verify_reviews(config, NOW)
                verify.assert_called_once_with(config.destination_policy, config.root)
            with patch("backup_destination.verify", side_effect=ValueError("SYNTHETIC PRIVATE ERROR")):
                with self.assertRaisesRegex(RuntimeError, "OPERATOR_OR_DESTINATION_NOT_VERIFIED") as error:
                    verify_reviews(config, NOW)
                self.assertNotIn("PRIVATE", str(error.exception))
            with self.assertRaisesRegex(RuntimeError, "OPERATOR_SCOPE_NOT_VERIFIED"):
                verify_reviews(config, NOW + timedelta(hours=1))
            config.operator_receipt.write_text("changed")
            with self.assertRaisesRegex(RuntimeError, "REVIEW_FILE_CHANGED"):
                verify_reviews(config, NOW)

    def test_constructor_refuses_missing_reviews_before_any_cluster_call(self):
        with tempfile.TemporaryDirectory() as directory:
            config = make_config(Path(directory).resolve())
            with patch.object(OpenShiftBackupTransport, "_get") as get:
                with self.assertRaisesRegex(RuntimeError, "OPERATOR_OR_DESTINATION_NOT_VERIFIED"):
                    OpenShiftBackupTransport(config, engine_root=config.root, now=lambda: NOW)
                get.assert_not_called()

    def test_namespace_lease_writer_and_container_changes_are_blockers(self):
        with tempfile.TemporaryDirectory() as directory:
            config = make_config(Path(directory).resolve())
            valid = metadata(config)
            pod = valid("pod", "postgres", "")
            variants = [
                ({("namespace", "investment"): "different"}, "NAMESPACE_CHANGED"),
                ({("lease", "backup-lock"): "lock-uid\nwrong-holder\n" + NOW.isoformat() + "\n60"}, "LEASE_NOT_HELD"),
                ({("lease", "backup-lock"): "lock-uid\nfixture-backup-session\n" + (NOW - timedelta(minutes=2)).isoformat() + "\n60"}, "LEASE_NOT_HELD"),
                ({("lease", "backup-lock"): "lock-uid\nfixture-backup-session\n" + (NOW + timedelta(seconds=1)).isoformat() + "\n60"}, "LEASE_NOT_HELD"),
                ({("deployments", None): "api\t1\t1\t1\t1\n"}, "WRITERS_NOT_QUIESCED"),
                ({("deployments", None): "api\t0\t0\t0\t0\n"}, "WRITER_SCOPE_CHANGED"),
                ({("deployments", None): valid("deployments", None, "") + "unknown\t0\t0\t0\t0\n"}, "WRITER_SCOPE_CHANGED"),
                ({("pods", None): "worker-old\tRunning\n"}, "WRITER_PODS_ACTIVE"),
                ({("pods", None): "worker-new\tPending\n"}, "WRITER_PODS_ACTIVE"),
                ({("pods", None): "worker-lost\tUnknown\n"}, "WRITER_PODS_ACTIVE"),
                ({("jobs", None): "migration\tfalse\t1\t\n"}, "NAMESPACE_JOBS_NOT_QUIESCED"),
                ({("jobs", None): "pending-job\tfalse\t\t\n"}, "NAMESPACE_JOBS_NOT_QUIESCED"),
                ({("pod", "postgres"): pod.replace("postgres-uid", "new-uid")}, "POD_IDENTITY_OR_STATE_CHANGED"),
                ({("pod", "postgres"): pod.replace("cri-o://postgres-container", "cri-o://restarted")}, "POD_IDENTITY_OR_STATE_CHANGED"),
                ({("pod", "postgres"): pod.replace("@sha256:" + "a" * 64, "@sha256:" + "d" * 64)}, "POD_IDENTITY_OR_STATE_CHANGED"),
            ]
            for override, expected in variants:
                with self.subTest(expected=expected, override=override):
                    with self.assertRaisesRegex(RuntimeError, expected):
                        self.transport(config, override)

    def test_only_three_engine_calls_allowed_without_env_or_secret_readback(self):
        with tempfile.TemporaryDirectory() as directory:
            config = make_config(Path(directory).resolve())
            transport = self.transport(config)
            with patch.object(transport, "verify_scope") as verify, patch.object(transport, "_stream") as stream:
                for args in (("config",), ("up", "-d"), ("exec", "postgres", "printenv"),
                             ("exec", "-T", "postgres", "printenv", "POSTGRES_PASSWORD"),
                             ("--profile", "ops", "run", "--rm", "backup", "mirror", "local/other", "/backup/sets/x/raw")):
                    with self.assertRaisesRegex(RuntimeError, "CALL_NOT_ALLOWED"):
                        transport.compose(Path("unused.yml"), Path("DO_NOT_READ.env"), *args)
                verify.assert_not_called()
                stream.assert_not_called()

    def test_existing_backup_engine_creates_manifest_and_checksums_without_docker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            config = make_config(root)
            transport = self.transport(config)
            executed = []
            raw = archive([("./", b"", tarfile.DIRTYPE), ("./provider/", b"", tarfile.DIRTYPE),
                           ("./provider/exact.bin", b"exact-original\x00bytes", tarfile.REGTYPE)])
            @contextmanager
            def stream(args):
                executed.append(args)
                command = args[args.index("--") + 1:]
                if command == ["printenv", "POSTGRES_DB"]:
                    yield io.BytesIO(b"investment\n")
                elif command == ["sh", "-c", PG_DUMP]:
                    yield io.BytesIO(b"PGDMPsynthetic-custom-dump")
                elif command[:3] == ["sh", "-ec", MIRROR]:
                    yield io.BytesIO()
                elif command[:3] == ["tar", "-c", "-C"]:
                    yield io.BytesIO(raw)
                else:
                    self.fail("Unexpected transport command")
            with patch.object(transport, "_get", side_effect=metadata(config)), patch.object(transport, "_stream", side_effect=stream), patch.object(OpenShiftBackupTransport, "from_file", return_value=transport) as factory, patch.object(backup, "compose") as docker, patch.object(sys, "argv", ["backup.py", "--root", str(root), "--openshift-config", str(root / "reviewed-config.json")]), patch("subprocess.Popen") as external:
                self.assertEqual(backup.main(), 0)
                factory.assert_called_once_with(root / "reviewed-config.json", engine_root=root)
                docker.assert_not_called()
                external.assert_not_called()
            status = json.loads((root / "runtime/backup-status.json").read_text())
            result = root / "sets" / status["run_id"]
            manifest = json.loads((result / "manifest.json").read_text())
            self.assertTrue(manifest["success"])
            self.assertEqual(manifest["raw_object_count"], 1)
            self.assertEqual((result / "raw/provider/exact.bin").read_bytes(), b"exact-original\x00bytes")
            self.assertEqual(manifest["checksums"]["raw/provider/exact.bin"], hashlib.sha256(b"exact-original\x00bytes").hexdigest())
            self.assertEqual(len(executed), 4)
            self.assertTrue(all(args[0] == "exec" for args in executed))
            self.assertIn("S3_CA_REQUIRED=true", executed[2][executed[2].index("-ec") + 1])
            self.assertNotIn("POSTGRES_PASSWORD", repr(executed))

    def test_cli_never_falls_back_or_writes_when_openshift_review_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for extra in ([], ["--env-file", "unused.env"], ["--compose-override", "unused.yml"]):
                with patch.object(sys, "argv", ["backup.py", "--root", str(root), "--openshift-config", str(root / "missing.json"), *extra]), patch.object(backup, "compose") as docker:
                    self.assertEqual(backup.main(), 2)
                    docker.assert_not_called()
                    self.assertEqual(list(root.iterdir()), [])

    def test_basic_busybox_header_accepted_but_gnu_extension_fields_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / "raw"
            target.mkdir()
            data = bytearray(archive([("original.bin", b"exact", tarfile.REGTYPE)]))
            def header(extension=False):
                changed = bytearray(data)
                changed[257:265] = b"ustar  \x00"
                if extension:
                    changed[345] = 1
                changed[148:156] = b"        "
                changed[148:156] = ("%06o\0 " % sum(changed[:512])).encode()
                return changed
            with self.assertRaisesRegex(RuntimeError, "ARCHIVE_HEADER_INVALID"):
                extract_ustar(io.BytesIO(header(True)), target, make_config(root))
            extract_ustar(io.BytesIO(header()), target, make_config(root))
            self.assertEqual((target / "original.bin").read_bytes(), b"exact")

    def test_failed_post_transfer_recheck_never_yields_engine_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            config = make_config(root)
            transport = self.transport(config)
            transport._database_checked = True
            transport._dump_run, transport._dump_completed = RUN, True
            target = root / "sets" / RUN / "raw"
            target.mkdir(parents=True)
            @contextmanager
            def stream(args):
                yield io.BytesIO(archive([]) if "tar" in args else b"")
            with patch.object(transport, "_stream", side_effect=stream), patch.object(transport, "verify_scope", side_effect=[None, None, RuntimeError("OPENSHIFT_BACKUP_LEASE_NOT_HELD")]):
                with self.assertRaisesRegex(RuntimeError, "LEASE_NOT_HELD"):
                    transport.compose(None, None, "--profile", "ops", "run", "--rm", "backup", "mirror", "local/raw-ingestions", "/backup/sets/" + RUN + "/raw")

    def test_archive_rejects_links_extensions_and_devices_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            config = make_config(root)
            target = root / "raw"
            target.mkdir()
            for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.FIFOTYPE,
                         tarfile.XHDTYPE, tarfile.GNUTYPE_LONGNAME, tarfile.GNUTYPE_SPARSE):
                with self.subTest(kind=kind):
                    with self.assertRaisesRegex(RuntimeError, "ARCHIVE_TYPE_NOT_ALLOWED"):
                        extract_ustar(io.BytesIO(archive([("unsafe", b"", kind)])), target, config)
                    self.assertEqual(list(target.iterdir()), [])

    def test_archive_rejects_traversal_windows_aliases_and_duplicate_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            config = make_config(root)
            target = root / "raw"
            target.mkdir()
            for name in ("../outside", "/outside", "a/../../outside", "C:/outside", "a\\outside",
                         "./a//b", "CON", "NUL.bin", "file:stream", "name.", "name "):
                with self.subTest(name=name):
                    with self.assertRaisesRegex(RuntimeError, "ARCHIVE_NAME_UNSAFE"):
                        extract_ustar(io.BytesIO(archive([(name, b"", tarfile.REGTYPE)])), target, config)
                    self.assertEqual(list(target.iterdir()), [])
            with self.assertRaisesRegex(RuntimeError, "ARCHIVE_DUPLICATE_NAME"):
                extract_ustar(io.BytesIO(archive([("File", b"", tarfile.REGTYPE), ("file", b"", tarfile.REGTYPE)])), target, config)
            self.assertEqual(len(list(target.iterdir())), 1)
            self.assertFalse((root / "outside").exists())
            other = root / "case-parents"
            other.mkdir()
            with self.assertRaisesRegex(RuntimeError, "ARCHIVE_CASE_COLLISION"):
                extract_ustar(io.BytesIO(archive([("a/one", b"x", tarfile.REGTYPE), ("A/two", b"y", tarfile.REGTYPE)])), other, config)
            self.assertFalse((other / "A/two").exists())

    def test_archive_limits_include_directory_headers_and_padding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            config = make_config(root)
            target = root / "raw"
            target.mkdir()
            cases = [
                (archive([("one", b"xx", tarfile.REGTYPE)]), replace(config, max_file_bytes=1), "CONTENT_TOO_LARGE"),
                (archive([("dir/", b"", tarfile.DIRTYPE), ("other/", b"", tarfile.DIRTYPE)]), replace(config, max_files=1), "TOO_MANY_ENTRIES"),
                (archive([]), replace(config, max_archive_bytes=512), "ARCHIVE_TOO_LARGE"),
                (archive([])[:512], config, "ARCHIVE_TRUNCATED"),
                (archive([]) + b"second-archive", config, "ARCHIVE_TRAILING_DATA"),
            ]
            for data, limits, expected in cases:
                with self.subTest(expected=expected):
                    with self.assertRaisesRegex(RuntimeError, expected):
                        extract_ustar(io.BytesIO(data), target, limits)
                    self.assertEqual(list(target.iterdir()), [])

    def test_empty_directories_are_accepted_without_creating_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / "raw"
            target.mkdir()
            extract_ustar(io.BytesIO(archive([("./", b"", tarfile.DIRTYPE), ("./empty/", b"", tarfile.DIRTYPE)])), target, make_config(root))
            self.assertEqual(list(target.iterdir()), [])

    def test_metadata_output_bound_and_subprocess_errors_are_sanitized(self):
        with tempfile.TemporaryDirectory() as directory:
            config = make_config(Path(directory).resolve())
            transport = self.transport(config)
            process = Mock()
            process.stdout = io.BytesIO(b"SYNTHETIC PRIVATE OUTPUT")
            process.wait.return_value = 1
            process.poll.return_value = 1
            with patch("openshift_backup.subprocess.Popen", return_value=process) as popen:
                with self.assertRaisesRegex(RuntimeError, "COMMAND_FAILED") as error:
                    transport._read(["get", "namespace", "investment"])
                self.assertNotIn("PRIVATE", str(error.exception))
                self.assertEqual(popen.call_args.kwargs["stderr"], subprocess.DEVNULL)
                self.assertNotIn("shell", popen.call_args.kwargs)
                self.assertEqual(popen.call_args.args[0][:5], ["oc", "--context", "fixture-context", "--namespace", "investment"])


if __name__ == "__main__":
    unittest.main()
