"""Build/pull and scan all configured production images without starting services."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from preflight import compose_environment, read_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--scanner", type=Path, required=True)
    parser.add_argument("--scanner-sha256", required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--core-only", action="store_true")
    args = parser.parse_args()
    compose = Path("docker-compose.prod.yml")
    env = compose_environment(read_env(args.env_file), compose)
    command = ["docker", "compose", "-f", str(compose), "--env-file", str(args.env_file), "--profile", "*"]
    built = {}
    specifications = []
    try:
        config = json.loads(subprocess.check_output(command + ["config", "--format", "json"], env=env, stderr=subprocess.PIPE))
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
    return subprocess.run([
        sys.executable, "ops/security_audit.py", "--scanner", str(args.scanner),
        "--scanner-sha256", args.scanner_sha256, "--cache", str(args.cache),
        "--output", str(args.output), *specifications,
    ], env=env).returncode


if __name__ == "__main__":
    raise SystemExit(main())
