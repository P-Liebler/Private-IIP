import asyncio
import hashlib
import json
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from app.core.errors import AppError
from app.models import ActionCoverageReview, DataSource, RawIngestion
from app.providers.alpha_vantage import parse_daily
from app.providers.http import PinnedBackend, fetch_response, public_addresses, retry_delay
from app.providers.snb_fx import parse_snb_csv
from app.schemas.data_operations import CollectionInput
from app.services.backfill_jobs import chunks
from app.services.market_validation import validate_action
from app.services.version_hashing import version_payload

SNB = (
    b'"CubeId";"snboffzisa"\r\n"PublishingDate";"2024-02-01 09:00"\r\n\r\n'
    b'"Date";"D0";"Value"\r\n"2024-01";"LZ";"1.75"\r\n'
)
NOW = datetime(2026, 10, 16, tzinfo=UTC)


@pytest.mark.parametrize(
    "change",
    [
        "valid",
        "missing",
        "schema",
        "duplicate",
        "wrong_dimension",
        "nan",
        "date",
        "empty",
        "wrong_cube",
    ],
)
def test_snb_verified_contract(change: str) -> None:
    data = SNB
    if change == "missing":
        data = data.replace(b'"1.75"', b'"-"')
    elif change == "schema":
        data = data.replace(b'"Value"', b'"Close"')
    elif change == "duplicate":
        data += b'"2024-01";"LZ";"1.75"\r\n'
    elif change == "wrong_dimension":
        data = data.replace(b'"LZ"', b'"EUR1"')
    elif change == "nan":
        data = data.replace(b'"1.75"', b'"NaN"')
    elif change == "date":
        data = data.replace(b'"2024-01"', b'"2024-19"')
    elif change == "empty":
        data = b""
    elif change == "wrong_cube":
        data = data.replace(b'"snboffzisa"', b'"devkum"')
    if change not in {"valid", "missing"}:
        with pytest.raises(AppError):
            parse_snb_csv(data, "SNB_rate", NOW)
    else:
        rows = parse_snb_csv(data, "SNB_rate", NOW)
        if change == "missing":
            assert rows == []
        else:
            assert rows[0]["observation_date"] == date(2024, 1, 31)
            assert rows[0]["known_at"] == NOW
            assert rows[0]["frequency"] == "M"
            assert rows[0]["unit"] == "PERCENT"


def test_snb_reference_fx_cannot_become_daily_valuation() -> None:
    data = (
        b'"CubeId";"devkum"\n"PublishingDate";"2024-02-01 14:30"\n\n'
        b'"Date";"D0";"D1";"Value"\n"2024-01";"M1";"EUR1";"0.93"\n'
    )
    row = parse_snb_csv(data, "EUR_CHF", NOW)[0]
    assert row["series"] == "EUR_CHF" and row["frequency"] == "M"
    assert "rate_date" not in row
    with pytest.raises(AppError):
        parse_snb_csv(data.replace(b'"EUR1"', b'"USD1"'), "EUR_CHF", NOW)


@pytest.mark.parametrize(
    "scenario", ["success", "redirect", "oversize", "type", "timeout", "429", "304", "blocked"]
)
def test_bounded_archival_transport(scenario: str) -> None:
    async def run() -> None:
        source = DataSource(
            id=uuid4(),
            slug="TEST_PR1",
            type="MANUAL",
            checked_at=datetime.now(UTC),
            gate_status="UNKNOWN" if scenario == "blocked" else "APPROVED",
            enabled=scenario != "blocked",
            allowed_uses=["fx_rates"],
        )
        calls, stored = [], []

        async def store(**values: object) -> RawIngestion:
            stored.append(values)
            body = values["data"]
            return RawIngestion(
                id=uuid4(),
                source_id=source.id,
                received_at=datetime.now(UTC),
                sha256=hashlib.sha256(body).hexdigest(),
                http_status=values["http_status"],
            )

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            if scenario == "timeout":
                raise httpx.ReadTimeout("synthetic timeout")
            status = {"redirect": 302, "429": 429, "304": 304}.get(scenario, 200)
            return httpx.Response(
                status,
                content=b'{"test":true}',
                headers={
                    "Content-Type": "text/html" if scenario == "type" else "application/json",
                    "Location": "http://127.0.0.1/private",
                    "Retry-After": "120",
                },
            )

        raw, db, limit = MagicMock(), MagicMock(), AsyncMock()
        raw.store, raw.record_failure, db.refresh = (
            AsyncMock(side_effect=store),
            AsyncMock(),
            AsyncMock(),
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=True
        ) as client:
            with (
                patch("app.providers.http.MAX_BYTES", 3 if scenario == "oversize" else 1000),
                patch("app.providers.http.asyncio.sleep", new=AsyncMock()),
            ):
                operation = fetch_response(
                    db,
                    raw,
                    source,
                    use="fx_rates",
                    url="https://example.org/fx",
                    allowed_host="example.org",
                    resource="test",
                    client=client,
                    limiter=limit,
                )
                if scenario in {"success", "304"}:
                    row = await operation
                    assert row.http_status == (304 if scenario == "304" else 200)
                else:
                    with pytest.raises(AppError):
                        await operation
        assert len(calls) == (0 if scenario == "blocked" else 3 if scenario == "timeout" else 1)
        assert len(stored) == (0 if scenario in {"blocked", "oversize", "timeout"} else 1)
        assert len(calls) == limit.await_count
        if stored:
            assert stored[0]["data"] == b'{"test":true}'

    asyncio.run(run())


