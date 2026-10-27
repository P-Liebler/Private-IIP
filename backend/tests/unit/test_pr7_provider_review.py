import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from app.core.errors import AppError
from app.models import DataSource, RawIngestion
from app.providers.http import fetch_response


@pytest.mark.parametrize("change", ["scope", "review", "uses"])
def test_retry_cannot_reuse_a_replaced_approved_source_contract(change: str):
    async def run():
        now = datetime.now(UTC)
        source = DataSource(
            id=uuid4(),
            slug="TEST_PR7_REVIEW",
            type="API",
            checked_at=now,
            next_review_at=now + timedelta(days=1),
            terms_url="https://example.org/terms",
            decision_by="synthetic-operator",
            scope="series=EUR_CHF",
            gate_status="APPROVED",
            enabled=True,
            allowed_uses=["fx_rates"],
        )
        calls = []
        body = b'{"temporary":true}'

        def handler(request):
            calls.append(request)
            return httpx.Response(
                503, content=body, headers={"Content-Type": "application/json", "Retry-After": "1"}
            )

        async def operator_replaced_contract(_):
            # Even if the operator separately re-enables the newly approved
            # review, an old in-flight request must not inherit that new scope.
            if change == "scope":
                source.scope = "series=USD_CHF"
            elif change == "review":
                source.checked_at = now + timedelta(microseconds=1)
            else:
                source.allowed_uses = ["fx_rates", "prices"]

        raw, db, limiter = MagicMock(), MagicMock(), AsyncMock()
        db.refresh = AsyncMock()
        raw.store = AsyncMock(
            return_value=RawIngestion(
                id=uuid4(),
                source_id=source.id,
                received_at=now,
                sha256=hashlib.sha256(body).hexdigest(),
                http_status=503,
            )
        )
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with patch(
                "app.providers.http.asyncio.sleep",
                new=AsyncMock(side_effect=operator_replaced_contract),
            ):
                with pytest.raises(AppError) as error:
                    await fetch_response(
                        db,
                        raw,
                        source,
                        use="fx_rates",
                        url="https://example.org/fx",
                        allowed_host="example.org",
                        resource="synthetic-fx",
                        client=client,
                        limiter=limiter,
                    )
        assert error.value.code == "SOURCE_REVIEW_CHANGED"
        assert source.enabled and source.gate_status == "APPROVED"
        assert len(calls) == limiter.await_count == raw.store.await_count == 1
        assert raw.store.await_args.kwargs["data"] == body

    asyncio.run(run())
