"""Synthetic private-beta workflow; real local PostgreSQL, no provider network."""

import asyncio
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_engine, get_session
from app.main import create_app
from app.models import Instrument, InstrumentIdentifier
from app.services.auth import AuthService
from app.services.market_import import MarketImportService
from app.services.raw_ingestion import RawIngestionService


class MemoryStorage:
    def __init__(self):
        self.objects = {}

    def put(self, key, data, _content_type):
        self.objects[key] = data

    def get(self, key):
        return self.objects[key]


@pytest.mark.integration
def test_pr5_reviewed_import_correction_opening_and_readonly_reconciliation(monkeypatch):
    storage = MemoryStorage()
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
                        username = "pr5_synthetic_" + uuid4().hex[:12]
                        password = "synthetic-pr5-test-password-2"
                        await AuthService(db).create_user(username, password)
                        day = date(2025, 1, 6)
                        ticker = "P5" + uuid4().hex[:8].upper()
                        first, second = uuid4(), uuid4()

                        async def add_instrument(iid, mic, currency):
                            db.add(
                                Instrument(
                                    id=iid,
                                    name=f"SYNTHETIC PR5 {mic}",
                                    asset_type="STOCK",
                                    currency=currency,
                                    ticker=ticker,
                                    mic=mic,
                                )
                            )
                            db.add(
                                InstrumentIdentifier(
                                    instrument_id=iid,
                                    type="TICKER",
                                    value=ticker,
                                    market_key=mic,
                                    valid_from=day,
                                    observed_at=datetime.now(UTC),
                                )
                            )
                            await db.commit()

                        await add_instrument(first, "XSWX", "CHF")
                        market = MarketImportService(db, RawIngestionService(db, storage))
                        price = await market.preview(
                            "prices",
                            f"date,ticker,close,currency\n{day},{ticker},15,CHF\n".encode(),
                            "SYNTHETIC-price.csv",
                        )
                        await market.commit("prices", price["raw_ingestion_id"], price["mapping"])
                        await add_instrument(second, "XNYS", "USD")
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
                                    json={"name": "SYNTHETIC PR5", "base_currency": "CHF"},
                                )
                            ).json()["id"]
                            base = f"/api/v1/portfolios/{portfolio}"
                            account = (
                                await client.post(
                                    base + "/accounts", json={"name": "SYNTHETIC broker"}
                                )
                            ).json()["id"]
                            assert (
                                await client.post(
                                    base + "/transactions",
                                    json={
                                        "account_id": account,
                                        "type": "DEPOSIT",
                                        "trade_date": str(day),
                                        "amount": "500",
                                        "currency": "CHF",
                                    },
                                )
                            ).status_code == 201
                            contents = (
                                "type,trade_date,ticker,quantity,price,currency,fee,tax,external_id\n"
                                f"BUY,{day},{ticker},2,10,CHF,1,2,SYNTHETIC-ORDER-1\n"
                            )

                            async def preview(data, choices=None, mapping=None):
                                params = {"account_id": account}
                                if choices is not None:
                                    params["instrument_resolutions"] = json.dumps(choices)
                                if mapping is not None:
                                    params["column_mapping"] = json.dumps(mapping)
                                response = await client.post(
                                    base + "/transactions/import/preview",
                                    params=params,
                                    content=data.encode(),
                                    headers={"Content-Type": "text/csv"},
                                )
                                assert response.status_code == 200, response.text
                                return response.json()

                            ambiguous = await preview(contents)
                            assert ambiguous["rows"][0]["status"] == "INVALID"
                            assert "AMBIGUOUS" in ambiguous["rows"][0]["error"]
                            choices = {"2": str(first)}
                            reviewed = await preview(contents, choices, ambiguous["mapping"])
                            assert (
                                reviewed["ready_count"] == 1 and reviewed["rows"][0]["fee"] == "1"
                            )
                            request = {
                                "account_id": account,
                                "raw_ingestion_id": reviewed["raw_ingestion_id"],
                                "mapping": reviewed["mapping"],
                                "instrument_resolutions": choices,
                            }
                            altered = await client.post(
                                base + "/transactions/import/commit",
                                json=request | {"instrument_resolutions": {"2": str(second)}},
                            )
                            assert (
                                altered.status_code == 409
                                and altered.json()["error"]["code"] == "IMPORT_PREVIEW_CHANGED"
                            )
                            committed = await client.post(
                                base + "/transactions/import/commit", json=request
                            )
                            assert committed.status_code == 200, committed.text
                            trade_id = committed.json()["transaction_ids"][0]
                            assert (
                                await client.post(
                                    base + "/transactions/import/commit", json=request
                                )
                            ).json()["created_count"] == 0
                            repeated = await preview(contents, choices)
                            assert repeated["rows"][0]["status"] == "DUPLICATE"
                            repeated_request = request | {
                                "raw_ingestion_id": repeated["raw_ingestion_id"],
                                "mapping": repeated["mapping"],
                            }
                            assert (
                                await client.post(
                                    base + "/transactions/import/commit", json=repeated_request
                                )
                            ).json()["created_count"] == 0
                            conflict = await preview(
                                contents.replace(",2,10,CHF", ",2,11,CHF"), choices
                            )
                            assert conflict["rows"][0]["status"] == "CONFLICT"
                            corrected = await client.patch(
                                f"/api/v1/transactions/{trade_id}",
                                json={
                                    "account_id": account,
                                    "instrument_id": str(first),
                                    "type": "BUY",
                                    "trade_date": str(day),
                                    "quantity": "2",
                                    "price": "12",
                                    "currency": "CHF",
                                    "fee": "1",
                                    "tax": "2",
                                    "external_id": "SYNTHETIC-ORDER-1",
                                },
                            )
                            assert corrected.status_code == 200, corrected.text
                            original = await preview(contents, choices)
                            assert original["rows"][0]["status"] == "DUPLICATE"
                            assert (
                                await client.post(
                                    base + "/transactions/import/commit",
                                    json=request
                                    | {
                                        "raw_ingestion_id": original["raw_ingestion_id"],
                                        "mapping": original["mapping"],
                                    },
                                )
                            ).json()["created_count"] == 0
                            transactions_before = (await client.get(base + "/transactions")).json()
                            assert (
                                len(
                                    [
                                        t
                                        for t in transactions_before
                                        if t["type"] == "BUY" and t["status"] == "ACTIVE"
                                    ]
                                )
                                == 1
                            )
                            value = (
                                await client.get(base + "/valuation", params={"on_date": str(day)})
                            ).json()
                            assert Decimal(str(value["total_value_base"])) == 503
                            statement = {
                                "account_id": account,
                                "statement_date": str(day),
                                "source_reference": "SYNTHETIC statement PR5",
                                "complete_statement": True,
                                "positions": [
                                    {
                                        "instrument_id": str(first),
                                        "quantity": "2",
                                        "currency": "CHF",
                                        "reported_market_value": "30",
                                    }
                                ],
                                "cash": [{"currency": "CHF", "amount": "473"}],
                                "reported_value_base": "503",
                            }
                            compared = await client.post(base + "/reconciliation", json=statement)
                            assert compared.status_code == 200, compared.text
                            assert (
                                compared.json()["status"] == "MATCHED_ENTERED_FIELDS"
                                and compared.json()["ledger_changed"] is False
                            )
                            changed = await client.post(
                                base + "/reconciliation",
                                json=statement | {"cash": [{"currency": "CHF", "amount": "472"}]},
                            )
                            assert changed.json()["status"] == "DIFFERENCES_FOUND"
                            assert (
                                await client.get(base + "/transactions")
                            ).json() == transactions_before
                            stale = await client.post(
                                base + "/reconciliation",
                                json=statement | {"statement_date": str(datetime.now(UTC).date())},
                            )
                            assert (
                                stale.json()["status"] == "PARTIAL"
                                and stale.json()["calculated_value_base"] is None
                            )
                            opening_portfolio = (
                                await client.post(
                                    "/api/v1/portfolios",
                                    json={"name": "SYNTHETIC opening", "base_currency": "CHF"},
                                )
                            ).json()["id"]
                            opening_base = f"/api/v1/portfolios/{opening_portfolio}"
                            opening_account = (
                                await client.post(
                                    opening_base + "/accounts",
                                    json={"name": "SYNTHETIC opening account"},
                                )
                            ).json()["id"]
                            opened = await client.post(
                                opening_base + "/transactions",
                                json={
                                    "account_id": opening_account,
                                    "instrument_id": str(first),
                                    "type": "OPENING_POSITION",
                                    "trade_date": str(day),
                                    "quantity": "3",
                                    "currency": "CHF",
                                    "notes": "SYNTHETIC opening statement; original cost unknown",
                                },
                            )
                            assert opened.status_code == 201, opened.text
                            opening_value = (
                                await client.get(
                                    opening_base + "/valuation", params={"on_date": str(day)}
                                )
                            ).json()
                            assert Decimal(str(opening_value["total_value_base"])) == 45
                            assert opening_value["holdings"][0]["cost_basis_native"] is None
                            assert opening_value["unrealized_pnl_base_at_valuation_fx"] is None
                            summary = (await client.get(opening_base + "/summary")).json()
                            assert summary["total_return_base"] is None
                finally:
                    await outer.rollback()
        finally:
            await get_engine().dispose()

    asyncio.run(run())
