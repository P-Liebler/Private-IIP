"""Verify local production HTTPS, secure login, valuation and monitoring without logging secrets."""

from __future__ import annotations

import argparse
import base64
import http.cookiejar
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", default="https://localhost")
    parser.add_argument("--ca-file", type=Path)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--expected-value", required=True)
    args = parser.parse_args()
    password = os.environ.get("RESTORE_TEST_PASSWORD")
    if not password or not args.origin.startswith("https://"):
        parser.error("Use HTTPS and set the explicit fixture RESTORE_TEST_PASSWORD")
    context = ssl.create_default_context(cafile=str(args.ca_file) if args.ca_file else None)
    cookies = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context), urllib.request.HTTPCookieProcessor(cookies)
    )

    def fetch(url: str, data: dict[str, str] | None = None, headers: dict[str, str] | None = None):
        request = urllib.request.Request(
            url,
            data=json.dumps(data).encode() if data else None,
            headers={"Origin": args.origin, "Content-Type": "application/json", **(headers or {})},
        )
        with opener.open(request, timeout=20) as response:
            return response.headers, json.loads(response.read())

    try:
        with opener.open(args.origin + "/login", timeout=20) as response:
            assert response.status == 200 and b"Anmelden" in response.read()
            assert response.headers["X-Frame-Options"] == "DENY"
        headers, _ = fetch(args.origin + "/api/v1/health/ready")
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        login_headers, login = fetch(
            args.origin + "/api/v1/auth/login", {"username": args.username, "password": password}
        )
        assert login["status"] == "authenticated"
        cookie = login_headers.get("Set-Cookie", "")
        assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
        _, value = fetch(args.origin + f"/api/v1/portfolios/{args.portfolio_id}/valuation")
        assert value["status"] == "COMPLETE" and Decimal(value["total_value_base"]) == Decimal(
            args.expected_value
        )
        try:
            fetch(args.origin + "/internal/metrics")
            raise AssertionError("Metrics must be blocked at Caddy")
        except urllib.error.HTTPError as error:
            assert error.code == 404
        _, targets = fetch("http://localhost:9090/api/v1/targets")
        api_targets = [
            target
            for target in targets["data"]["activeTargets"]
            if target["labels"].get("job") == "private-iip-api"
        ]
        assert api_targets and all(target["health"] == "up" for target in api_targets)
        settings = {}
        for line in args.env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(("GRAFANA_ADMIN_USER=", "GRAFANA_ADMIN_PASSWORD=")):
                key, value = line.split("=", 1)
                settings[key] = value.strip().strip('"').strip("'")
        credentials = (
            settings["GRAFANA_ADMIN_USER"] + ":" + settings["GRAFANA_ADMIN_PASSWORD"]
        ).encode()
        auth = "Basic " + base64.b64encode(credentials).decode()
        _, dashboard = fetch(
            "http://localhost:3001/api/dashboards/uid/private-iip-v1",
            headers={"Authorization": auth},
        )
        assert dashboard["dashboard"]["panels"]
        print(
            "Endpoint probe PASSED (not operator/target acceptance): verified TLS, security headers, Secure/HttpOnly login, "
            "valuation, blocked metrics, Prometheus scrape and provisioned Grafana dashboard"
        )
        return 0
    except Exception as error:
        print(f"Production probe FAILED: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
