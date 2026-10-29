"""Plan or enqueue bounded updates for current holdings using existing Core APIs.

Default is preview only. Provider rights, identity, quotas and checkpoints remain
authoritative in BackfillJobService. This tool never contacts a provider itself.
"""
import argparse
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
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


def current_requirements(valuation):
    """No price/FX fallback; the current ledger determines the requested IDs."""
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
        except (KeyError, TypeError, InvalidOperation, ValueError):
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
    if any(not isinstance(c, str) or len(c) != 3 or not c.isupper() for c in currencies):
        raise ValueError("HOLDINGS_CURRENCY_INVALID")
    return sorted(identifiers), currencies


def reviewed_source(source, use, now):
    """Selection is stricter than a generic approval; the backend remains authoritative."""
    try:
        checked = datetime.fromisoformat(source["checked_at"])
        expires = datetime.fromisoformat(source["next_review_at"])
        return (source["gate_status"] == "APPROVED" and source["enabled"] is True
                and source.get("gate_reason") is None
                and checked.tzinfo is not None and expires.tzinfo is not None
                and checked <= now < expires and source["terms_url"].startswith("https://")
                and bool(source["scope"]) and type(source["rate_limit_per_minute"]) is int
                and source["rate_limit_per_minute"] > 0
                and {use, "raw_archive", "derived_analysis"} <= set(source["allowed_uses"]))
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def covered_listing(source, instrument, start, end):
    """Exact operator-reviewed tokens in the existing append-only source scope.

    price_listing=UUID|symbol|MIC|currency|STOCK-or-ETF|from|through
    The existing collector additionally requires instrument=UUID. A generic
    country, ISIN or provider advertising claim never establishes coverage.
    """
    try:
        iid = str(UUID(instrument["id"]))
        identity = [iid, instrument["ticker"], instrument["mic"], instrument["currency"],
                    instrument["asset_type"]]
        if (instrument["active"] is not True or not all(isinstance(v, str) and v for v in identity)
                or len(identity[2]) != 4 or identity[4] not in {"STOCK", "ETF"}):
            return False
        tokens = source["scope"].split()
        if "instrument=" + iid not in tokens:
            return False
        matches = []
        for token in tokens:
            if not token.startswith("price_listing=" + iid + "|"):
                continue
            parts = token.removeprefix("price_listing=").split("|")
            if len(parts) != 7:
                return False
            first, last = date.fromisoformat(parts[5]), date.fromisoformat(parts[6])
            matches.append(parts[:5] == identity and first <= start <= end <= last)
        # Contradictory or duplicated attestation is a review task, not a tie-break.
        return len(matches) == 1 and matches[0]
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def covered_fx(source, start, end):
    """The existing ECB collector always retrieves both EUR-denominated input legs."""
    try:
        tokens = source["scope"].split()
        inputs = "fx_inputs=EXR.D.CHF.EUR.SP00.A,EXR.D.USD.EUR.SP00.A"
        ranges = [token.removeprefix("fx_coverage=").split("|")
                  for token in tokens if token.startswith("fx_coverage=")]
        return (inputs in tokens and len(ranges) == 1 and len(ranges[0]) == 2
                and date.fromisoformat(ranges[0][0]) <= start <= end <= date.fromisoformat(ranges[0][1]))
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def requests_for_holdings(valuation, start, end, sources=(), instruments=None, *, now=None):
    """Deterministic coverage selection; missing evidence produces an abstention."""
    if start > end or (end - start).days > 31:
        raise ValueError("REFRESH_RANGE_INVALID")
    now = now or datetime.now(UTC)
    identifiers, currencies = current_requirements(valuation)
    instruments = instruments or {}
    registry = {}
    for source in sources:
        slug = source["slug"]
        if slug in registry:
            raise ValueError("SOURCE_REGISTRY_AMBIGUOUS")
        registry[slug] = source
    common = {"start": start.isoformat(), "end": end.isoformat()}
    jobs, unavailable = [], []
    # Only collectors already implemented in BackfillJobService may be selected.
    source = registry.get("ALPHAVANTAGE", {})
    for identifier in identifiers:
        detail = instruments.get(identifier, {})
        holding_currencies = {h["currency"] for h in valuation["holdings"]
                              if h["instrument_id"] == identifier and Decimal(str(h["quantity"])) != 0}
        if (holding_currencies == {detail.get("currency")} and detail.get("id") == identifier and reviewed_source(source, "prices", now)
                and covered_listing(source, detail, start, end)):
            jobs.append({**common, "source_slug": "ALPHAVANTAGE", "kind": "ALPHA_PRICES",
                         "instrument_ids": [identifier]})
        else:
            unavailable.append({"kind": "prices", "instrument_id": identifier,
                                "reason": "NO_APPROVED_EXACT_LISTING_COVERAGE", "action": "MANUAL_IMPORT_OR_REVIEW"})
    for currency in sorted(currencies - {"CHF", "USD", "EUR"}):
        unavailable.append({"kind": "fx", "currency": currency,
                            "reason": "FX_CURRENCY_UNSUPPORTED", "action": "MANUAL_IMPORT_OR_REVIEW"})
    needed_fx = sorted(currencies & {"USD", "EUR"})
    if needed_fx:
        source = registry.get("ECB", {})
        if reviewed_source(source, "fx_rates", now) and covered_fx(source, start, end):
            # One request already yields EUR/CHF plus the EUR/USD leg for USD/CHF.
            jobs.append({**common, "source_slug": "ECB", "kind": "ECB_FX",
                         "series": "USD_CHF" if "USD" in needed_fx else "EUR_CHF"})
        else:
            unavailable.append({"kind": "fx", "currencies": needed_fx,
                                "reason": "NO_APPROVED_ECB_INPUT_COVERAGE", "action": "MANUAL_IMPORT_OR_REVIEW"})
    return jobs, unavailable


