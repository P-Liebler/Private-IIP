"""Synthetic format review, immutable raw data and idempotent ledger commit."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_engine, get_session
from app.main import create_app
from app.services.auth import AuthService
from app.services.market_import import MarketImportService
from app.services.raw_ingestion import RawIngestionService


@pytest.mark.integration
def test_explicit_format_review_is_required_and_commit_cannot_reinterpret(monkeypatch):
    class Storage:
        objects = {}

        def put(self, key, data, _content_type):
            self.objects[key] = data

        def get(self, key):
            return self.objects[key]

    storage = Storage()
    monkeypatch.setattr("app.services.raw_ingestion.get_storage", lambda: storage)

    async def run():
        try:
            async with get_engine().connect() as connection:
                outer = await connection.begin()
                try:
                    async with AsyncSession(
                        bind=connection,
                        join_transaction_mode="create_savepoint",
                        expire_on_commit=False,
                    ) as db:
                        username = "pr6_csv_synthetic_" + uuid4().hex[:10]
                        password = "synthetic-pr6-csv-test-password"
                        await AuthService(db).create_user(username, password)
                        app = create_app()

                        async def database():
                            yield db

                        app.dependency_overrides[get_session] = database
                        async with AsyncClient(
                            transport=ASGITransport(app=app),
                            base_url="http://testserver",
                            headers={"Origin": get_settings().frontend_origin},
                        ) as client:
                            assert (
                                await client.post(
                                    "/api/v1/auth/login",
                                    json={"username": username, "password": password},
                                )
                            ).status_code == 200
                            portfolio = (
                                await client.post(
                                    "/api/v1/portfolios",
                                    json={"name": "SYNTHETIC PR6 CSV", "base_currency": "CHF"},
                                )
                            ).json()["id"]
                            base = f"/api/v1/portfolios/{portfolio}"
                            account = (
                                await client.post(
                                    base + "/accounts", json={"name": "SYNTHETIC CSV"}
                                )
                            ).json()["id"]
                            original = (
                                b"\xef\xbb\xbftype;date;currency;amount;external_id\n"
                                b"DEPOSIT;01/02/2026;CHF;1'234.50;SYNTHETIC-PR6-1\n"
                            )
                            params = {"account_id": account}
                            response = await client.post(
                                base + "/transactions/import/preview",
                                params=params,
                                content=original,
                                headers={"Content-Type": "text/csv"},
                            )
                            assert response.status_code == 200, response.text
                            assert response.json()["format_required"] is True
                            assert original in storage.objects.values()
                            # CHF reporting revalues original flows at event-date FX;
                            # translating today's USD P&L would incorrectly yield zero.
                            today = datetime.now(UTC).date()
                            fx_csv = (
                                "date,base_currency,quote_currency,rate\n"
                                "2026-02-01,USD,CHF,0.8\n"
                                f"{today - timedelta(days=1)},USD,CHF,0.85\n"
                                f"{today},USD,CHF,0.9\n"
                            ).encode()
                            market = MarketImportService(db, RawIngestionService(db, storage))
                            fx_preview = await market.preview("fx", fx_csv, "SYNTHETIC-PR6-FX.csv")
                            await market.commit(
                                "fx",
                                fx_preview["raw_ingestion_id"],
                                fx_preview["mapping"],
                                conflict_policy="ACCEPT_NEW",
                                decision_note="Synthetic isolated rollback test",
                            )
                            usd = (
                                await client.post(
                                    "/api/v1/portfolios",
                                    json={"name": "SYNTHETIC USD", "base_currency": "USD"},
                                )
                            ).json()["id"]
                            usd_account = (
                                await client.post(
                                    f"/api/v1/portfolios/{usd}/accounts",
                                    json={"name": "SYNTHETIC USD"},
                                )
                            ).json()["id"]
                            assert (
                                await client.post(
                                    f"/api/v1/portfolios/{usd}/transactions",
                                    json={
                                        "account_id": usd_account,
                                        "type": "DEPOSIT",
                                        "trade_date": "2026-02-01",
                                        "currency": "USD",
                                        "amount": "100",
                                    },
                                )
                            ).status_code == 201
                            summary = (await client.get("/api/v1/portfolio-dashboard")).json()
                            chf = summary["chf_summary"]
                            assert Decimal(chf["total_value_base"]) == Decimal("90")
                            assert Decimal(chf["total_return_base"]) == Decimal("10")
                            assert Decimal(chf["daily_change_base"]) == Decimal("5")
                            native = next(
                                g for g in summary["groups"] if g["base_currency"] == "USD"
                            )
                            assert Decimal(native["total_value_base"]) == Decimal("100")
                            assert Decimal(native["total_return_base"]) == Decimal("0")
                            config = {"delimiter": ";", "date_format": "DMY", "number_format": "CH"}
                            response = await client.post(
                                base + "/transactions/import/preview",
                                params=params | {"csv_format": json.dumps(config)},
                                content=original,
                                headers={"Content-Type": "text/csv"},
                            )
                            assert response.status_code == 200, response.text
                            preview = response.json()
                            assert preview["rows"][0]["trade_date"] == "2026-02-01"
                            assert preview["rows"][0]["amount"] == "1234.50"
                            request = {
                                "account_id": account,
                                "raw_ingestion_id": preview["raw_ingestion_id"],
                                "mapping": preview["mapping"],
                                "csv_format": config,
                            }
                            changed = await client.post(
                                base + "/transactions/import/commit",
                                json=request | {"csv_format": config | {"date_format": "MDY"}},
                            )
                            assert changed.status_code == 409
                            assert changed.json()["error"]["code"] == "IMPORT_PREVIEW_CHANGED"
                            assert (await client.get(base + "/transactions")).json() == []
                            committed = await client.post(
                                base + "/transactions/import/commit", json=request
                            )
                            assert committed.status_code == 200, committed.text
                            assert committed.json()["created_count"] == 1
                            assert (
                                await client.post(
                                    base + "/transactions/import/commit", json=request
                                )
                            ).json()["created_count"] == 0
                            assert len((await client.get(base + "/transactions")).json()) == 1
                            assert original in storage.objects.values()
                            key = str(uuid4())
                            manual = {
                                "account_id": account,
                                "type": "DEPOSIT",
                                "trade_date": "2026-02-02",
                                "currency": "CHF",
                                "amount": "1",
                            }
                            headers = {"Idempotency-Key": key}
                            first = await client.post(
                                base + "/transactions", json=manual, headers=headers
                            )
                            assert first.status_code == 201, first.text
                            repeated = await client.post(
                                base + "/transactions", json=manual, headers=headers
                            )
                            assert repeated.json()["id"] == first.json()["id"]
                            conflict = await client.post(
                                base + "/transactions",
                                json=manual | {"amount": "2"},
                                headers=headers,
                            )
                            assert conflict.status_code == 409
                            assert conflict.json()["error"]["code"] == "REQUEST_KEY_CONFLICT"
                            assert len((await client.get(base + "/transactions")).json()) == 2
                            receipt_key = {"Idempotency-Key": str(uuid4())}
                            body = {"name": "SYNTHETIC PR6 retry", "base_currency": "CHF"}
                            created = await client.post(
                                "/api/v1/portfolios", json=body, headers=receipt_key
                            )
                            assert created.status_code == 201, created.text
                            repeated = await client.post(
                                "/api/v1/portfolios", json=body, headers=receipt_key
                            )
                            assert repeated.json()["id"] == created.json()["id"]
                            assert (
                                await client.post(
                                    "/api/v1/portfolios",
                                    json=body | {"name": "changed"},
                                    headers=receipt_key,
                                )
                            ).status_code == 409
                            retry_account_url = (
                                f"/api/v1/portfolios/{created.json()['id']}/accounts"
                            )
                            account_key = {"Idempotency-Key": str(uuid4())}
                            first_account = await client.post(
                                retry_account_url,
                                json={"name": "SYNTHETIC retry account"},
                                headers=account_key,
                            )
                            assert first_account.status_code == 201, first_account.text
                            repeat_account = await client.post(
                                retry_account_url,
                                json={"name": "SYNTHETIC retry account"},
                                headers=account_key,
                            )
                            assert repeat_account.json()["id"] == first_account.json()["id"]
                            assert len((await client.get(retry_account_url)).json()) == 1
                            assert (
                                await client.delete("/api/v1/transactions/" + first.json()["id"])
                            ).status_code == 200
                            retry_voided = await client.post(
                                base + "/transactions", json=manual, headers=headers
                            )
                            assert retry_voided.json()["status"] == "VOIDED"
                            assert len((await client.get(base + "/transactions")).json()) == 2
                finally:
                    await outer.rollback()
        finally:
            await get_engine().dispose()

    asyncio.run(run())
