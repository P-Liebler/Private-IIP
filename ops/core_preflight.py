"""Read-only Core V1 installation plan. Never starts or migrates a service."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from preflight import compose_environment, read_env, validate_compose, validate_config
from release_scope import active_services, evaluate_scope
from security_audit import sha256, write_new


def check(scope, config, values, mode, image_ids, free_bytes):
    errors = validate_config(values, mode) + validate_compose(config, values)
    required = active_services(scope)
    services = config.get("services", {})
    if set(required) != set(services):
        errors.append("RELEASE_SERVICE_SET_MISMATCH")
    for name, row in required.items():
        value = services.get(name, {})
        if value.get("image") != row["image"] or value.get("build"):
            errors.append("UNPINNED_OR_CHANGED_SERVICE_" + name.upper())
        if image_ids.get(row["image"]) != row["image"].split("@")[1]:
            errors.append("IMAGE_NOT_AVAILABLE_EXACT_" + name.upper())
    for name, service in services.items():
        if name != "caddy" and "edge" in service.get("networks", {}):
            errors.append("CORE_EDGE_ACCESS_FORBIDDEN_" + name.upper())
        for port in service.get("ports", []):
            if name != "caddy":
                errors.append("CORE_PRIVATE_PORT_REQUIRED_" + name.upper())
        for mount in service.get("volumes", []):
            if mount.get("type") == "volume" and mount.get("source", "").startswith("investment-intelligence_"):
                errors.append("ORIGINAL_VOLUME_FORBIDDEN")
    if free_bytes < 5 * 1024**3:
        errors.append("BACKUP_FREE_SPACE_BELOW_5_GIB")
    return sorted(set(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--scope", type=Path, default=Path("ops/releases/pr8-core-v1-scope.json"))
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--mode", choices=["STAGING", "PRODUCTION"], default="STAGING")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    values = read_env(args.env_file)
    scope = json.loads(args.scope.read_text(encoding="utf-8"))
    base = ["docker", "compose", "-f", "docker-compose.prod.yml", "-f", "ops/docker-compose.core.yml",
            "--env-file", str(args.env_file), "--profile", "ops"]
    environment = compose_environment(values, Path("docker-compose.prod.yml"))
    environment = {key: value for key, value in environment.items() if key != "CORE_S3_CONFIG"} | {
        "CORE_S3_CONFIG": values.get("CORE_S3_CONFIG", "")}
    record = {"executed": False, "target_status": "TARGET_HOST_NOT_VERIFIED",
              "release_status": "NOT_APPROVED", "scope_sha256": sha256(args.scope)}
    try:
        config = json.loads(subprocess.check_output(base + ["config", "--format", "json"],
            env=environment, stderr=subprocess.PIPE, timeout=60))
        ids = {}
        for row in active_services(scope).values():
            reference = row["image"]
            if reference in ids:
                continue
            result = subprocess.run(["docker", "image", "inspect", reference, "--format", "{{.Id}}"],
                                    capture_output=True, timeout=30, check=False)
            ids[reference] = result.stdout.decode().strip() if result.returncode == 0 else None
        backup = Path(values.get("BACKUP_ROOT", ""))
        available = shutil.disk_usage(backup).free
        errors = check(scope, config, values, args.mode, ids, available)
        identities = json.loads(Path(values.get("CORE_S3_CONFIG", "")).read_text(encoding="utf-8"))
        if not any(credential.get("accessKey") == values.get("MINIO_ACCESS_KEY")
                   and credential.get("secretKey") == values.get("MINIO_SECRET_KEY")
                   for identity in identities.get("identities", [])
                   for credential in identity.get("credentials", [])):
            errors.append("S3_APPLICATION_IDENTITY_MISMATCH")
        memory = int(subprocess.check_output(["docker", "info", "--format", "{{.MemTotal}}"],
                                            stderr=subprocess.PIPE, timeout=30))
        if memory < 8 * 1024**3:
            errors.append("DOCKER_MEMORY_BELOW_8_GIB")
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        status = evaluate_scope(scope, inventory, config)
        record.update(configuration_errors=errors, security_status=status,
                      backup_free_bytes=available,
                      docker_memory_bytes=memory,
                      private_dns_vpn_and_os_ca="TARGET_HOST_NOT_VERIFIED",
                      inventory_sha256=sha256(args.inventory),
                      # Commands are reviewable; credentials/configuration are never printed.
                      plan=[base + ["run", "--rm", "--no-deps", "storage-init"],
                            base + ["up", "--no-build", "--pull", "never", "-d", "--wait", "postgres", "minio", "caddy", "ca-export", "valkey"],
                            base + ["run", "--rm", "--no-deps", "--pull", "never", "api", "alembic", "upgrade", "head"],
                            base + ["up", "--no-build", "--pull", "never", "-d", "--wait",
                                    *[name for name, row in active_services(scope).items()
                                      if row["role"] == "runtime"]]],
                      status="TECHNICAL_CONFIGURATION_VALID" if not errors else "CONFIGURATION_BLOCKED")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        record.update(status="PREFLIGHT_INCOMPLETE", security_status="SCAN_INCOMPLETE")
    write_new(args.output, record)
    print(record["status"], record["security_status"], "NOT_APPROVED")
    return 0 if record["status"] == "TECHNICAL_CONFIGURATION_VALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
