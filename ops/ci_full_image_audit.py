"""Build/pull and scan all configured production images without starting services."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from preflight import compose_environment, read_env
from release_scope import active_services
from security_audit import sha256, write_new
import hashlib

CONFIGURATION_FILES = ("docker-compose.prod.yml", "ops/docker-compose.core.yml", "ops/caddy/Core.Caddyfile",
                       "ops/prometheus/prometheus.yml", "ops/prometheus/alerts.yml")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--scanner", type=Path, required=True)
    parser.add_argument("--scanner-sha256", required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--core-only", action="store_true")
    selection.add_argument("--release-scope", type=Path,
                           help="Scan exact Core runtime/recovery images; never rebuild or substitute them")
    args = parser.parse_args()
    compose = Path("docker-compose.prod.yml")
    env = compose_environment(read_env(args.env_file), compose)
    command = ["docker", "compose", "-f", str(compose), "--env-file", str(args.env_file), "--profile", "*"]
    if args.release_scope:
        command = ["docker", "compose", "-f", str(compose), "-f", "ops/docker-compose.core.yml",
                   "--env-file", str(args.env_file), "--profile", "ops"]
    built = {}
    specifications = []
    try:
        config = json.loads(subprocess.check_output(command + ["config", "--format", "json"], env=env, stderr=subprocess.PIPE))
        if args.release_scope:
            scope = json.loads(args.release_scope.read_text(encoding="utf-8"))
            required = active_services(scope)
            if set(config["services"]) != set(required):
                raise ValueError("RELEASE_SERVICE_SET_MISMATCH")
            for name, row in required.items():
                service = config["services"][name]
                if service.get("build") or service.get("image") != row["image"]:
                    raise ValueError("RELEASE_IMAGE_MISMATCH")
                identity = subprocess.check_output(["docker", "image", "inspect", row["image"],
                                                    "--format", "{{.Id}}"], stderr=subprocess.PIPE,
                                                   timeout=30).decode().strip()
                if identity != row["image"].split("@")[1]:
                    raise ValueError("RELEASE_IMAGE_UNAVAILABLE")
                specifications.extend(["--image", name + "=" + row["image"]])
            services = ()
        else:
            services = ("api", "web") if args.core_only else ("api", "worker", "scheduler", "ml-worker", "web", "postgres", "valkey", "minio", "caddy", "prometheus", "grafana", "mlflow", "ollama")
        for service in services:
            value = config["services"][service]
            image = value.get("image") or config["name"] + "-" + service
            if "build" in value:
                contract = json.dumps(value["build"], sort_keys=True)
                if contract in built:
                    subprocess.run(["docker", "tag", built[contract], image], check=True, capture_output=True)
                else:
                    subprocess.run(command + ["build", service], env=env, check=True, capture_output=True)
                    built[contract] = image
            else:
                subprocess.run(["docker", "pull", image], check=True, capture_output=True)
            specifications.extend(["--image", service + "=" + image])
    except (subprocess.SubprocessError, OSError, ValueError, KeyError):
        print("SECURITY_SCAN_INCOMPLETE: build/pull/configuration did not complete")
        return 2
    result = subprocess.run([
        sys.executable, "ops/security_audit.py", "--scanner", str(args.scanner),
        "--scanner-sha256", args.scanner_sha256, "--cache", str(args.cache),
        "--output", str(args.output), *specifications,
    ], env=env).returncode
    if args.release_scope and result == 0:
        write_new(args.output / "release-scope-audit.json", {
            "status": "EXACT_CONFIG_AND_IMAGE_SCOPE_VERIFIED",
            "scope_sha256": sha256(args.release_scope),
            "configuration_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
            "selected_config_files_sha256": {name: sha256(Path(name)) for name in CONFIGURATION_FILES},
            "configuration_scope": "CI_GENERATED_CONFIG_ONLY_NOT_TARGET",
            "verified_service_images": {name: row["image"] for name, row in required.items()},
            "release_status": "NOT_APPROVED",
        })
    return result


if __name__ == "__main__":
    raise SystemExit(main())
