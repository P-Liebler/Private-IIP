"""Read-only deployment checks. Passing this tool is never target-host acceptance.

Uses only Python's standard library; Compose output and secret values are not printed.
"""

from __future__ import annotations

import argparse
import base64
import ipaddress
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, separator, value = line.partition("=")
            if not separator or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
                raise ValueError("Invalid environment file")
            if key in values:
                raise ValueError("Duplicate environment key")
            values[key] = value.strip().strip("\"'")
    return values


def placeholder(value: str) -> bool:
    return not value or any(
        marker in value.lower()
        for marker in ("replace", "change-me", "changeme", "dev-only", "example", "placeholder")
    )


def validate_config(values: dict[str, str], mode: str) -> list[str]:
    errors: list[str] = []
    required = (
        "APP_DOMAIN", "VPN_BIND_ADDRESS", "POSTGRES_DB", "POSTGRES_USER",
        "POSTGRES_PASSWORD", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY",
        "TOTP_ENCRYPTION_KEY", "GRAFANA_ADMIN_USER", "GRAFANA_ADMIN_PASSWORD", "BACKUP_ROOT",
    )
    for key in required:
        if placeholder(values.get(key, "")):
            errors.append(key + "_REQUIRED_OR_PLACEHOLDER")
    domain = values.get("APP_DOMAIN", "")
    parsed = urlparse("https://" + domain)
    if (not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]{0,251}[a-zA-Z0-9]", domain)
        or parsed.hostname != domain.lower() or domain.endswith((".invalid", ".example"))
        or "." not in domain or domain.lower() == "localhost"):
        errors.append("APP_DOMAIN_INVALID")
    try:
        address = ipaddress.ip_address(values.get("VPN_BIND_ADDRESS", ""))
        if address.is_unspecified or address.is_multicast or address.is_global or address.is_link_local:
            errors.append("VPN_BIND_ADDRESS_UNSAFE")
        if mode == "PRODUCTION" and address.is_loopback:
            errors.append("VPN_TARGET_ADDRESS_NOT_CONFIGURED")
    except ValueError:
        errors.append("VPN_BIND_ADDRESS_INVALID")
    for key in ("POSTGRES_PASSWORD", "MINIO_SECRET_KEY", "GRAFANA_ADMIN_PASSWORD"):
        value = values.get(key, "")
        if len(value) < 24 or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            errors.append(key + "_UNSAFE_FORMAT")
    if len({values.get(k) for k in ("POSTGRES_PASSWORD", "MINIO_SECRET_KEY", "GRAFANA_ADMIN_PASSWORD")}) != 3:
        errors.append("SECRETS_MUST_BE_DISTINCT")
    try:
        key = values.get("TOTP_ENCRYPTION_KEY", "").encode("ascii")
        if len(key) != 44 or len(base64.b64decode(key, altchars=b"-_", validate=True)) != 32:
            raise ValueError
    except (ValueError, UnicodeError):
        errors.append("TOTP_ENCRYPTION_KEY_INVALID")
    for key in ("APP_DEBUG", "ASSISTANT_TEST_MODE"):
        if values.get(key, "false").lower() != "false":
            errors.append(key + "_FORBIDDEN")
    for key in ("DATA_COLLECTION_ENABLED", "FORWARD_SHADOW_ENABLED"):
        if values.get(key, "false").lower() != "false":
            errors.append(key + "_REQUIRES_SEPARATE_ACCEPTANCE")
    for key in ("SESSION_SECURE_COOKIE", "MINIO_SECURE"):
        if values.get(key, "true").lower() != "true":
            errors.append(key + "_REQUIRED")
    for key in ("FRONTEND_ORIGIN", "API_PUBLIC_ORIGIN"):
        if values.get(key, "https://" + domain) != "https://" + domain:
            errors.append(key + "_DOMAIN_MISMATCH")
    project = values.get("COMPOSE_PROJECT_NAME", "")
    expected = values.get("APP_ENV", "production") if mode == "DRY_RUN" else (
        "production" if mode == "PRODUCTION" else "staging"
    )
    if expected not in {"staging", "production"}:
        errors.append("SECURE_ENVIRONMENT_REQUIRED")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*-" + expected, project):
        errors.append("ENVIRONMENT_PROJECT_ISOLATION_REQUIRED")
    if values.get("APP_ENV", "production") != expected:
        errors.append("APP_ENV_MODE_MISMATCH")
    for key in ("POSTGRES_DB", "POSTGRES_USER", "MINIO_ACCESS_KEY", "GRAFANA_ADMIN_USER"):
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{2,62}", values.get(key, "")):
            errors.append(key + "_INVALID")
    if not Path(values.get("BACKUP_ROOT", "")).is_absolute():
        errors.append("BACKUP_ROOT_MUST_BE_ABSOLUTE")
    return sorted(set(errors))


