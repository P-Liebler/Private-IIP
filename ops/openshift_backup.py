"""Optional oc transport for backup.compose; the existing backup engine owns artifacts.

This module never creates, starts, scales, locks, restores or approves anything.
An operator must provide running, digest-bound PostgreSQL and backup-agent pods,
quiesce every writer, and hold/renew an external Lease for the entire operation.
The backup-agent has a private staging PVC at /backup, writable /tmp, Secret-backed
MC_HOST_local=https://..., and the injected service CA at /trusted-ca/root.crt.
Its pinned image must provide sh, env, tar and /usr/local/bin/iip-mc. No credentials
are configuration inputs or read back from Kubernetes. Only the three calls used
by backup.py are accepted. Restore remains a separate, isolated operator action.

Use OpenShiftBackupTransport.from_file(config, engine_root=root).compose as an
injected replacement for backup.compose, after checking root and before engine
writes. Configuration/receipt examples are described by Config.from_dict and
operator_scope(); neither is a deployment or security approval. The default
destination verifier is the existing independent encrypted destination verifier.
The Windows host contract deliberately fails closed on unsupported destinations.

oc exec has no atomic Pod-UID precondition. External operator exclusivity and
checks before/after each command are required; a replacement/restart invalidates
the run. Cluster/network/CSI functionality is not established by offline tests.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import threading
from typing import BinaryIO, Callable, Iterator


CONTRACT = "OPENSHIFT_BACKUP_TRANSPORT_V1"
PG_DUMP = 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc'
NAME = re.compile(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?\Z")
UID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
IMAGE = re.compile(r"[A-Za-z0-9_./:-]+@sha256:[0-9a-f]{64}\Z")
RUN = re.compile(r"[0-9]{8}T[0-9]{6}Z-[0-9]{1,12}\Z")
SELECTOR = re.compile(r"[a-z0-9./_-]+=[A-Za-z0-9_.-]+(?:,[a-z0-9./_-]+=[A-Za-z0-9_.-]+){0,7}\Z")
RESERVED = re.compile(r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?\Z", re.I)

# The script is constant; source/destination are separate argv entries, never
# interpolated into shell code. Secret values are only examined inside the pod.
MIRROR = '''case "$MC_HOST_local" in https://*[@]*) ;; *) exit 71 ;; esac
test "${MC_HOST_local##*@}" = "$4"
test -d /backup && test ! -L /backup
if test -e /backup/sets; then test -d /backup/sets && test ! -L /backup/sets; fi
test ! -e "$3" && test ! -L "$3"
mkdir -p /backup/sets
mkdir "$3"
exec env S3_CA_REQUIRED=true MC_CONFIG_DIR=/tmp/.mc /usr/local/bin/iip-mc --quiet mirror "$1" "$2"
'''


def fail(code: str) -> None:
    # Never expose subprocess output, JSON inputs or credentials in exceptions.
    raise RuntimeError("OPENSHIFT_BACKUP_" + code)


def _stamp(value: object) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if result.tzinfo is None:
            fail("TIME_INVALID")
        return result.astimezone(UTC)
    except (ValueError, TypeError):
        fail("TIME_INVALID")


def _plain_path(path: Path, *, directory: bool = True) -> Path:
    """Reject aliases/reparse points rather than following them into host files."""
    if not path.is_absolute() or ".." in path.parts:
        fail("ROOT_NOT_ABSOLUTE")
    for parent in (path, *path.parents):
        info = parent.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            fail("LOCAL_PATH_ALIAS")
    if directory and not path.is_dir():
        fail("LOCAL_DIRECTORY_REQUIRED")
    return path.resolve(strict=True)


@dataclass(frozen=True)
class Pod:
    name: str
    uid: str
    container: str
    image: str
    image_id: str
    container_id: str

    def validate(self) -> None:
        if (not NAME.fullmatch(self.name) or not NAME.fullmatch(self.container)
                or not UID.fullmatch(self.uid) or not IMAGE.fullmatch(self.image)
                or not re.search(r"(?:@|://|^)sha256:[0-9a-f]{64}\Z", self.image_id)
                or not re.fullmatch(r"[a-z0-9-]+://[a-zA-Z0-9_.:-]{1,256}", self.container_id)):
            fail("POD_BINDING_INVALID")


@dataclass(frozen=True)
class Config:
    context: str
    namespace: str
    namespace_uid: str
    session: str
    lease_name: str
    lease_uid: str
    writer_selector: str
    writer_deployments: dict[str, str]
    postgres: Pod
    backup_agent: Pod
    database: str
    bucket: str
    root: Path
    operator_receipt: Path
    operator_receipt_sha256: str
    destination_policy: Path
    destination_policy_sha256: str
    command_timeout: int = 1800
    max_files: int = 100000
    max_file_bytes: int = 1024 ** 3
    max_total_bytes: int = 16 * 1024 ** 3
    max_archive_bytes: int = 18 * 1024 ** 3
    max_dump_bytes: int = 16 * 1024 ** 3

    @classmethod
    def from_dict(cls, value: dict) -> Config:
        try:
            if not isinstance(value, dict) or value.get("contract") != CONTRACT:
                fail("CONFIG_CONTRACT_INVALID")
            fields = {key: item for key, item in value.items() if key != "contract"}
            for key in ("root", "operator_receipt", "destination_policy"):
                fields[key] = Path(fields[key])
            for key in ("postgres", "backup_agent"):
                fields[key] = Pod(**fields[key])
            return cls(**fields)
        except (KeyError, ValueError, TypeError):
            fail("CONFIG_INVALID")

    def validate(self, engine_root: Path) -> None:
        if (not re.fullmatch(r"[A-Za-z0-9_.:/@-]{1,253}", self.context)
                or self.context.startswith("-") or not NAME.fullmatch(self.namespace)
                or not UID.fullmatch(self.namespace_uid) or not UID.fullmatch(self.session)
                or not NAME.fullmatch(self.lease_name) or not UID.fullmatch(self.lease_uid)
                or not SELECTOR.fullmatch(self.writer_selector)
                or set(self.writer_deployments) - {"api", "web", "worker", "scheduler", "ml-worker"}
                or not {"api", "web", "worker", "scheduler"} <= set(self.writer_deployments)
                or len(set(self.writer_deployments.values())) != len(self.writer_deployments)
                or any(not NAME.fullmatch(name) for name in self.writer_deployments.values())
                or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", self.database)
                or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", self.bucket)
                or not DIGEST.fullmatch(self.operator_receipt_sha256)
                or not DIGEST.fullmatch(self.destination_policy_sha256)):
            fail("CONFIG_INVALID")
        for number in (self.command_timeout, self.max_files, self.max_file_bytes,
                       self.max_total_bytes, self.max_archive_bytes, self.max_dump_bytes):
            if type(number) is not int or number <= 0:
                fail("LIMIT_INVALID")
        if self.command_timeout > 86400 or self.max_files > 1000000:
            fail("LIMIT_INVALID")
        self.postgres.validate()
        self.backup_agent.validate()
        if self.postgres.name == self.backup_agent.name:
            fail("DISTINCT_PODS_REQUIRED")
        if _plain_path(self.root) != _plain_path(engine_root):
            fail("ROOT_MISMATCH")

    def operator_scope(self) -> dict:
        """Exact non-secret receipt binding; no inferred approval fields."""
        return {"context": self.context, "namespace": self.namespace,
                "namespace_uid": self.namespace_uid, "session": self.session,
                "lease_name": self.lease_name, "lease_uid": self.lease_uid,
                "writer_selector": self.writer_selector,
                "writer_deployments": self.writer_deployments,
                "postgres": vars(self.postgres), "backup_agent": vars(self.backup_agent),
                "database": self.database, "bucket": self.bucket,
                "s3_endpoint": "caddy." + self.namespace + ".svc:9002",
                "root": str(self.root), "destination_policy_sha256": self.destination_policy_sha256,
                "transfer_limits": {key: getattr(self, key) for key in
                                    ("command_timeout", "max_files", "max_file_bytes", "max_total_bytes",
                                     "max_archive_bytes", "max_dump_bytes")}}


def _reviewed_file(path: Path, digest: str) -> bytes:
    _plain_path(path, directory=False)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
        fail("REVIEW_FILE_INVALID")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        fail("REVIEW_FILE_CHANGED")
    return data


def verify_reviews(config: Config, now: datetime) -> None:
    try:
        receipt = json.loads(_reviewed_file(config.operator_receipt, config.operator_receipt_sha256))
        _reviewed_file(config.destination_policy, config.destination_policy_sha256)
        start, end = _stamp(receipt["reviewed_at"]), _stamp(receipt["expires_at"])
        if (receipt.get("contract") != "OPENSHIFT_BACKUP_OPERATOR_SCOPE_V1"
                or receipt.get("status") != "OPERATOR_REVIEWED_BACKUP_SCOPE"
                or not isinstance(receipt.get("operator"), str) or not receipt["operator"].strip()
                or receipt.get("scope") != config.operator_scope()
                or not start <= now < end or end - start > timedelta(hours=24)):
            fail("OPERATOR_SCOPE_NOT_VERIFIED")
        from backup_destination import verify
        verify(config.destination_policy, config.root)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        fail("OPERATOR_OR_DESTINATION_NOT_VERIFIED")


class OpenShiftBackupTransport:
    def __init__(self, config: Config, *, engine_root: Path,
                 verify_preconditions: Callable[[Config, datetime], None] = verify_reviews,
                 now: Callable[[], datetime] = lambda: datetime.now(UTC)):
        config.validate(engine_root)
        self.config, self.engine_root = config, engine_root
        self._reviews, self._now = verify_preconditions, now
        self._database_checked = False
        self._dump_run: str | None = None
        self._dump_completed = False
        # Constructor performs every prerequisite check before engine writes.
        self.verify_scope()

    @classmethod
    def from_file(cls, path: Path, *, engine_root: Path) -> OpenShiftBackupTransport:
        try:
            _plain_path(path, directory=False)
            if path.stat().st_size > 65536:
                fail("CONFIG_TOO_LARGE")
            config = Config.from_dict(json.loads(path.read_bytes()))
            return cls(config, engine_root=engine_root)
        except (OSError, ValueError, TypeError):
            fail("CONFIG_UNAVAILABLE")

    def _base(self) -> list[str]:
        return ["oc", "--context", self.config.context, "--namespace", self.config.namespace,
                "--request-timeout=30s"]

    @contextmanager
    def _stream(self, args: list[str]) -> Iterator[BinaryIO]:
        process = None
        timer = None
        expired = threading.Event()
        try:
            process = subprocess.Popen(self._base() + args, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            def timeout() -> None:
                expired.set()
                try:
                    process.kill()
                except OSError:
                    pass
            timer = threading.Timer(self.config.command_timeout, timeout)
            timer.daemon = True
            timer.start()
            yield process.stdout
            if process.wait(timeout=10) or expired.is_set():
                fail("COMMAND_FAILED")
        except (OSError, subprocess.SubprocessError):
            fail("COMMAND_FAILED")
        finally:
            if timer is not None:
                timer.cancel()
            if process is not None:
                if process.poll() is None:
                    process.kill()
                process.wait()
                if process.stdout is not None:
                    process.stdout.close()

    def _read(self, args: list[str], limit: int = 65536) -> bytes:
        with self._stream(args) as stream:
            result = stream.read(limit + 1)
            if len(result) > limit:
                fail("METADATA_TOO_LARGE")
            return result

    def _get(self, kind: str, name: str | None, template: str, *, selector: str | None = None) -> str:
        args = ["get", kind]
        if name is not None:
            args.append(name)
        if selector is not None:
            args += ["--selector", selector]
        args += ["--output=jsonpath=" + template]
        try:
            return self._read(args).decode("utf-8", errors="strict")
        except UnicodeError:
            fail("METADATA_INVALID")

    def _pod(self, pod: Pod) -> None:
        fields = [".metadata.namespace", ".metadata.uid", ".status.phase",
                  f'.spec.containers[?(@.name=="{pod.container}")].image',
                  *[f'.status.containerStatuses[?(@.name=="{pod.container}")].{field}'
                    for field in ("imageID", "containerID", "ready", "state.running.startedAt")]]
        template = '{"\\n"}'.join("{" + field + "}" for field in fields)
        values = self._get("pod", pod.name, template).splitlines()
        expected = [self.config.namespace, pod.uid, "Running", pod.image, pod.image_id,
                    pod.container_id, "true"]
        if len(values) != 8 or values[:7] != expected or not values[7]:
            fail("POD_IDENTITY_OR_STATE_CHANGED")

    def verify_scope(self) -> None:
        config = self.config
        config.validate(self.engine_root)
        now = self._now()
        self._reviews(config, now)
        if self._get("namespace", config.namespace, "{.metadata.uid}") != config.namespace_uid:
            fail("NAMESPACE_CHANGED")
        lease = self._get("lease", config.lease_name,
                          '{.metadata.uid}{"\\n"}{.spec.holderIdentity}{"\\n"}'
                          '{.spec.renewTime}{"\\n"}{.spec.leaseDurationSeconds}').splitlines()
        try:
            if len(lease) != 4:
                fail("LEASE_NOT_HELD")
            renewal, ttl = _stamp(lease[2]), int(lease[3])
            if (lease[:2] != [config.lease_uid, config.session] or not 1 <= ttl <= 3600
                    or not renewal <= now < renewal + timedelta(seconds=ttl)):
                fail("LEASE_NOT_HELD")
        except (ValueError, TypeError):
            fail("LEASE_NOT_HELD")
        rows = self._get("deployments", None,
                         '{range .items[*]}{.metadata.name}{"\\t"}{.spec.replicas}{"\\t"}'
                         '{.status.replicas}{"\\t"}{.status.readyReplicas}{"\\t"}'
                         '{.status.updatedReplicas}{"\\n"}{end}', selector=config.writer_selector)
        writers = {}
        for row in rows.splitlines():
            values = row.split("\t")
            if (len(values) != 5 or values[0] in writers or values[1] != "0"
                    or any(value not in {"", "0"} for value in values[2:])):
                fail("WRITERS_NOT_QUIESCED")
            writers[values[0]] = True
        if set(writers) != set(config.writer_deployments.values()):
            fail("WRITER_SCOPE_CHANGED")
        rows = self._get("pods", None,
                         '{range .items[*]}{.metadata.name}{"\\t"}{.status.phase}{"\\n"}{end}',
                         selector=config.writer_selector)
        if any(len(row.split("\t")) != 2 or row.split("\t")[1] not in {"Succeeded", "Failed"}
               for row in rows.splitlines()):
            fail("WRITER_PODS_ACTIVE")
        # Migration/manual Jobs are outside the application writer selector.
        # Refuse every non-suspended, unfinished Job in this dedicated namespace.
        jobs = self._get("jobs", None,
                         '{range .items[*]}{.metadata.name}{"\\t"}{.spec.suspend}{"\\t"}'
                         '{.status.active}{"\\t"}{.status.conditions[?(@.type=="Complete")].status}'
                         '{"\\n"}{end}')
        for row in jobs.splitlines():
            fields = row.split("\t")
            if (len(fields) != 4 or fields[2] not in {"", "0"}
                    or fields[1] != "true" and fields[3] != "True"):
                fail("NAMESPACE_JOBS_NOT_QUIESCED")
        self._pod(config.postgres)
        self._pod(config.backup_agent)

    @staticmethod
    def _exec(pod: Pod, command: list[str]) -> list[str]:
        return ["exec", pod.name, "--container", pod.container, "--", *command]

    def _run_path(self, run: str, leaf: str) -> Path:
        if not RUN.fullmatch(run):
            fail("RUN_INVALID")
        try:
            datetime.strptime(run.split("-")[0], "%Y%m%dT%H%M%SZ")
        except ValueError:
            fail("RUN_INVALID")
        path = self.config.root / "sets" / run / leaf
        _plain_path(path, directory=leaf == "raw")
        if not path.resolve().is_relative_to(self.config.root.resolve()):
            fail("LOCAL_PATH_ESCAPED")
        return path

    def compose(self, file, env_file, *args: str, stdout=None) -> bytes | None:
        """Match backup.py's transport interface; never read compose/env files."""
        config = self.config
        if args == ("exec", "-T", "postgres", "printenv", "POSTGRES_DB"):
            if stdout != subprocess.PIPE:
                fail("CALL_NOT_ALLOWED")
            self.verify_scope()
            value = self._read(self._exec(config.postgres, ["printenv", "POSTGRES_DB"]), 128)
            if value != (config.database + "\n").encode():
                fail("DATABASE_MISMATCH")
            self.verify_scope()
            self._database_checked = True
            return value
        if args == ("exec", "-T", "postgres", "sh", "-c", PG_DUMP):
            if not self._database_checked or stdout is None or not hasattr(stdout, "name"):
                fail("CALL_NOT_ALLOWED")
            path = Path(stdout.name)
            run = path.parent.name
            if self._dump_run is not None or path != self._run_path(run, "postgres.dump"):
                fail("DUMP_TARGET_INVALID")
            if not stat.S_ISREG(os.fstat(stdout.fileno()).st_mode) or stdout.tell() != 0:
                fail("DUMP_TARGET_INVALID")
            self.verify_scope()
            self._dump_run = run
            total = 0
            with self._stream(self._exec(config.postgres, ["sh", "-c", PG_DUMP])) as stream:
                while chunk := stream.read(1024 * 1024):
                    if not total and not chunk.startswith(b"PGDMP"):
                        fail("DUMP_FORMAT_INVALID")
                    total += len(chunk)
                    if total > config.max_dump_bytes:
                        fail("DUMP_TOO_LARGE")
                    stdout.write(chunk)
            if not total:
                fail("DUMP_EMPTY")
            self.verify_scope()
            self._dump_completed = True
            return None
        if len(args) == 8 and args[:6] == ("--profile", "ops", "run", "--rm", "backup", "mirror"):
            source, remote = args[6:]
            prefix = "/backup/sets/"
            if (stdout is not None or source != "local/" + config.bucket
                    or not remote.startswith(prefix) or not remote.endswith("/raw")):
                fail("CALL_NOT_ALLOWED")
            run = remote[len(prefix):-len("/raw")]
            target = self._run_path(run, "raw")
            if not self._dump_completed or run != self._dump_run or any(target.iterdir()):
                fail("RUN_NOT_READY")
            self.verify_scope()
            self._read(self._exec(config.backup_agent,
                                 ["sh", "-ec", MIRROR, "iip-backup-mirror", source, remote,
                                  prefix + run, "caddy." + config.namespace + ".svc:9002"]))
            self.verify_scope()
            with self._stream(self._exec(config.backup_agent, ["tar", "-c", "-C", remote, "."])) as stream:
                extract_ustar(stream, target, config)
            self.verify_scope()
            return None
        fail("CALL_NOT_ALLOWED")


