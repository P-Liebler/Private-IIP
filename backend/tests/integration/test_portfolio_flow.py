from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, or_, select

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.main import create_app
from app.models import (
    AuditEvent,
    Benchmark,
    CashBalance,
    CorporateAction,
    CorporateActionVersion,
    DataQuarantine,
    FxRate,
    FxRateVersion,
    Instrument,
    InstrumentIdentifier,
    Portfolio,
    PortfolioAccount,
    PortfolioActionApplication,
    PortfolioSnapshot,
    PositionSnapshot,
    PriceDaily,
    PriceDailyVersion,
    RawIngestion,
    SessionRecord,
    Transaction,
    User,
)
from app.services.auth import AuthService
from app.services.market_import import MarketImportService
from app.services.raw_ingestion import RawIngestionService


class MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, _content_type: str) -> None:
        self.objects[key] = data

    def get(self, key: str) -> bytes:
        return self.objects[key]


@pytest.mark.integration
def test_login_portfolio_missing_fx_then_complete_valuation() -> None:
    async def run() -> None:
        username = "portfolio_" + uuid4().hex[:12]
        ticker = "P" + uuid4().hex[:10].upper()
        password = "test-only-portfolio-password-2"
        instrument_id = uuid4()
        day = date(2025, 2, 3)
        raw_ids = []
        portfolio_id = None
        extra_portfolio_id = None
        user_id = None
        other_user_id = None
        benchmark_id = None
        async with get_session_factory()() as db:
            try:
                user = await AuthService(db).create_user(username, password)
                user_id = user.id
                db.add(
                    Instrument(
                        id=instrument_id,
                        name="P4 golden test",
                        asset_type="STOCK",
                        currency="USD",
                        ticker=ticker,
                    )
                )
                db.add(
                    InstrumentIdentifier(
                        instrument_id=instrument_id,
                        type="TICKER",
                        value=ticker,
                        market_key="",
                        valid_from=day,
                        observed_at=datetime.now(UTC),
                    )
                )
                await db.commit()
                market = MarketImportService(db, RawIngestionService(db, MemoryStorage()))
                price = await market.preview(
                    "prices",
                    (f"date,ticker,close,currency\n{day},{ticker},120,USD\n").encode(),
                    "p4-price.csv",
                )
                raw_ids.append(price["raw_ingestion_id"])
                async with AsyncClient(
                    transport=ASGITransport(app=create_app()),
                    base_url="http://testserver",
                    headers={"Origin": get_settings().frontend_origin},
                ) as client:
                    assert (
                        await client.post(
                            "/api/v1/auth/login", json={"username": username, "password": password}
                        )
                    ).status_code == 200
                    created = await client.post(
                        "/api/v1/portfolios",
                        json={"name": "Golden Portfolio", "base_currency": "CHF"},
                    )
                    assert created.status_code == 201, created.text
                    portfolio_id = created.json()["id"]
                    before_existence = await client.get(
                        f"/api/v1/portfolios/{portfolio_id}/valuation",
                        params={"on_date": "2024-01-01", "as_of": "2024-01-02T00:00:00Z"},
                    )
                    assert (
                        before_existence.status_code == 422
                        and before_existence.json()["error"]["code"]
                        == "PORTFOLIO_NOT_AVAILABLE_AS_OF"
                    )
                    account = await client.post(
                        f"/api/v1/portfolios/{portfolio_id}/accounts",
                        json={"name": "Broker", "account_type": "BROKER"},
                    )
                    assert account.status_code == 201, account.text
                    account_id = account.json()["id"]
                    deposit = await client.post(
                        f"/api/v1/portfolios/{portfolio_id}/transactions",
                        json={
                            "account_id": account_id,
                            "type": "DEPOSIT",
                            "trade_date": str(day),
                            "amount": "10000",
                            "currency": "CHF",
                        },
                    )
                    assert deposit.status_code == 201, deposit.text
                    buy = await client.post(
                        f"/api/v1/portfolios/{portfolio_id}/transactions",
                        json={
                            "account_id": account_id,
                            "instrument_id": str(instrument_id),
                            "type": "BUY",
                            "trade_date": str(day),
                            "quantity": "10",
                            "price": "100",
                            "currency": "USD",
                        },
                    )
                    assert buy.status_code == 201, buy.text
                    absent_price = await client.get(
                        f"/api/v1/portfolios/{portfolio_id}/valuation", params={"on_date": str(day)}
                    )
                    assert absent_price.json()["total_value_base"] is None
                    assert absent_price.json()["holdings"][0]["market_value_native"] is None
                    assert any(
                        issue["code"] == "MISSING_PRICE" for issue in absent_price.json()["issues"]
                    )
                    assert Decimal(absent_price.json()["cash"][0]["amount"]) == 10000
                    assert (
                        await market.commit("prices", price["raw_ingestion_id"], price["mapping"])
                    )["inserted"] == 1
                    missing = await client.get(
                        f"/api/v1/portfolios/{portfolio_id}/valuation", params={"on_date": str(day)}
                    )
                    assert missing.status_code == 200, missing.text
                    assert missing.json()["status"] == "PARTIAL"
                    assert missing.json()["total_value_base"] is None
                    assert any(issue["code"] == "MISSING_FX" for issue in missing.json()["issues"])
                    fx = await market.preview(
                        "fx",
                        (f"date,base_currency,quote_currency,rate\n{day},USD,CHF,0.9\n").encode(),
                        "p4-fx.csv",
                    )
                    raw_ids.append(fx["raw_ingestion_id"])
                    assert (await market.commit("fx", fx["raw_ingestion_id"], fx["mapping"]))[
                        "inserted"
                    ] == 1
                    valued = await client.get(
                        f"/api/v1/portfolios/{portfolio_id}/valuation", params={"on_date": str(day)}
                    )
                    assert valued.status_code == 200, valued.text
                    payload = valued.json()
                    assert payload["status"] == "COMPLETE"
                    assert Decimal(payload["total_value_base"]) == Decimal(10180)
                    assert Decimal(payload["holdings"][0]["unrealized_pnl_native"]) == Decimal(200)
                    allocation = await client.get(
                        f"/api/v1/portfolios/{portfolio_id}/allocation",
                        params={"on_date": str(day)},
                    )
                    assert (
                        allocation.status_code == 200 and allocation.json()["status"] == "AVAILABLE"
                    )
                    assert allocation.json()["by_currency"]
                    snapshot = await client.post(
                        f"/api/v1/portfolios/{portfolio_id}/snapshots/{day}"
                    )
                    assert snapshot.status_code == 200 and Decimal(
                        snapshot.json()["value_base"]
                    ) == Decimal(10180)
                    assert snapshot.json()["knowledge_cutoff"] is not None
                    stored_snapshot = await db.scalar(
                        select(PortfolioSnapshot).where(
                            PortfolioSnapshot.id == snapshot.json()["id"]
                        )
                    )
                    assert stored_snapshot.input_provenance is not None
                    assert len(stored_snapshot.input_provenance["transactions"]) == 2
                    transactions = await client.get(
                        f"/api/v1/portfolios/{portfolio_id}/transactions"
                    )
                    assert len(transactions.json()) == 2
                    # Ownership applies to reads and mutations across every resource level.
                    other = await AuthService(db).create_user("other_" + uuid4().hex[:12], password)
                    other_user_id = other.id
                    async with AsyncClient(
                        transport=ASGITransport(app=create_app()),
                        base_url="http://testserver",
                        headers={"Origin": get_settings().frontend_origin},
                    ) as outsider:
                        assert (
                            await outsider.post(
                                "/api/v1/auth/login",
                                json={"username": other.username, "password": password},
                            )
                        ).status_code == 200
                        for path in (
                            f"/portfolios/{portfolio_id}",
                            f"/portfolios/{portfolio_id}/valuation",
                            f"/portfolios/{portfolio_id}/accounts",
                            f"/portfolios/{portfolio_id}/transactions",
                            f"/portfolios/{portfolio_id}/snapshots",
                        ):
                            assert (await outsider.get("/api/v1" + path)).status_code == 404
                        assert (
                            await outsider.patch(
                                f"/api/v1/accounts/{account_id}", json={"name": "stolen"}
                            )
                        ).status_code == 404
                        assert (
                            await outsider.delete(f"/api/v1/transactions/{buy.json()['id']}")
                        ).status_code == 404
                        assert (
                            await outsider.post(
                                f"/api/v1/portfolios/{portfolio_id}/transactions",
                                json={
                                    "account_id": account_id,
                                    "type": "DEPOSIT",
                                    "trade_date": str(day),
                                    "amount": "1",
                                    "currency": "CHF",
                                },
                            )
                        ).status_code == 404
                    stale = await client.get(
                        f"/api/v1/portfolios/{portfolio_id}/valuation",
                        params={"on_date": str(day + timedelta(days=10))},
                    )
                    assert stale.json()["total_value_base"] is None
                    assert any(issue["code"] == "STALE_PRICE" for issue in stale.json()["issues"])
                    repeat = await client.post(f"/api/v1/portfolios/{portfolio_id}/snapshots/{day}")
                    assert repeat.json()["id"] == snapshot.json()["id"]
                    before_correction = datetime.now(UTC)
                    replacement = await client.patch(
                        f"/api/v1/transactions/{buy.json()['id']}",
                        json={
                            "account_id": account_id,
                            "instrument_id": str(instrument_id),
                            "type": "BUY",
                            "trade_date": str(day),
                            "quantity": "10",
                            "price": "110",
                            "currency": "USD",
                        },
                    )
                    assert (
                        replacement.status_code == 200
                        and replacement.json()["replaces_transaction_id"] == buy.json()["id"]
                    )
                    old_value = await client.get(
                        f"/api/v1/portfolios/{portfolio_id}/valuation",
                        params={"on_date": str(day), "as_of": before_correction.isoformat()},
                    )
                    current_value = await client.get(
                        f"/api/v1/portfolios/{portfolio_id}/valuation", params={"on_date": str(day)}
                    )
                    assert Decimal(old_value.json()["total_value_base"]) == Decimal(10180)
                    assert Decimal(current_value.json()["total_value_base"]) == Decimal(10090)
                    assert (
                        await client.delete(f"/api/v1/transactions/{replacement.json()['id']}")
                    ).status_code == 200
                    empty = await client.get(
                        f"/api/v1/portfolios/{portfolio_id}/valuation", params={"on_date": str(day)}
                    )
                    assert empty.json()["holdings"] == [] and Decimal(
                        empty.json()["total_value_base"]
                    ) == Decimal(10000)
                    # Raw-first CSV; identifiers resolve using their validity on the trade date.
                    csv_data = (
                        "type,date,ticker,qty,price,ccy,external_id\n"
                        f"BUY,{day},{ticker},10,100,USD,broker-001\n"
                    )
                    before_count = len(
                        (await client.get(f"/api/v1/portfolios/{portfolio_id}/transactions")).json()
                    )
                    preview = await client.post(
                        f"/api/v1/portfolios/{portfolio_id}/transactions/import/preview",
                        params={"account_id": account_id},
                        content=csv_data,
                        headers={"Content-Type": "text/csv"},
                    )
                    assert preview.status_code == 200 and preview.json()["ready_count"] == 1, (
                        preview.text
                    )
                    raw_ids.append(preview.json()["raw_ingestion_id"])
                    assert (
                        len(
                            (
                                await client.get(f"/api/v1/portfolios/{portfolio_id}/transactions")
                            ).json()
                        )
                        == before_count
                    )
                    committed = await client.post(
                        f"/api/v1/portfolios/{portfolio_id}/transactions/import/commit",
                        json={
                            "account_id": account_id,
                            "raw_ingestion_id": preview.json()["raw_ingestion_id"],
                            "mapping": preview.json()["mapping"],
                        },
                    )
                    assert (
                        committed.status_code == 200 and committed.json()["created_count"] == 1
                    ), committed.text
                    duplicate = await client.post(
                        f"/api/v1/portfolios/{portfolio_id}/transactions/import/preview",
                        params={"account_id": account_id},
                        content=csv_data,
                        headers={"Content-Type": "text/csv"},
                    )
                    raw_ids.append(duplicate.json()["raw_ingestion_id"])
                    assert duplicate.json()["rows"][0]["status"] == "DUPLICATE"
                    bad_csv = (
                        "type,date,ticker,qty,price,ccy,external_id\n"
                        f"BUY,{day},{ticker},1,100,USD,atomic-buy\n"
                        f"SELL,{day},{ticker},999,100,USD,atomic-sell\n"
                    )
                    count_before = len(
                        (await client.get(f"/api/v1/portfolios/{portfolio_id}/transactions")).json()
                    )
                    bad_preview = await client.post(
                        f"/api/v1/portfolios/{portfolio_id}/transactions/import/preview",
                        params={"account_id": account_id},
                        content=bad_csv,
                        headers={"Content-Type": "text/csv"},
                    )
                    raw_ids.append(bad_preview.json()["raw_ingestion_id"])
                    assert bad_preview.json()["rows"][1]["status"] == "INVALID"
                    bad_commit = await client.post(
                        f"/api/v1/portfolios/{portfolio_id}/transactions/import/commit",
                        json={
                            "account_id": account_id,
                            "raw_ingestion_id": bad_preview.json()["raw_ingestion_id"],
                            "mapping": bad_preview.json()["mapping"],
                        },
                    )
                    assert (
                        bad_commit.status_code == 409
                        and bad_commit.json()["error"]["code"] == "INSUFFICIENT_POSITION"
                    )
                    assert (
                        len(
                            (
                                await client.get(f"/api/v1/portfolios/{portfolio_id}/transactions")
                            ).json()
                        )
                        == count_before
                    )

                    async def import_market(kind, contents, review=False):
                        imported = await market.preview(kind, contents.encode(), f"p4-{kind}.csv")
                        raw_ids.append(imported["raw_ingestion_id"])
                        result = await market.commit(
                            kind,
                            imported["raw_ingestion_id"],
                            imported["mapping"],
                            conflict_policy="ACCEPT_NEW" if review else "REJECT",
                            decision_note="Explicit fixture correction reviewed"
                            if review
                            else None,
                        )
                        assert result["inserted"] + result["corrected"] > 0

                    await import_market(
                        "actions",
                        "date,ticker,action_type,value,currency\n"
                        f"{day + timedelta(days=1)},{ticker},SPLIT,2,\n"
                        f"{day + timedelta(days=2)},{ticker},DIVIDEND,1,USD\n",
                    )
                    action_rows = (
                        await db.scalars(
                            select(CorporateActionVersion).where(
                                CorporateActionVersion.instrument_id == instrument_id
                            )
                        )
                    ).all()
                    actions = {row.action_type: str(row.id) for row in action_rows}

                    async def apply(action_id):
                        return await client.post(
                            f"/api/v1/portfolios/{portfolio_id}/corporate-actions/apply",
                            json={
                                "account_id": account_id,
                                "action_version_id": action_id,
                                "fee": "0",
                                "tax": "0",
                            },
                        )

                    unconfirmed = await client.post(
                        f"/api/v1/portfolios/{portfolio_id}/corporate-actions/apply",
                        json={"account_id": account_id, "action_version_id": actions["DIVIDEND"]},
                    )
                    assert (
                        unconfirmed.status_code == 409
                        and unconfirmed.json()["error"]["code"] == "ACTION_COST_REVIEW_REQUIRED"
                    )
                    preview_action = await client.get(
                        f"/api/v1/portfolios/{portfolio_id}/corporate-actions/{actions['DIVIDEND']}/preview",
                        params={"account_id": account_id},
                    )
                    assert (
                        preview_action.status_code == 200
                        and preview_action.json()["cost_confirmation_required"] is True
                    )
                    assert (await apply(actions["DIVIDEND"])).json()["error"][
                        "code"
                    ] == "ACTION_DEPENDENCY_UNAPPLIED"
                    applied_split = await apply(actions["SPLIT"])
                    assert applied_split.status_code == 200, applied_split.text
                    assert (await apply(actions["SPLIT"])).json()["id"] == applied_split.json()[
                        "id"
                    ]
                    applied_dividend = await apply(actions["DIVIDEND"])
                    assert applied_dividend.status_code == 200, applied_dividend.text
                    assert (await apply(actions["DIVIDEND"])).json()[
                        "id"
                    ] == applied_dividend.json()["id"]
                    changed_cost = await client.post(
                        f"/api/v1/portfolios/{portfolio_id}/corporate-actions/apply",
                        json={
                            "account_id": account_id,
                            "action_version_id": actions["DIVIDEND"],
                            "fee": "0",
                            "tax": "1",
                        },
                    )
                    assert (
                        changed_cost.status_code == 409
                        and changed_cost.json()["error"]["code"] == "ACTION_CORRECTION_REVIEW"
                    )
                    manual_duplicate = await client.post(
                        f"/api/v1/portfolios/{portfolio_id}/transactions",
                        json={
                            "account_id": account_id,
                            "instrument_id": str(instrument_id),
                            "type": "DIVIDEND",
                            "trade_date": str(day + timedelta(days=2)),
                            "amount": "20",
                            "currency": "USD",
                        },
                    )
                    assert (
                        manual_duplicate.status_code == 409
                        and manual_duplicate.json()["error"]["code"] == "DUPLICATE_ACTION_EFFECT"
                    )
                    waiting_for_close = (
                        await client.get(
                            f"/api/v1/portfolios/{portfolio_id}/valuation",
                            params={"on_date": str(day + timedelta(days=2))},
                        )
                    ).json()
                    assert waiting_for_close["total_value_base"] is None
                    assert waiting_for_close["holdings"][0]["market_value_native"] is None
                    assert any(
                        issue["code"] == "MISSING_EVENT_PRICE"
                        for issue in waiting_for_close["issues"]
                    )
                    partial_snapshot = await client.post(
                        f"/api/v1/portfolios/{portfolio_id}/snapshots/{day + timedelta(days=2)}"
                    )
                    assert (
                        partial_snapshot.status_code == 200
                        and partial_snapshot.json()["status"] == "PARTIAL"
                    )
                    assert partial_snapshot.json()["value_base"] is None
                    end = day + timedelta(days=3)
                    await import_market(
                        "prices",
                        "date,ticker,close,currency\n"
                        f"{day + timedelta(days=1)},{ticker},60,USD\n"
                        f"{day + timedelta(days=2)},{ticker},60,USD\n"
                        f"{end},{ticker},65,USD\n",
                    )
                    sold = await client.post(
                        f"/api/v1/portfolios/{portfolio_id}/transactions",
                        json={
                            "account_id": account_id,
                            "instrument_id": str(instrument_id),
                            "type": "SELL",
                            "trade_date": str(end),
                            "quantity": "5",
                            "price": "65",
                            "fee": "1",
                            "tax": "1",
                            "currency": "USD",
                        },
                    )
                    assert sold.status_code == 201, sold.text
                    final = (
                        await client.get(
                            f"/api/v1/portfolios/{portfolio_id}/valuation",
                            params={"on_date": str(end)},
                        )
                    ).json()
                    assert final["status"] == "COMPLETE" and Decimal(
                        final["total_value_base"]
                    ) == Decimal("10286.2")
                    assert Decimal(final["holdings"][0]["quantity"]) == 15
                    assert Decimal(final["holdings"][0]["cost_basis_native"]) == 750
                    assert Decimal(final["realized_pnl_base_at_trade_fx"]) == Decimal("65.7")
                    assert Decimal(final["income_base_at_event_fx"]) == 18
                    before_price_correction = datetime.now(UTC)
                    await import_market(
                        "prices",
                        f"date,ticker,close,currency\n{end},{ticker},66,USD\n",
                        review=True,
                    )
                    historical = (
                        await client.get(
                            f"/api/v1/portfolios/{portfolio_id}/valuation",
                            params={
                                "on_date": str(end),
                                "as_of": before_price_correction.isoformat(),
                            },
                        )
                    ).json()
                    revised = (
                        await client.get(
                            f"/api/v1/portfolios/{portfolio_id}/valuation",
                            params={"on_date": str(end)},
                        )
                    ).json()
                    assert Decimal(historical["total_value_base"]) == Decimal("10286.2")
                    assert Decimal(revised["total_value_base"]) == Decimal("10299.7")
                    benchmark = await client.post(
                        "/api/v1/benchmarks", json={"instrument_id": str(instrument_id)}
                    )
                    benchmark_id = benchmark.json()["id"]
                    assert (
                        await client.patch(
                            f"/api/v1/portfolios/{portfolio_id}",
                            json={"benchmark_id": benchmark_id},
                        )
                    ).status_code == 200
                    result = (
                        await client.get(
                            f"/api/v1/portfolios/{portfolio_id}/performance",
                            params={"start": str(day), "end": str(end)},
                        )
                    ).json()
                    assert result["status"] == "AVAILABLE", result
                    assert abs(
                        Decimal(result["twr"]) - (Decimal("10299.7") / Decimal(10180) - 1)
                    ) < Decimal("0.00000001")
                    assert abs(
                        Decimal(result["benchmark"]["return_base"])
                        - (Decimal(134) / Decimal(120) - 1)
                    ) < Decimal("0.00000001")
                    assert result["benchmark"]["status"] == "PROVISIONAL"
                    manual_day = day + timedelta(days=4)
                    manual_income = await client.post(
                        f"/api/v1/portfolios/{portfolio_id}/transactions",
                        json={
                            "account_id": account_id,
                            "instrument_id": str(instrument_id),
                            "type": "DIVIDEND",
                            "trade_date": str(manual_day),
                            "amount": "15",
                            "currency": "USD",
                            "tax": "3",
                        },
                    )
                    assert manual_income.status_code == 201
                    await import_market(
                        "actions",
                        f"date,ticker,action_type,value,currency\n{manual_day},{ticker},DIVIDEND,1,USD\n",
                    )
                    manual_action = await db.scalar(
                        select(CorporateActionVersion).where(
                            CorporateActionVersion.instrument_id == instrument_id,
                            CorporateActionVersion.action_date == manual_day,
                        )
                    )
                    assert (await apply(str(manual_action.id))).json()["error"][
                        "code"
                    ] == "DUPLICATE_ACTION_EFFECT"
                    adoption = {
                        "account_id": account_id,
                        "action_version_id": str(manual_action.id),
                        "adopt_manual": True,
                        "fee": "0",
                        "tax": "3",
                    }
                    mismatch = await client.post(
                        f"/api/v1/portfolios/{portfolio_id}/corporate-actions/apply",
                        json={**adoption, "tax": "0"},
                    )
                    assert mismatch.json()["error"]["code"] == "MANUAL_ACTION_MISMATCH"
                    before_adoption = len(
                        (await client.get(f"/api/v1/portfolios/{portfolio_id}/transactions")).json()
                    )
                    adopted = await client.post(
                        f"/api/v1/portfolios/{portfolio_id}/corporate-actions/apply", json=adoption
                    )
                    assert (
                        adopted.status_code == 200
                        and adopted.json()["transaction_id"] == manual_income.json()["id"]
                    )
                    assert (
                        len(
                            (
                                await client.get(f"/api/v1/portfolios/{portfolio_id}/transactions")
                            ).json()
                        )
                        == before_adoption
                    )
                    assert (
                        await client.delete(f"/api/v1/transactions/{manual_income.json()['id']}")
                    ).status_code == 409
                    await import_market(
                        "prices", f"date,ticker,close,currency\n{manual_day},{ticker},66,USD\n"
                    )
                    adopted_value = (
                        await client.get(
                            f"/api/v1/portfolios/{portfolio_id}/valuation",
                            params={"on_date": str(manual_day)},
                        )
                    ).json()
                    assert adopted_value["status"] == "COMPLETE" and Decimal(
                        adopted_value["total_value_base"]
                    ) == Decimal("10310.5")
                    before_action_correction = datetime.now(UTC)
                    await import_market(
                        "actions",
                        "date,ticker,action_type,value,currency\n"
                        f"{day + timedelta(days=1)},{ticker},SPLIT,3,\n",
                    )
                    prior_action = (
                        await client.get(
                            f"/api/v1/portfolios/{portfolio_id}/valuation",
                            params={
                                "on_date": str(end),
                                "as_of": before_action_correction.isoformat(),
                            },
                        )
                    ).json()
                    new_action = (
                        await client.get(
                            f"/api/v1/portfolios/{portfolio_id}/valuation",
                            params={"on_date": str(end)},
                        )
                    ).json()
                    assert (
                        prior_action["status"] == "COMPLETE" and new_action["status"] == "PARTIAL"
                    )
                    latest_split = await db.scalar(
                        select(CorporateActionVersion)
                        .where(
                            CorporateActionVersion.instrument_id == instrument_id,
                            CorporateActionVersion.action_type == "SPLIT",
                        )
                        .order_by(CorporateActionVersion.known_at.desc())
                    )
                    assert (await apply(str(latest_split.id))).json()["error"][
                        "code"
                    ] == "ACTION_CORRECTION_REVIEW"
                    eur_portfolio = await client.post(
                        "/api/v1/portfolios", json={"name": "EUR golden", "base_currency": "EUR"}
                    )
                    extra_portfolio_id = eur_portfolio.json()["id"]
                    eur_account = await client.post(
                        f"/api/v1/portfolios/{extra_portfolio_id}/accounts",
                        json={"name": "EUR account"},
                    )
                    eur_account_id = eur_account.json()["id"]
                    assert (
                        await client.post(
                            f"/api/v1/portfolios/{extra_portfolio_id}/transactions",
                            json={
                                "account_id": eur_account_id,
                                "type": "DEPOSIT",
                                "trade_date": str(day),
                                "amount": "500",
                                "currency": "EUR",
                            },
                        )
                    ).status_code == 201
                    assert (
                        await client.post(
                            f"/api/v1/portfolios/{extra_portfolio_id}/transactions",
                            json={
                                "account_id": eur_account_id,
                                "instrument_id": str(instrument_id),
                                "type": "BUY",
                                "trade_date": str(day),
                                "quantity": "10",
                                "price": "100",
                                "currency": "USD",
                            },
                        )
                    ).status_code == 201
                    eur_missing = (
                        await client.get(
                            f"/api/v1/portfolios/{extra_portfolio_id}/valuation",
                            params={"on_date": str(day)},
                        )
                    ).json()
                    assert (
                        eur_missing["status"] == "PARTIAL"
                        and eur_missing["holdings"][0]["market_value_native"] is not None
                    )
                    await import_market(
                        "fx", f"date,base_currency,quote_currency,rate\n{day},USD,EUR,0.8\n"
                    )
                    eur_valued = (
                        await client.get(
                            f"/api/v1/portfolios/{extra_portfolio_id}/valuation",
                            params={"on_date": str(day)},
                        )
                    ).json()
                    assert eur_valued["status"] == "COMPLETE" and Decimal(
                        eur_valued["total_value_base"]
                    ) == Decimal(660)
                    assert Decimal(eur_valued["holdings"][0]["market_value_base"]) == Decimal(960)
                    assert (await client.get("/api/v1/auth/session")).json()[
                        "authenticated"
                    ] is True
            finally:
                await db.rollback()
                portfolio_ids = [item for item in (portfolio_id, extra_portfolio_id) if item]
                if portfolio_id:
                    await db.execute(
                        delete(CashBalance).where(CashBalance.portfolio_id.in_(portfolio_ids))
                    )
                    await db.execute(
                        delete(PositionSnapshot).where(
                            PositionSnapshot.portfolio_id.in_(portfolio_ids)
                        )
                    )
                    await db.execute(
                        delete(PortfolioSnapshot).where(
                            PortfolioSnapshot.portfolio_id.in_(portfolio_ids)
                        )
                    )
                    await db.execute(
                        delete(PortfolioActionApplication).where(
                            PortfolioActionApplication.portfolio_id.in_(portfolio_ids)
                        )
                    )
                    await db.execute(
                        delete(Transaction).where(Transaction.portfolio_id.in_(portfolio_ids))
                    )
                    await db.execute(
                        delete(PortfolioAccount).where(
                            PortfolioAccount.portfolio_id.in_(portfolio_ids)
                        )
                    )
                    await db.execute(delete(Portfolio).where(Portfolio.id.in_(portfolio_ids)))
                if benchmark_id:
                    await db.execute(delete(Benchmark).where(Benchmark.id == benchmark_id))
                await db.execute(
                    delete(CorporateAction).where(CorporateAction.instrument_id == instrument_id)
                )
                await db.execute(
                    delete(CorporateActionVersion).where(
                        CorporateActionVersion.instrument_id == instrument_id
                    )
                )
                await db.execute(
                    delete(PriceDaily).where(PriceDaily.instrument_id == instrument_id)
                )
                await db.execute(
                    delete(PriceDailyVersion).where(
                        PriceDailyVersion.instrument_id == instrument_id
                    )
                )
                if raw_ids:
                    await db.execute(
                        delete(FxRate).where(
                            FxRate.version_id.in_(
                                select(FxRateVersion.id).where(
                                    FxRateVersion.raw_ingestion_id.in_(raw_ids)
                                )
                            )
                        )
                    )
                    await db.execute(
                        delete(FxRateVersion).where(FxRateVersion.raw_ingestion_id.in_(raw_ids))
                    )
                    await db.execute(
                        delete(DataQuarantine).where(DataQuarantine.raw_ingestion_id.in_(raw_ids))
                    )
                    await db.execute(delete(RawIngestion).where(RawIngestion.id.in_(raw_ids)))
                await db.execute(
                    delete(InstrumentIdentifier).where(
                        InstrumentIdentifier.instrument_id == instrument_id
                    )
                )
                await db.execute(delete(Instrument).where(Instrument.id == instrument_id))
                if user_id:
                    users = [uid for uid in (user_id, other_user_id) if uid]
                    await db.execute(delete(SessionRecord).where(SessionRecord.user_id.in_(users)))
                    await db.execute(
                        delete(AuditEvent).where(
                            or_(
                                AuditEvent.actor_user_id.in_(users),
                                AuditEvent.resource_id.in_([str(item) for item in raw_ids]),
                            )
                        )
                    )
                    await db.execute(delete(User).where(User.id.in_(users)))
                await db.commit()
        await get_engine().dispose()

    asyncio.run(run())