def completion(job):
    """Keep bounded checkpoints and error codes; never copy provider response bodies."""
    return {key: job.get(key) for key in ("status", "progress", "last_error_code",
            "started_at", "completed_at")} | {"job_id": job["id"], "result_chunks": len(job.get("results", []))}


def quota_errors(receipts, overview):
    """Conservative preview budgets; actual remaining quota is checked per attempt by the API."""
    errors = []
    total, alpha = 0, 0
    for receipt in receipts:
        maximum = receipt.get("maximum_requests", 0)
        if type(maximum) is not int or maximum < 0:
            return ["APPLICATION_QUOTA_RESPONSE_INVALID"]
        total += maximum
        if receipt["request"]["source_slug"] == "ALPHAVANTAGE":
            alpha += maximum
    limit = overview.get("daily_request_limit")
    if type(limit) is not int or limit < 1:
        errors.append("APPLICATION_QUOTA_RESPONSE_INVALID")
    elif total > limit or alpha > 25:
        errors.append("CONSERVATIVE_DAILY_REQUEST_BUDGET_EXCEEDED")
    pending = sum(job.get("status") in {"QUEUED", "RUNNING"} for job in overview.get("jobs", []))
    if pending + len(receipts) > 4:
        errors.append("PENDING_JOB_BUDGET_EXCEEDED")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--ca", type=Path, required=True)
    parser.add_argument("--portfolio-id", type=UUID, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Private append-only receipt, outside Git")
    parser.add_argument("--execute", action="store_true", help="Enqueue only previews accepted by the existing source gates")
    parser.add_argument("--inspect-receipt", type=Path, help="Read existing job checkpoints without enqueueing new jobs")
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
    if args.execute and args.inspect_receipt:
        parser.error("Inspect and execute are separate operations")
    root = Path(__file__).resolve().parents[1]
    if args.output.resolve().is_relative_to(root) and not args.output.resolve().is_relative_to(root / "backups"):
        parser.error("Keep private receipts outside the repository or under ignored backups/")
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

    record = {"contract": "CURRENT_HOLDINGS_REFRESH_V2", "recorded_at": datetime.now(UTC).isoformat(),
              "portfolio_id": str(args.portfolio_id), "execute_requested": args.execute,
              "live_continuity_proven": False, "jobs": [], "status": "INCOMPLETE"}
    authenticated = False
    try:
        request("/auth/login", {"username": username, "password": password})
        authenticated = True
        if args.inspect_receipt:
            if args.inspect_receipt.stat().st_size > 4 * 1024**2:
                raise ValueError("RECEIPT_TOO_LARGE")
            previous = json.loads(args.inspect_receipt.read_bytes())
            if previous["portfolio_id"] != str(args.portfolio_id):
                raise ValueError("RECEIPT_PORTFOLIO_MISMATCH")
            for receipt in previous["jobs"]:
                if receipt.get("job_id"):
                    iid = UUID(receipt["job_id"])
                    record["jobs"].append(completion(request(f"/data-operations/jobs/{iid}")))
            statuses = [job["status"] for job in record["jobs"]]
            record["status"] = ("JOBS_SUCCESS_NOT_LIVE_VALIDATED" if statuses and all(s == "SUCCESS" for s in statuses)
                                else "JOBS_PENDING_OR_FAILED" if statuses else "NO_JOB_CHECKPOINTS")
            return_code = 0 if record["status"] == "JOBS_SUCCESS_NOT_LIVE_VALIDATED" else 1
            print(record["status"])
            return return_code
        valuation = request(f"/portfolios/{args.portfolio_id}/valuation")
        sources = request("/data-sources")
        identifiers, _ = current_requirements(valuation)
        instruments = {iid: request(f"/instruments/{iid}") for iid in identifiers}
        overview = request("/data-operations")
        # Overlap is intentional: canonical versioning and existing persistent
        # collector checkpoints handle corrections and duplicate observations.
        end = datetime.now(UTC).date() - timedelta(days=1)
        jobs, unavailable = requests_for_holdings(valuation, end - timedelta(days=31), end, sources, instruments)
        record.update(unavailable=unavailable, holdings_observed_at=datetime.now(UTC).isoformat(),
                      source_review_pins=[{"slug": s["slug"], "checked_at": s.get("checked_at"),
                          "scope_sha256": hashlib.sha256(str(s.get("scope", "")).encode()).hexdigest()}
                          for s in sources if s["slug"] in {job["source_slug"] for job in jobs}],
                      remaining_quota_status="AUTHORITATIVE_PER_ATTEMPT_BACKEND_CHECK")
        for job in jobs:
            receipt = {"request": job, "status": "PREVIEW_PENDING"}
            try:
                preview = request("/data-operations/preview", job)
                if preview["status"] != "READY":
                    raise ValueError("APPLICATION_PREVIEW_INVALID")
                receipt.update(status="PREVIEW_ACCEPTED", maximum_requests=preview["maximum_requests"])
            except urllib.error.HTTPError as error:
                # No raw body, cookies, request headers or credentials in receipts.
                receipt.update(status="BLOCKED_BY_APPLICATION_GATE", http_status=error.code)
            record["jobs"].append(receipt)
        accepted = [receipt for receipt in record["jobs"] if receipt["status"] == "PREVIEW_ACCEPTED"]
        record["quota_errors"] = quota_errors(accepted, overview)
        if args.execute and not record["quota_errors"]:
            for receipt in accepted:
                try:
                    # Re-read registry and identity immediately before enqueue;
                    # the backend rechecks source rights on every actual attempt.
                    fresh_jobs, _ = requests_for_holdings(valuation, end - timedelta(days=31), end,
                        request("/data-sources"), {iid: request(f"/instruments/{iid}") for iid in identifiers})
                    if receipt["request"] not in fresh_jobs:
                        receipt["status"] = "COVERAGE_CHANGED_REVIEW_REQUIRED"
                        continue
                    result = request("/data-operations/jobs", receipt["request"])
                    receipt.update(status="QUEUED", job_id=result["id"], checkpoint=completion(result))
                except urllib.error.HTTPError as error:
                    receipt.update(status="BLOCKED_BY_APPLICATION_GATE", http_status=error.code)
        record["status"] = ("BLOCKED" if unavailable or record["quota_errors"] or any(j["status"] in {"BLOCKED_BY_APPLICATION_GATE", "COVERAGE_CHANGED_REVIEW_REQUIRED"} for j in record["jobs"])
                            else "QUEUED_NOT_LIVE_VERIFIED" if args.execute and jobs else "PREVIEW_ONLY")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, InvalidOperation):
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
