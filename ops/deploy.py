"""Explicit deployment orchestration; defaults to printing a plan without changes."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import re
import tempfile
from pathlib import Path

from preflight import compose_environment, read_env, validate_config
from release_manifest import validate_manifest


def reviewed_images(manifest, root):
    validate_manifest(manifest, root)
    if (manifest.get("security_status") != "SECURITY_REMEDIATED"
            or manifest.get("target_status") != "TARGET_HOST_VERIFIED"
            or manifest.get("release_status") != "OPERATOR_APPROVED"
            or not manifest.get("operator_approval_reference")):
        raise ValueError("RELEASE_GATES_OPEN")
    images = manifest.get("service_image_digests", {})
    required = {"api", "worker", "scheduler", "ml-worker", "web", "postgres", "valkey",
                "minio", "backup", "caddy", "ca-export", "prometheus", "grafana", "mlflow", "ollama"}
    if set(images) != required or any(
        not re.fullmatch(r"[A-Za-z0-9_./:-]+@sha256:[0-9a-f]{64}", ref) for ref in images.values()
    ):
        raise ValueError("RELEASE_IMAGE_CONTRACT_INCOMPLETE")
    aliases = {"api": "backend", "worker": "backend", "scheduler": "backend", "ml-worker": "backend",
               "ca-export": "caddy", "backup": "minio"}
    audited = manifest.get("image_digests", {})
    for service, reference in images.items():
        component = aliases.get(service, service)
        if reference.split("@", 1)[1] != audited.get(component, {}).get("image_id"):
            raise ValueError("RELEASE_SERVICE_DIGEST_MISMATCH")
    reference = manifest.get("inventory_reference")
    if not reference or reference not in manifest["artifact_hashes"]:
        raise ValueError("RELEASE_INVENTORY_NOT_BOUND")
    inventory = json.loads((root / reference).read_text(encoding="utf-8"))
    if inventory.get("security_status") != manifest["security_status"]:
        raise ValueError("RELEASE_SECURITY_STATUS_MISMATCH")
    if {item["component"]: item["image_id"] for item in inventory["images"]} != {
        key: item["image_id"] for key, item in audited.items()
    }:
        raise ValueError("RELEASE_INVENTORY_DIGEST_MISMATCH")
    return images


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "deploy", "rollback-prep"))
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--mode", choices=("DRY_RUN", "STAGING", "PRODUCTION"), default="DRY_RUN")
    parser.add_argument("--operator-authorized", action="store_true")
    parser.add_argument("--migrations-reviewed", action="store_true")
    parser.add_argument("--release-manifest", type=Path)
    args = parser.parse_args()
    base = ["docker", "compose", "-f", "docker-compose.prod.yml", "--env-file", str(args.env_file)]
    root = read_env(args.env_file).get("BACKUP_ROOT", "")
    backup = [sys.executable, "ops/backup.py", "--compose-file", "docker-compose.prod.yml", "--env-file", str(args.env_file), "--root", root]
    preflight = [sys.executable, "ops/preflight.py", "--env-file", str(args.env_file), "--mode", args.mode]
    plans = {
        "status": [base + ["ps", "--format", "json"]],
        "rollback-prep": [preflight, backup],
        "deploy": [preflight, backup, base + ["build"], base + ["run", "--rm", "api", "alembic", "upgrade", "head"], base + ["up", "-d", "--wait"]],
    }
    if args.mode == "DRY_RUN":
        print(json.dumps({"executed": False, "plan": plans[args.action], "operator_acceptance": "NOT_VERIFIED"}, indent=2))
        return 0
    if validate_config(read_env(args.env_file), args.mode):
        parser.error("Configuration failed preflight; inspect ops/preflight.py")
    if args.action != "status" and (not args.operator_authorized or not args.migrations_reviewed):
        parser.error("Changing deployment requires explicit operator authorization and migration review")
    if args.action == "deploy" and args.mode == "PRODUCTION":
        if not args.release_manifest:
            parser.error("Production deployment requires an approved immutable release manifest")
        try:
            manifest = json.loads(args.release_manifest.read_text(encoding="utf-8"))
            images = reviewed_images(manifest, Path.cwd().resolve())
        except (OSError, ValueError, KeyError, TypeError):
            parser.error("Release evidence is invalid or security/target/operator gates remain open")
        # Audited images must never be rebuilt by deployment. Compose accepts JSON overrides.
        with tempfile.TemporaryDirectory(prefix="iip-reviewed-images-") as folder:
            override = Path(folder) / "images.json"
            override.write_text(json.dumps({"services": {name: {"image": ref} for name, ref in images.items()}}), encoding="utf-8")
            frozen = base + ["-f", str(override)]
            plans["deploy"] = [preflight, backup,
                               frozen + ["run", "--no-deps", "--pull", "never", "--rm", "api", "alembic", "upgrade", "head"],
                               frozen + ["up", "--no-build", "-d", "--wait"]]
            return execute(plans[args.action], args, read_env(args.env_file))
    return execute(plans[args.action], args, read_env(args.env_file))


def execute(commands, args, values):
    for command in commands:
        result = subprocess.run(command, env=compose_environment(values, Path("docker-compose.prod.yml")), capture_output=True, check=False)
        if result.returncode:
            # Child output can contain interpolated secrets; do not echo it.
            print("Operation failed; inspect protected service logs", file=sys.stderr)
            return 1
        if args.action == "status":
            print(result.stdout.decode())
    print("Technical steps completed; run verify_production.py and operator checklist before acceptance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