@pytest.mark.parametrize(
    "address", ["127.0.0.1", "10.1.2.3", "169.254.169.254", "::1", "::ffff:127.0.0.1"]
)
def test_dns_private_address_rejected(address: str) -> None:
    async def run() -> None:
        with patch(
            "app.providers.http.socket.getaddrinfo", return_value=[(2, 1, 6, "", (address, 443))]
        ):
            with pytest.raises(AppError):
                await public_addresses("example.org")

    asyncio.run(run())


def test_dns_connect_uses_checked_ip_once() -> None:
    async def run() -> None:
        with (
            patch(
                "app.providers.http.public_addresses", new=AsyncMock(return_value=["93.184.216.34"])
            ) as resolve,
            patch("httpcore._backends.anyio.AnyIOBackend.connect_tcp", new=AsyncMock()) as connect,
        ):
            await PinnedBackend().connect_tcp("example.org", 443)
            resolve.assert_awaited_once_with("example.org")
            assert connect.await_args.args[0] == "93.184.216.34"

    asyncio.run(run())


def test_backfill_bounds_and_corporate_action_semantics() -> None:
    request = CollectionInput(
        source_slug="ECB", kind="ECB_FX", start=date(2024, 1, 1), end=date(2024, 3, 1)
    )
    windows = chunks(request)
    assert len(windows) == 2 and windows[0][1] < windows[1][0]
    assert sum((b - a).days + 1 for a, b in windows) == 61
    action = validate_action(
        {
            "date": "2024-01-02",
            "action_type": "SPLIT",
            "ratio_numerator": "3",
            "ratio_denominator": "2",
        },
        "CHF",
    )
    assert str(action["ratio"]) == "1.5"
    dividend = validate_action(
        {
            "date": "2024-01-02",
            "action_type": "SPECIAL_DIVIDEND",
            "cash_amount": "2",
            "currency": "CHF",
        },
        "CHF",
    )
    assert dividend["action_type"] == "DIVIDEND"
    assert dividend["event_details"]["classification"] == "SPECIAL_DIVIDEND"
    for kind in ("SPIN_OFF", "MERGER", "EXCHANGE"):
        with pytest.raises(ValueError):
            validate_action({"date": "2024-01-02", "action_type": kind}, "CHF")
    assert retry_delay("120", 0) == 120


@pytest.mark.parametrize(
    "scenario", ["valid", "wrong_symbol", "adjusted", "numeric_type", "notice", "duplicate"]
)
def test_optional_raw_daily_contract(scenario: str) -> None:
    payload = {
        "Meta Data": {"2. Symbol": "SYNTHETIC"},
        "Time Series (Daily)": {
            "2024-01-03": {
                "1. open": "99",
                "2. high": "101",
                "3. low": "98",
                "4. close": "100",
                "5. volume": "10",
            }
        },
    }
    if scenario == "wrong_symbol":
        payload["Meta Data"]["2. Symbol"] = "OTHER"
    elif scenario == "adjusted":
        payload["Time Series (Daily)"]["2024-01-03"]["5. adjusted close"] = "95"
        del payload["Time Series (Daily)"]["2024-01-03"]["5. volume"]
    elif scenario == "numeric_type":
        payload["Time Series (Daily)"]["2024-01-03"]["1. open"] = 99
    elif scenario == "notice":
        payload = {"Information": "synthetic quota notice"}
    data = json.dumps(payload).encode()
    if scenario == "duplicate":
        data = data.replace(
            b'"2. Symbol": "SYNTHETIC"', b'"2. Symbol":"OTHER","2. Symbol":"SYNTHETIC"'
        )
    if scenario == "valid":
        row = parse_daily(data, "SYNTHETIC")[0]
        assert row["open"] == "99" and row["close"] == "100"
        assert "adjusted_close" not in row
    else:
        with pytest.raises(AppError):
            parse_daily(data, "SYNTHETIC")


def test_archive_schema_extension_cannot_hide_changed_evidence() -> None:
    row = ActionCoverageReview(action_types=["SPLIT", "DIVIDEND"], coverage_evidence=None)
    legacy = version_payload(row, "coverage", None)
    assert "action_types" not in legacy and "coverage_evidence" not in legacy
    fields = [c.name for c in row.__table__.columns]
    assert version_payload(row, "coverage", fields)["action_types"] == ["SPLIT", "DIVIDEND"]
    row.action_types = ["SPLIT"]
    with pytest.raises(AppError, match="non-default"):
        version_payload(row, "coverage", None)
    with pytest.raises(AppError):
        version_payload(row, "coverage", fields[:-1])
