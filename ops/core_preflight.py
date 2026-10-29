"""Read-only Core V1 installation plan. Never starts or migrates a service."""
import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
import shutil
import subprocess

from preflight import compose_environment, read_env, validate_compose, validate_config
from release_scope import active_services, evaluate_scope
from security_audit import sha256, write_new
from core_storage import measure, path_errors
from core_install_plan import configuration_hashes, startup_commands


def check(scope, config, values, mode, image_ids, free_bytes):
    errors = validate_config(values, mode) + validate_compose(config, values, core=True)
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
    project = values.get("COMPOSE_PROJECT_NAME", "")
    if project in {"investment-intelligence", "investment"}:
        errors.append("ORIGINAL_PROJECT_FORBIDDEN")
    for volume in config.get("volumes", {}).values():
        if volume.get("external") or not volume.get("name", "").startswith(project + "_"):
            errors.append("EXTERNAL_OR_NONISOLATED_VOLUME_FORBIDDEN")
    for network in config.get("networks", {}).values():
        if network.get("external") or not network.get("name", "").startswith(project + "_"):
            errors.append("EXTERNAL_OR_NONISOLATED_NETWORK_FORBIDDEN")
    if free_bytes < 5 * 1024**3:
        errors.append("BACKUP_FREE_SPACE_BELOW_5_GIB")
    return sorted(set(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--scope", type=Path, default=Path("ops/releases/pr10-core-v1-scope.json"))
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
              "release_status": "NOT_APPROVED", "scope_sha256": sha256(args.scope),
              "generated_at": datetime.now(UTC).isoformat(), "mode": args.mode,
              "environment_sha256": sha256(args.env_file)}
    stage = "COMPOSE_CONFIGURATION"
    try:
        record["configuration_file_hashes"] = configuration_hashes()
        config = json.loads(subprocess.check_output(base + ["config", "--format", "json"],
            env=environment, stderr=subprocess.PIPE, timeout=60))
        stage = "LOCAL_IMAGE_IDENTITIES"
        ids = {}
        for row in active_services(scope).values():
            reference = row["image"]
            if reference in ids:
                continue
            result = subprocess.run(["docker", "image", "inspect", reference, "--format", "{{.Id}}"],
                                    capture_output=True, timeout=30, check=False)
            ids[reference] = result.stdout.decode().strip() if result.returncode == 0 else None
        stage = "BACKUP_AND_PRIVATE_PATHS"
        backup = Path(values.get("BACKUP_ROOT", ""))
        root = Path.cwd().resolve()
        path_checks = {"backup": path_errors(backup, directory=True, root=root, mode=args.mode),
                       "environment": path_errors(args.env_file.absolute(), directory=False, root=root, mode=args.mode),
                       "s3_identity": path_errors(Path(values.get("CORE_S3_CONFIG", "")),
                                                  directory=False, root=root, mode=args.mode)}
        available = shutil.disk_usage(backup).free if backup.is_dir() else 0
        errors = check(scope, config, values, args.mode, ids, available)
        errors.extend(name.upper() + "_" + error for name, entries in path_checks.items() for error in entries)
        capacity = measure(backup) if not path_checks["backup"] else {"status": "UNAVAILABLE_UNSAFE_PATH"}
        record.update(configuration_errors=errors, backup_free_bytes=available,
                      backup_path_checks=path_checks, backup_capacity=capacity)
        stage = "S3_IDENTITY_CONFIGURATION"
        identity_bytes = Path(values.get("CORE_S3_CONFIG", "")).read_bytes()
        identities = json.loads(identity_bytes)
        record["s3_identity_sha256"] = hashlib.sha256(identity_bytes).hexdigest()
        if not any(credential.get("accessKey") == values.get("MINIO_ACCESS_KEY")
                   and credential.get("secretKey") == values.get("MINIO_SECRET_KEY")
                   for identity in identities.get("identities", [])
                   for credential in identity.get("credentials", [])):
            errors.append("S3_APPLICATION_IDENTITY_MISMATCH")
        stage = "DOCKER_MEMORY"
        memory = int(subprocess.check_output(["docker", "info", "--format", "{{.MemTotal}}"],
                                            stderr=subprocess.PIPE, timeout=60))
        if memory < 8 * 1024**3:
            errors.append("DOCKER_MEMORY_BELOW_8_GIB")
        stage = "SECURITY_INVENTORY"
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        status = evaluate_scope(scope, inventory, config)
        record.update(configuration_errors=errors, security_status=status,
                      backup_free_bytes=available,
                      backup_path_checks=path_checks, backup_capacity=capacity,
                      docker_memory_bytes=memory,
                      private_dns_vpn_and_os_ca="TARGET_HOST_NOT_VERIFIED",
                      inventory_sha256=sha256(args.inventory),
                      # Commands are reviewable; credentials/configuration are never printed.
                      plan=startup_commands(base, scope),
                      status="TECHNICAL_CONFIGURATION_VALID" if not errors else "CONFIGURATION_BLOCKED")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        record.update(status="PREFLIGHT_INCOMPLETE", security_status="SCAN_INCOMPLETE",
                      failure_stage=stage, failure_class=type(error).__name__)
    write_new(args.output, record)
    print(record["status"], record["security_status"], "NOT_APPROVED")
    return 0 if record["status"] == "TECHNICAL_CONFIGURATION_VALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
