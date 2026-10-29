"""The concrete ECB two-leg rights contract is enforced without live services."""

import asyncio
import hashlib
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from app.core.errors import AppError
from app.models import DataSource, RawIngestion
from app.providers.ecb_fx import ECB_INPUT_SCOPE, EcbFxCollector
from app.schemas.data_operations import CollectionInput
from app.services.backfill_jobs import BackfillJobService

START = END = date(2024, 1, 3)
SCOPE = f"private reference valuation {ECB_INPUT_SCOPE} fx_coverage=2024-01-01|2024-01-31"
BODY = (
    b"FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE\n"
    b"D,CHF,EUR,SP00,A,2024-01-03,0.93\n"
    b"D,USD,EUR,SP00,A,2024-01-03,1.1\n"
)


def reviewed_source() -> DataSource:
    now = datetime.now(UTC)
    return DataSource(
        id=uuid4(),
        slug="ECB",
        type="API",
        gate_status="APPROVED",
        enabled=True,
        checked_at=now,
        next_review_at=now + timedelta(days=1),
        terms_url="https://example.invalid/synthetic-terms",
        decision_by="synthetic-operator",
        scope=SCOPE,
        allowed_uses=["fx_rates", "raw_archive", "derived_analysis"],
        rate_limit_per_minute=1,
    )


@pytest.mark.parametrize(
    "change",
    [
        "generic_legacy_text",
        "only_chf",
        "wrong_range",
        "malformed_range",
        "duplicate_inputs",
        "duplicate_range",
        "missing_archive_right",
        "missing_analysis_right",
    ],
)
def test_ecb_direct_collection_rejects_unreviewed_scope_before_http(change: str) -> None:
    async def run() -> None:
        source = reviewed_source()
        if change == "generic_legacy_text":
            source.scope = "private generic FX analysis from an earlier review"
        elif change == "only_chf":
            source.scope = SCOPE.replace(ECB_INPUT_SCOPE, "fx_inputs=EXR.D.CHF.EUR.SP00.A")
        elif change == "wrong_range":
            source.scope = SCOPE.replace("2024-01-01|2024-01-31", "2024-02-01|2024-02-02")
        elif change == "malformed_range":
            source.scope = SCOPE.replace("2024-01-01|2024-01-31", "not-a-date")
        elif change == "duplicate_inputs":
            source.scope += f" {ECB_INPUT_SCOPE}"
        elif change == "duplicate_range":
            source.scope += " fx_coverage=2024-01-01|2024-01-31"
        elif change == "missing_archive_right":
            source.allowed_uses = ["fx_rates", "derived_analysis"]
        else:
            source.allowed_uses = ["fx_rates", "raw_archive"]
        original_scope = source.scope
        db, raw = MagicMock(), MagicMock()
        raw.store = AsyncMock()
        with (
            patch("app.services.sources.SourceService.get", new=AsyncMock(return_value=source)),
            patch("app.providers.http.provider_client") as create_client,
        ):
            with pytest.raises(AppError) as denied:
                await EcbFxCollector(db, raw_service=raw).collect(START, END)
        assert denied.value.code == "SOURCE_NOT_APPROVED"
        create_client.assert_not_called()
        raw.store.assert_not_awaited()
        assert source.scope == original_scope  # No old review is rewritten or auto-upgraded.

    asyncio.run(run())


@pytest.mark.parametrize("outside", [False, True])
def test_ecb_preview_checks_the_full_request_before_queueing(outside: bool) -> None:
    async def run() -> None:
        source = reviewed_source()
        user, db = MagicMock(), MagicMock()
        user.id, user.is_active = uuid4(), True
        db.refresh = AsyncMock()
        request = CollectionInput(
            source_slug="ECB",
            kind="ECB_FX",
            start=date(2024, 1, 1),
            end=date(2024, 2, 1) if outside else END,
        )
        with (
            patch("app.services.sources.SourceService.get", new=AsyncMock(return_value=source)),
            patch("app.services.backfill_jobs.require_data_operator"),
        ):
            operation = BackfillJobService(db, user).preview(request)
            if outside:
                with pytest.raises(AppError) as denied:
                    await operation
                assert denied.value.code == "SOURCE_NOT_APPROVED"
            else:
                result = await operation
                assert result["status"] == "READY"
                assert result["chunks"] == 1
        db.add.assert_not_called()
        db.commit.assert_not_called()

    asyncio.run(run())


