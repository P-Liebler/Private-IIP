"""Explicit deployment orchestration; defaults to printing a plan without changes."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path

from preflight import compose_environment, read_env, validate_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "deploy", "rollback-prep"))
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--mode", choices=("DRY_RUN", "STAGING", "PRODUCTION"), default="DRY_RUN")
    parser.add_argument("--operator-authorized", action="store_true")
    parser.add_argument("--migrations-reviewed", action="store_true")
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
    for command in plans[args.action]:
        result = subprocess.run(command, env=compose_environment(read_env(args.env_file), Path("docker-compose.prod.yml")), capture_output=True, check=False)
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
