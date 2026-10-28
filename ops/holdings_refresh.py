"""Plan or enqueue bounded updates for current holdings using existing Core APIs.

Default is preview only. Provider rights, identity, quotas and checkpoints remain
authoritative in BackfillJobService. This tool never contacts a provider itself.
"""
import argparse
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import http.cookiejar
import json
import os
from pathlib import Path
import ssl
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from uuid import UUID

from security_audit import write_new


def requests_for_holdings(valuation, start, end):
    """No price/FX fallback; ledger quantities determine the requested IDs."""
    identifiers, currencies = set(), set()
    if valuation.get("base_currency") != "CHF":
        raise ValueError("AUTOMATIC_FX_BASE_UNSUPPORTED")
    if not isinstance(valuation.get("holdings"), list) or not isinstance(valuation.get("cash"), list):
        raise ValueError("HOLDINGS_RESPONSE_INVALID")
    for holding in valuation["holdings"]:
        try:
            quantity = Decimal(str(holding["quantity"]))
            if not quantity.is_finite():
                raise ValueError("NONFINITE_QUANTITY")
            identifier = str(UUID(holding["instrument_id"]))
        except (KeyError, TypeError, InvalidOperation):
            raise ValueError("HOLDINGS_RESPONSE_INVALID") from None
        if quantity != 0:
            identifiers.add(identifier)
            currencies.add(holding["currency"])
    for cash in valuation["cash"]:
        amount = Decimal(str(cash["amount"]))
        if not amount.is_finite():
            raise ValueError("NONFINITE_CASH")
        if amount != 0:
            currencies.add(cash["currency"])
    if len(identifiers) > 30:
        raise ValueError("HOLDINGS_LIMIT_EXCEEDED")
    common = {"start": start.isoformat(), "end": end.isoformat()}
    jobs = [{**common, "source_slug": "ALPHAVANTAGE", "kind": "ALPHA_PRICES",
             "instrument_ids": [identifier]} for identifier in sorted(identifiers)]
    unsupported = sorted(currencies - {"CHF", "USD", "EUR"})
    for currency in sorted(currencies & {"USD", "EUR"}):
        jobs.append({**common, "source_slug": "ECB", "kind": "ECB_FX", "series": currency + "_CHF"})
    return jobs, unsupported


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--ca", type=Path, required=True)
    parser.add_argument("--portfolio-id", type=UUID, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Private append-only receipt, outside Git")
    parser.add_argument("--execute", action="store_true", help="Enqueue only previews accepted by the existing source gates")
    args = parser.parse_args()
    origin = args.origin.rstrip("/")
    parsed = urlsplit(origin)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        parser.error("An HTTPS application origin without credentials or path is required")
    username, password = os.environ.get("IIP_OPERATOR_USERNAME"), os.environ.get("IIP_OPERATOR_PASSWORD")
    if not username or not password:
        parser.error("Set IIP_OPERATOR_USERNAME and IIP_OPERATOR_PASSWORD through protected local environment")
    if args.output.exists():
        parser.error("Choose a new receipt path")
    # Explicit local certificate trust; never disable verification.
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=str(args.ca))),
        urllib.request.HTTPCookieProcessor(jar))

    def request(path, body=None):
        with opener.open(urllib.request.Request(origin + "/api/v1" + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Origin": origin, "Content-Type": "application/json"}), timeout=60) as response:
            data = response.read(4 * 1024**2 + 1)
            if len(data) > 4 * 1024**2:
                raise ValueError("APPLICATION_RESPONSE_TOO_LARGE")
            return json.loads(data) if data else None

    record = {"contract": "CURRENT_HOLDINGS_REFRESH_V1", "recorded_at": datetime.now(UTC).isoformat(),
              "portfolio_id": str(args.portfolio_id), "execute_requested": args.execute,
              "live_continuity_proven": False, "jobs": [], "status": "INCOMPLETE"}
    authenticated = False
    try:
        request("/auth/login", {"username": username, "password": password})
        authenticated = True
        valuation = request(f"/portfolios/{args.portfolio_id}/valuation")
        # Overlap is intentional: canonical versioning and existing persistent
        # collector checkpoints handle corrections and duplicate observations.
        end = datetime.now(UTC).date() - timedelta(days=1)
        jobs, unsupported = requests_for_holdings(valuation, end - timedelta(days=31), end)
        record.update(unsupported_fx_currencies=unsupported, holdings_observed_at=datetime.now(UTC).isoformat())
        for job in jobs:
            receipt = {"request": job, "status": "PREVIEW_PENDING"}
            try:
                preview = request("/data-operations/preview", job)
                receipt["status"] = "PREVIEW_ACCEPTED"
                if args.execute:
                    result = request("/data-operations/jobs", job)
                    receipt.update(status="QUEUED", job_id=result["id"])
            except urllib.error.HTTPError as error:
                # No raw body, cookies, request headers or credentials in receipts.
                receipt.update(status="BLOCKED_BY_APPLICATION_GATE", http_status=error.code)
            record["jobs"].append(receipt)
        record["status"] = ("BLOCKED" if unsupported or any(j["status"] == "BLOCKED_BY_APPLICATION_GATE" for j in record["jobs"])
                            else "QUEUED_NOT_LIVE_VERIFIED" if args.execute and jobs else "PREVIEW_ONLY")
    except (OSError, ValueError, KeyError, TypeError, InvalidOperation):
        record["status"] = "APPLICATION_OR_HOLDINGS_UNAVAILABLE"
    finally:
        if authenticated:
            try:
                request("/auth/logout", {})
            except (OSError, ValueError):
                record["logout_status"] = "UNVERIFIED"
        write_new(args.output, record)
    print(record["status"])
    return 0 if record["status"] in {"PREVIEW_ONLY", "QUEUED_NOT_LIVE_VERIFIED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
