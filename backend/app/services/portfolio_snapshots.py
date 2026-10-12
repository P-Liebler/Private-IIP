"""Rebuildable materialized views; the ledger and versioned market data remain authoritative."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CashBalance, PortfolioSnapshot, PositionSnapshot
from app.services.market_queries import pit_cutoff
from app.services.portfolio_valuation import PortfolioValuationService
from app.services.portfolios import PortfolioService


def snapshot_hash(value: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


class PortfolioSnapshotService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id
        self.valuation = PortfolioValuationService(db, user_id)

    async def rebuild(
        self, portfolio_id: UUID, day: date, as_of: datetime | None = None
    ) -> PortfolioSnapshot:
        await PortfolioService(self.db, self.user_id).owned(portfolio_id, lock=True)
        cutoff = pit_cutoff(as_of)
        value = await self.valuation.value(portfolio_id, day, cutoff)
        dependency = {
            "transactions": value["transaction_ids"],
            "cash": value["cash"],
            "holdings": value["holdings"],
            "issues": value["issues"],
            "base_currency": value["base_currency"],
            "analytics": {
                key: value[key]
                for key in (
                    "realized_pnl_base_at_trade_fx",
                    "income_base_at_event_fx",
                    "fees_base_at_event_fx",
                    "taxes_base_at_event_fx",
                    "analytics_status",
                )
            },
            "event_fx_provenance": value["event_fx_provenance"],
        }
        digest = snapshot_hash(dependency)
        existing = await self.db.scalar(
            select(PortfolioSnapshot).where(
                PortfolioSnapshot.portfolio_id == portfolio_id,
                PortfolioSnapshot.snapshot_date == day,
                PortfolioSnapshot.input_hash == digest,
            )
        )
        if existing:
            return existing
        for cash in cast(list[dict[str, object]], value["cash"]):
            self.db.add(
                CashBalance(
                    portfolio_id=portfolio_id,
                    account_id=cast(UUID, cash["account_id"]),
                    snapshot_date=day,
                    currency=cast(str, cash["currency"]),
                    balance=cast(Decimal, cash["amount"]),
                    input_hash=digest,
                )
            )
        for holding in cast(list[dict[str, object]], value["holdings"]):
            self.db.add(
                PositionSnapshot(
                    portfolio_id=portfolio_id,
                    account_id=cast(UUID, holding["account_id"]),
                    instrument_id=cast(UUID, holding["instrument_id"]),
                    snapshot_date=day,
                    quantity=cast(Decimal, holding["quantity"]),
                    average_cost=cast(Decimal, holding["average_cost_native"]),
                    cost_basis=cast(Decimal, holding["cost_basis_native"]),
                    currency=cast(str, holding["currency"]),
                    market_price=cast(Decimal | None, holding["price"]),
                    market_value_native=cast(Decimal | None, holding["market_value_native"]),
                    fx_rate=cast(dict[str, object], holding["fx"]).get("rate"),
                    market_value_base=cast(Decimal | None, holding["market_value_base"]),
                    unrealized_pnl=cast(Decimal | None, holding["unrealized_pnl_native"]),
                    valuation_status=cast(str, holding["valuation_status"]),
                    price_version_id=cast(UUID | None, holding["price_version_id"]),
                    input_hash=digest,
                )
            )
        snapshot = PortfolioSnapshot(
            portfolio_id=portfolio_id,
            snapshot_date=day,
            base_currency=cast(str, value["base_currency"]),
            cash_value_base=cast(Decimal | None, value["cash_value_base"]),
            securities_value_base=cast(Decimal | None, value["securities_value_base"]),
            total_value_base=cast(Decimal | None, value["total_value_base"]),
            cost_basis_base=cast(Decimal | None, value["cost_basis_base_at_valuation_fx"]),
            unrealized_pnl_base=cast(Decimal | None, value["unrealized_pnl_base_at_valuation_fx"]),
            realized_pnl_base=cast(Decimal | None, value["realized_pnl_base_at_trade_fx"]),
            income_base=cast(Decimal | None, value["income_base_at_event_fx"]),
            fees_base=cast(Decimal | None, value["fees_base_at_event_fx"]),
            completeness_status=cast(str, value["status"]),
            issues=[
                cast(str, issue["code"]) for issue in cast(list[dict[str, object]], value["issues"])
            ],
            input_hash=digest,
            knowledge_cutoff=cutoff,
            input_provenance=json.loads(json.dumps(dependency, default=str)),
        )
        self.db.add(snapshot)
        await self.db.commit()
        return snapshot