def extract_ustar(stream: BinaryIO, destination: Path, limits: Config) -> None:
    """Bounded uncompressed USTAR subset; never use tarfile.extract/extractall.

    POSIX USTAR and the pinned BusyBox basic GNU header are supported. GNU/PAX
    extensions, compression, sparse files and links fail closed. Header
    and content bytes are counted before allocation. Directory headers are
    allowed and counted but never applied as filesystem metadata. New files are
    created exclusively; partial failed runs remain failed engine artifacts.
    """
    _plain_path(destination)
    if any(destination.iterdir()):
        fail("EXTRACTION_TARGET_NOT_EMPTY")
    count = total = consumed = 0
    seen: set[str] = set()
    component_spellings: dict[str, str] = {}

    def read(size: int) -> bytes:
        nonlocal consumed
        if consumed + size > limits.max_archive_bytes:
            fail("ARCHIVE_TOO_LARGE")
        parts = []
        remaining = size
        while remaining:
            chunk = stream.read(min(remaining, 1024 * 1024))
            if not chunk:
                fail("ARCHIVE_TRUNCATED")
            parts.append(chunk)
            remaining -= len(chunk)
            consumed += len(chunk)
        return b"".join(parts)

    def octal(raw: bytes) -> int:
        cleaned = raw.strip(b" \0")
        if not cleaned or not re.fullmatch(b"[0-7]+", cleaned):
            fail("ARCHIVE_NUMBER_INVALID")
        return int(cleaned, 8)

    def string(raw: bytes) -> str:
        value, _, padding = raw.partition(b"\0")
        if any(padding):
            fail("ARCHIVE_NAME_INVALID")
        try:
            return value.decode("utf-8", "strict")
        except UnicodeError:
            fail("ARCHIVE_NAME_INVALID")

    while True:
        block = read(512)
        if block == bytes(512):
            if read(512) != bytes(512):
                fail("ARCHIVE_TERMINATOR_INVALID")
            # Reject concatenated archives and nonzero material after EOF.
            while chunk := stream.read(65536):
                consumed += len(chunk)
                if consumed > limits.max_archive_bytes or any(chunk):
                    fail("ARCHIVE_TRAILING_DATA")
            return
        count += 1
        if count > limits.max_files:
            fail("ARCHIVE_TOO_MANY_ENTRIES")
        posix = block[257:265] == b"ustar\x0000"
        busybox_basic = block[257:265] == b"ustar  \x00" and not any(block[345:500])
        if (not (posix or busybox_basic)
                or sum(block[:148]) + 8 * 32 + sum(block[156:]) != octal(block[148:156])):
            fail("ARCHIVE_HEADER_INVALID")
        kind, size = block[156:157], octal(block[124:136])
        if kind not in {b"0", b"\0", b"5"} or (kind == b"5" and size):
            fail("ARCHIVE_TYPE_NOT_ALLOWED")
        name, prefix = string(block[:100]), string(block[345:500])
        name = (prefix + "/" if prefix else "") + name
        if name in {".", "./"} and kind == b"5":
            normalized = "."
            parts = ()
        else:
            if name.startswith("./"):
                name = name[2:]
            if kind == b"5" and name.endswith("/"):
                name = name[:-1]
            parts = tuple(name.split("/"))
            if (not name or PurePosixPath(name).is_absolute()
                    or any(part in {"", ".", ".."} or part.endswith((".", " "))
                           or RESERVED.fullmatch(part)
                           or any(ord(c) < 32 or c in '<>:"\\|?*' for c in part)
                           for part in parts)):
                fail("ARCHIVE_NAME_UNSAFE")
            normalized = "/".join(parts).casefold()
        if normalized in seen:
            fail("ARCHIVE_DUPLICATE_NAME")
        seen.add(normalized)
        # Windows folds directory case even when different leaf names would
        # avoid a full-path collision. Never silently change an S3 object key.
        for index in range(1, len(parts) + 1):
            spelling = "/".join(parts[:index])
            previous = component_spellings.setdefault(spelling.casefold(), spelling)
            if previous != spelling:
                fail("ARCHIVE_CASE_COLLISION")
        if kind == b"5":
            continue
        total += size
        if size > limits.max_file_bytes or total > limits.max_total_bytes:
            fail("ARCHIVE_CONTENT_TOO_LARGE")
        path = destination.joinpath(*parts)
        for parent in reversed(path.parents):
            if parent == destination or destination in parent.parents:
                if not parent.exists():
                    parent.mkdir(mode=0o700)
                _plain_path(parent)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
        with os.fdopen(descriptor, "wb") as output:
            remaining = size
            while remaining:
                chunk = read(min(remaining, 1024 * 1024))
                output.write(chunk)
                remaining -= len(chunk)
        padding = (-size) % 512
        if padding and any(read(padding)):
            fail("ARCHIVE_PADDING_INVALID")