@pytest.mark.parametrize("change", ["scope", "archive_right", "review"])
def test_ecb_retry_rechecks_rights_and_retains_the_first_rejected_original(change: str) -> None:
    async def run() -> None:
        source = reviewed_source()
        db, raw = MagicMock(), MagicMock()
        db.refresh = AsyncMock()
        calls: list[httpx.Request] = []
        stored: list[dict[str, object]] = []
        rejected = b"synthetic quota response retained before parsing"

        async def store(**values: object) -> RawIngestion:
            stored.append(values)
            return RawIngestion(
                id=uuid4(),
                source_id=source.id,
                sha256=hashlib.sha256(rejected).hexdigest(),
                received_at=datetime.now(UTC),
                http_status=429,
                request_metadata={},
            )

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return httpx.Response(
                429,
                content=rejected,
                headers={"content-type": "text/csv", "retry-after": "1"},
            )

        async def changed_review(_: object) -> None:
            if change == "scope":
                source.scope = "fx_inputs=EXR.D.CHF.EUR.SP00.A fx_coverage=2024-02-01|2024-02-02"
            elif change == "archive_right":
                source.allowed_uses = ["fx_rates", "derived_analysis"]
            else:
                source.checked_at = source.checked_at + timedelta(microseconds=1)

        raw.store = AsyncMock(side_effect=store)
        raw.get_verified = AsyncMock()
        limiter = AsyncMock()
        from app.providers.http import fetch_response

        async def offline_transport(*args: object, **kwargs: object) -> RawIngestion:
            return await fetch_response(*args, **kwargs, limiter=limiter)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.sources.SourceService.get", new=AsyncMock(return_value=source)),
                patch(
                    "app.services.provider_canonical.sync_state", new=AsyncMock(return_value=None)
                ),
                patch("app.providers.http.fetch_response", new=offline_transport),
                patch(
                    "app.providers.http.asyncio.sleep", new=AsyncMock(side_effect=changed_review)
                ),
            ):
                with pytest.raises(AppError) as denied:
                    await EcbFxCollector(db, client=client, raw_service=raw).collect(START, END)
        assert denied.value.code == "SOURCE_REVIEW_CHANGED"
        assert len(calls) == limiter.await_count == raw.store.await_count == 1
        assert stored[0]["data"] == rejected
        assert stored[0]["http_status"] == 429
        raw.get_verified.assert_not_awaited()

    asyncio.run(run())


def test_ecb_scope_is_rechecked_after_the_initial_sync_lookup() -> None:
    async def run() -> None:
        source = reviewed_source()
        db, raw = MagicMock(), MagicMock()
        raw.store = AsyncMock()

        async def changed_scope(*_: object) -> None:
            source.scope = "fx_inputs=EXR.D.CHF.EUR.SP00.A fx_coverage=2024-02-01|2024-02-02"

        with (
            patch("app.services.sources.SourceService.get", new=AsyncMock(return_value=source)),
            patch("app.services.provider_canonical.sync_state", new=changed_scope),
            patch("app.providers.http.provider_client") as create_client,
        ):
            with pytest.raises(AppError) as denied:
                await EcbFxCollector(db, raw_service=raw).collect(START, END)
        assert denied.value.code == "SOURCE_NOT_APPROVED"
        create_client.assert_not_called()
        raw.store.assert_not_awaited()

    asyncio.run(run())


def test_explicit_ecb_scope_keeps_both_real_request_parameters_and_archival_order() -> None:
    async def run() -> None:
        source = reviewed_source()
        db, raw = MagicMock(), MagicMock()
        db.refresh = AsyncMock()
        calls: list[httpx.Request] = []
        steps: list[str] = []
        raw_id = uuid4()

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return httpx.Response(200, content=BODY, headers={"content-type": "text/csv"})

        async def store(**values: object) -> RawIngestion:
            assert values["data"] == BODY
            steps.append("original_archived")
            return RawIngestion(
                id=raw_id,
                source_id=source.id,
                http_status=200,
                sha256=hashlib.sha256(BODY).hexdigest(),
                received_at=datetime.now(UTC),
                request_metadata={},
            )

        async def verified(identifier: object) -> bytes:
            assert identifier == raw_id and steps == ["original_archived"]
            steps.append("verified_before_parse")
            return BODY

        async def persist(*args: object) -> dict[str, object]:
            assert steps == ["original_archived", "verified_before_parse"]
            steps.append("canonical")
            return {"status": "SUCCESS", "observations": 2}

        raw.store, raw.get_verified = AsyncMock(side_effect=store), AsyncMock(side_effect=verified)
        from app.providers.http import fetch_response

        async def offline_transport(*args: object, **kwargs: object) -> RawIngestion:
            return await fetch_response(*args, **kwargs, limiter=AsyncMock())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with (
                patch("app.services.sources.SourceService.get", new=AsyncMock(return_value=source)),
                patch(
                    "app.services.provider_canonical.sync_state", new=AsyncMock(return_value=None)
                ),
                patch("app.services.provider_canonical.persist_fx", new=persist),
                patch("app.services.provider_canonical.save_sync", new=AsyncMock()),
                patch("app.providers.http.fetch_response", new=offline_transport),
            ):
                result = await EcbFxCollector(db, client=client, raw_service=raw).collect(
                    START, END
                )
        assert result == {"status": "SUCCESS", "observations": 2}
        assert steps == ["original_archived", "verified_before_parse", "canonical"]
        assert len(calls) == 1
        assert calls[0].url.path == "/service/data/EXR/D.CHF+USD.EUR.SP00.A"
        assert dict(calls[0].url.params) == {
            "startPeriod": "2024-01-03",
            "endPeriod": "2024-01-03",
            "format": "csvdata",
            "includeHistory": "false",
        }

    asyncio.run(run())
