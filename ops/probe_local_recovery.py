"""Controlled local-only HTTPS/fault/performance probe of a disposable staging stack.

Never accepts a production mode or a remote hostname. No financial provider requests.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from preflight import read_env


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--ca-file", type=Path, required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--instrument-id", required=True)
    parser.add_argument("--faults", action="store_true", help="Explicitly permit local container stop/start")
    parser.add_argument("--optional-faults", action="store_true", help="Explicitly test local MLflow/Ollama stop/start")
    parser.add_argument("--compose-override", type=Path, help="Local staging image override, never a target deployment")
    args = parser.parse_args()
    values = read_env(args.env_file)
    if values.get("APP_ENV") != "staging" or values.get("VPN_BIND_ADDRESS") != "127.0.0.1" or values.get("APP_DOMAIN") != "localhost":
        parser.error("This synthetic probe is restricted to loopback staging")
    if not args.username.startswith("restore_") or not os.environ.get("RESTORE_TEST_PASSWORD"):
        parser.error("Explicit disposable restore fixture required")
    origin = "https://localhost"
    context = ssl.create_default_context(cafile=str(args.ca_file))
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context), urllib.request.HTTPCookieProcessor(jar))
    timings: list[dict] = []
    evidence: dict = {"scope": "LOCAL_SYNTHETIC_STAGING", "started_at": datetime.now(UTC).isoformat(), "concurrency": 1, "target_host_verified": False}

    def fetch(path: str, data: dict | None = None, expected: int = 200, extra_headers: dict | None = None):
        started = time.perf_counter()
        request = urllib.request.Request(origin + path, data=json.dumps(data).encode() if data is not None else None,
            headers={"Origin": origin, "Content-Type": "application/json", **(extra_headers or {})})
        try:
            with opener.open(request, timeout=30) as response:
                code, body = response.status, response.read()
        except urllib.error.HTTPError as error:
            code, body = error.code, error.read()
        timings.append({"operation": path.replace(args.portfolio_id, "{portfolio}").replace(args.instrument_id, "{instrument}"), "http_status": code, "seconds": round(time.perf_counter() - started, 4)})
        assert code == expected, f"Unexpected HTTP status {code}"
        return json.loads(body) if body else None

    def portfolio():
        result = fetch(f"/api/v1/portfolios/{args.portfolio_id}/valuation")
        assert result["status"] == "COMPLETE" and Decimal(result["total_value_base"]) == Decimal("10180")

    def compose(*command: str):
        base = ["docker", "compose", "--env-file", str(args.env_file), "-f", "docker-compose.prod.yml"]
        if args.compose_override:
            base += ["-f", str(args.compose_override)]
        result = subprocess.run([*base, *command], capture_output=True, check=False)
        if result.returncode:
            raise RuntimeError("Controlled Compose operation failed")

    try:
        try:
            urllib.request.urlopen(origin + "/api/v1/health/live", timeout=10)
            raise AssertionError("Untrusted CA was accepted")
        except urllib.error.URLError as error:
            assert isinstance(error.reason, ssl.SSLCertVerificationError)
        evidence["untrusted_tls"] = "REJECTED"
        fetch("/api/v1/settings", expected=401)
        fetch("/api/v1/auth/login", {"username": args.username, "password": os.environ["RESTORE_TEST_PASSWORD"]})
        portfolio()
        for path in ("/api/v1/portfolio-dashboard", f"/api/v1/instruments/{args.instrument_id}", "/api/v1/assistant/status", "/api/v1/notifications"):
            fetch(path)
        fetch(f"/api/v1/portfolios/{args.portfolio_id}/risk", {})
        fetch("/api/v1/auth/logout", {}, expected=403, extra_headers={"Origin": "https://hostile.invalid"})
        portfolio()
        if args.faults:
            for service in ("scheduler", "worker", "minio", "postgres", "valkey"):
                compose("stop", service)
                try:
                    fetch("/api/v1/health/ready", expected=503 if service in {"minio", "postgres", "valkey"} else 200)
                    if service in {"scheduler", "worker", "minio"}:
                        portfolio()
                finally:
                    started = time.perf_counter()
                    compose("start", "--wait", service)
                    evidence[service + "_restart_seconds"] = round(time.perf_counter() - started, 3)
                fetch("/api/v1/health/ready")
                portfolio()
            started = time.perf_counter()
            compose("restart", "--no-deps", "api")
            for attempt in range(60):
                try:
                    fetch("/api/v1/health/ready")
                    break
                except (urllib.error.URLError, AssertionError):
                    time.sleep(1)
            else:
                raise RuntimeError("API did not recover")
            evidence["api_warm_restart_seconds"] = round(time.perf_counter() - started, 3)
            portfolio()  # Existing cookie remains valid against the persisted session table.
        if args.optional_faults:
            for service in ("mlflow", "ollama"):
                compose("start", "--wait", service)
                compose("stop", service)
                try:
                    fetch("/api/v1/health/ready")
                    portfolio()
                    fetch(f"/api/v1/instruments/{args.instrument_id}")
                    assistant = fetch("/api/v1/assistant/status")
                    if service == "ollama":
                        assert assistant["status"] == "LLM_UNAVAILABLE"
                finally:
                    compose("start", "--wait", service)
                evidence[service + "_outage"] = "CORE_REMAINS_AVAILABLE"
                portfolio()
        fetch("/api/v1/auth/logout", {}, expected=204)
        fetch("/api/v1/settings", expected=401)
        evidence["passed"] = True
    except Exception as error:
        evidence.update(passed=False, error=type(error).__name__)
    evidence["timings"] = timings
    evidence["completed_at"] = datetime.now(UTC).isoformat()
    print(json.dumps(evidence, indent=2))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
