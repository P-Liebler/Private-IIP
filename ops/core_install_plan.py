"""Guided Core installation/rollback plan. This tool has no apply/deploy operation."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

from preflight import read_env
from release_manifest import validate_manifest
from release_scope import active_services
from security_audit import sha256, write_new


def configuration_hashes():
    return {name: sha256(Path(name)) for name in (
        "docker-compose.prod.yml", "ops/docker-compose.core.yml", "ops/caddy/Core.Caddyfile",
        "ops/prometheus/prometheus.yml", "ops/prometheus/alerts.yml",
    )}


def readiness(preflight, scope_path, inventory_path, env_path, mode, *, now=None):
    errors = []
    if preflight.get("executed") is not False or preflight.get("status") != "TECHNICAL_CONFIGURATION_VALID":
        errors.append("PREFLIGHT_NOT_VALID")
    for key, path in (("scope_sha256", scope_path), ("inventory_sha256", inventory_path),
                      ("environment_sha256", env_path)):
        if preflight.get(key) != sha256(path):
            errors.append("PREFLIGHT_INPUT_CHANGED_" + key.upper())
    if preflight.get("mode") != mode:
        errors.append("PREFLIGHT_MODE_MISMATCH")
    if preflight.get("configuration_file_hashes") != configuration_hashes():
        errors.append("PREFLIGHT_CONFIGURATION_CHANGED_OR_NOT_BOUND")
    try:
        identity = Path(read_env(env_path)["CORE_S3_CONFIG"])
        if preflight.get("s3_identity_sha256") != sha256(identity):
            errors.append("PREFLIGHT_S3_IDENTITY_CHANGED_OR_NOT_BOUND")
    except (OSError, ValueError, KeyError, TypeError):
        errors.append("PREFLIGHT_S3_IDENTITY_UNAVAILABLE")
    try:
        stamp = datetime.fromisoformat(preflight["generated_at"])
        if stamp.tzinfo is None or not timedelta(0) <= (now or datetime.now(UTC)) - stamp <= timedelta(hours=24):
            errors.append("PREFLIGHT_EXPIRED_OR_FUTURE")
    except (ValueError, KeyError, TypeError):
        errors.append("PREFLIGHT_TIME_MISSING")
    return errors


def startup_commands(base, scope):
    # ca-export is a successful one-shot dependency, never a healthy daemon.
    runtime = [name for name, row in active_services(scope).items()
               if row["role"] == "runtime" and name != "ca-export"]
    return [
        base + ["run", "--rm", "--no-deps", "--pull", "never", "storage-init"],
        base + ["up", "--no-build", "--pull", "never", "-d", "--wait", "postgres", "minio", "caddy", "valkey"],
        base + ["up", "--no-build", "--pull", "never", "--no-deps", "--exit-code-from", "ca-export", "ca-export"],
        base + ["run", "--rm", "--no-deps", "--pull", "never", "api", "alembic", "upgrade", "head"],
        base + ["up", "--no-build", "--pull", "never", "-d", "--wait", *runtime],
    ]


def plan(scope, env_path):
    base = ["docker", "compose", "-f", "docker-compose.prod.yml", "-f", "ops/docker-compose.core.yml",
            "--env-file", str(env_path), "--profile", "ops"]
    return {
        "status": base + ["ps", "--format", "json"],
        "after_separate_approval_only": startup_commands(base, scope),
        "rollback": ["Stop new writes; preserve volumes and new raw originals.",
                     "Create and verify a fresh backup with the existing ops/backup.py engine.",
                     "Reconcile post-cutover ledger/object deltas before choosing a recovery set.",
                     "Run ops/restore_verify.py in its random isolated project and verify immutable history.",
                     "Require separate operator cutover approval; never down -v, downgrade a volume, or discard new writes."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--mode", choices=["STAGING", "PRODUCTION"], default="STAGING")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = {"executed": False, "release_status": "NOT_APPROVED", "target_status": "TARGET_HOST_NOT_VERIFIED",
              "installer_operation": "READ_ONLY_PLAN_NO_APPLY_IMPLEMENTED", "generated_at": datetime.now(UTC).isoformat()}
    try:
        scope = json.loads(args.scope.read_text(encoding="utf-8"))
        preflight = json.loads(args.preflight.read_text(encoding="utf-8"))
        values = read_env(args.env_file)
        errors = readiness(preflight, args.scope, args.inventory, args.env_file, args.mode)
        record.update(project=values.get("COMPOSE_PROJECT_NAME"), mode=args.mode,
                      scope_sha256=sha256(args.scope), plan=plan(scope, args.env_file), configuration_errors=errors)
        manifest_status = "MANIFEST_NOT_PROVIDED"
        if args.manifest:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            try:
                validate_manifest(manifest, Path.cwd().resolve())
                expected = {name: row["image"] for name, row in active_services(scope).items()}
                if (manifest.get("release_scope_sha256") != sha256(args.scope)
                        or manifest.get("service_image_digests") != expected
                        or manifest.get("artifact_hashes", {}).get(args.inventory.resolve().relative_to(Path.cwd()).as_posix()) != sha256(args.inventory)):
                    raise ValueError("MANIFEST_SCOPE_OR_INVENTORY_MISMATCH")
                manifest_status = "MANIFEST_BYTES_VALID_APPROVALS_SEPARATELY_REQUIRED"
            except ValueError:
                manifest_status = "MANIFEST_INVALID_CHANGED_OR_SCOPE_MISMATCH"
        record.update(manifest_status=manifest_status,
                      status="CONFIGURATION_PLAN_READY" if not errors else "CONFIGURATION_BLOCKED",
                      required_approval_evidence=["SECURITY_REMEDIATED", "TARGET_HOST_VERIFIED", "OPERATOR_APPROVED",
                                                  "INDEPENDENT_ENCRYPTED_RECOVERY_VERIFIED", "MIGRATION_AND_ROLLBACK_REVIEW"],
                      production_start="NOT_IMPLEMENTED_NEVER_AUTHORIZED_BY_THIS_PLAN")
    except (OSError, ValueError, KeyError, TypeError):
        record.update(status="PLAN_INPUT_INVALID", configuration_errors=["PROTECTED_INPUT_OR_EVIDENCE_INVALID"])
    write_new(args.output, record)
    print(record["status"], "NOT_APPROVED", "NO_SERVICES_STARTED")
    return 0 if record["status"] == "CONFIGURATION_PLAN_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