def validate_compose(config: dict, values: dict[str, str], *, core: bool = False) -> list[str]:
    errors = []
    services = config.get("services", {})
    for name, service in services.items():
        for port in service.get("ports", []):
            allowed = {"caddy": {80, 443}, "prometheus": {9090}, "grafana": {3000}}
            bind = values.get("VPN_BIND_ADDRESS") if name == "caddy" else "127.0.0.1"
            try:
                if name == "caddy":
                    pairs = {(8080, 80), (8443, 443)} if core else {(80, 80), (443, 443)}
                    valid = ((int(port.get("target", 0)), int(port.get("published", 0))) in pairs
                             and port.get("protocol", "tcp") == "tcp")
                else:
                    valid = int(port.get("target", 0)) in allowed.get(name, set())
            except (ValueError, TypeError):
                valid = False
            if not valid or port.get("host_ip") != bind:
                errors.append("UNEXPECTED_PUBLISHED_PORT_" + name.upper())
        if service.get("privileged") or service.get("network_mode") == "host":
            errors.append("PRIVILEGED_SERVICE_" + name.upper())
        for volume in service.get("volumes", []):
            if "docker.sock" in volume.get("source", ""):
                errors.append("DOCKER_SOCKET_FORBIDDEN")
    for name in ("api", "worker", "scheduler"):
        env = services.get(name, {}).get("environment", {})
        if env.get("APP_ENV") != values.get("APP_ENV", "production"):
            errors.append("BACKEND_ENVIRONMENT_MISMATCH_" + name.upper())
        if str(env.get("SESSION_SECURE_COOKIE")).lower() != "true":
            errors.append("INSECURE_COOKIE_" + name.upper())
        for key in ("DATA_COLLECTION_ENABLED", "FORWARD_SHADOW_ENABLED", "ASSISTANT_TEST_MODE", "APP_DEBUG"):
            if str(env.get(key, "false")).lower() != "false":
                errors.append("UNAUTHORIZED_BACKEND_FLAG_" + key)
    return sorted(set(errors))


def compose_environment(values: dict[str, str], file: Path) -> dict[str, str]:
    keys = set(re.findall(r"\$\{([A-Z][A-Z0-9_]*)", file.read_text(encoding="utf-8")))
    return {k: v for k, v in os.environ.items() if k not in keys | values.keys()} | values


def run_json(command: list[str], environment: dict[str, str]) -> dict:
    result = subprocess.run(command, env=environment, capture_output=True, timeout=60, check=False)
    if result.returncode:
        raise RuntimeError("Command failed")
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--compose-file", type=Path, default=Path("docker-compose.prod.yml"))
    parser.add_argument("--mode", choices=("DRY_RUN", "STAGING", "PRODUCTION"), default="DRY_RUN")
    parser.add_argument("--offline", action="store_true", help="Configuration only, no Docker calls")
    args = parser.parse_args()
    errors: list[str] = []
    checks: dict[str, object] = {}
    try:
        values = read_env(args.env_file)
        errors += validate_config(values, args.mode)
        if os.name != "nt" and args.env_file.stat().st_mode & 0o077:
            errors.append("ENV_FILE_PERMISSIONS_TOO_BROAD")
        checks["secret_file_permissions"] = "OPERATOR_WINDOWS_ACL_CHECK_REQUIRED" if os.name == "nt" else "CHECKED"
        backup = Path(values.get("BACKUP_ROOT", ""))
        if not backup.is_dir():
            errors.append("BACKUP_ROOT_NOT_MOUNTED")
        else:
            checks["backup_free_bytes"] = shutil.disk_usage(backup).free
            if checks["backup_free_bytes"] < 5 * 1024**3:
                errors.append("BACKUP_FREE_SPACE_BELOW_5_GIB")
            checks["backup_access"] = "ACCESSIBLE" if os.access(backup, os.W_OK) else "UNAVAILABLE"
            if not os.access(backup, os.W_OK):
                errors.append("BACKUP_ROOT_NOT_WRITABLE")
        if not args.offline and not errors:
            # Compose gets the exact file values, not inherited ambient overrides.
            environment = compose_environment(values, args.compose_file)
            version = subprocess.run(["docker", "compose", "version", "--short"], capture_output=True, timeout=15, check=True)
            match = re.match(r"v?(\d+)\.(\d+)", version.stdout.decode().strip())
            if not match or tuple(map(int, match.groups())) < (2, 24):
                errors.append("COMPOSE_2_24_OR_LATER_REQUIRED")
            info = run_json(["docker", "info", "--format", "{{json .}}"], environment)
            engine = re.match(r"(\d+)\.", info.get("ServerVersion", ""))
            if not engine or int(engine.group(1)) < 28:
                errors.append("DOCKER_ENGINE_28_OR_LATER_REQUIRED")
            checks.update(docker_cpus=info.get("NCPU"), docker_memory_bytes=info.get("MemTotal"))
            if info.get("NCPU", 0) < 2 or info.get("MemTotal", 0) < 4 * 1024**3:
                errors.append("CORE_REQUIRES_2_CPU_4_GIB")
            config = run_json(["docker", "compose", "--env-file", str(args.env_file), "-f", str(args.compose_file), "config", "--format", "json"], environment)
            errors += validate_compose(config, values)
        checks["target_acceptance"] = "NOT_VERIFIED"
        checks["operator_required"] = ["VPN_DNS_OUTSIDE_VPN", "CLIENT_TLS_TRUST", "CLOCK_SYNC", "INDEPENDENT_ENCRYPTED_BACKUP", "DAILY_SCHEDULE", "SECRET_RECOVERY", "ALERT_DELIVERY", "IMAGE_SECURITY_AUDIT", "MIGRATION_REVIEW"]
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        errors.append("PREFLIGHT_INPUT_OR_DOCKER_CHECK_FAILED")
    print(json.dumps({"mode": args.mode, "scope": "CONFIGURATION_ONLY" if args.offline else "LOCAL_PREFLIGHT", "passed": not errors, "errors": sorted(set(errors)), "checks": checks}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
