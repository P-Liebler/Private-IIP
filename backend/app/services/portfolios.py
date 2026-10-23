from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import (
    Benchmark,
    CorporateActionVersion,
    Instrument,
    Portfolio,
    PortfolioAccount,
    PortfolioActionApplication,
    Transaction,
)
from app.schemas.portfolio import AccountCreate, PortfolioCreate, TransactionInput
from app.services.audit import audit_service
from app.services.portfolio_engine import ledger_state, money


def transaction_fingerprint(payload: TransactionInput) -> str:
    fields = payload.model_dump(mode="json", exclude={"notes", "external_id"})
    for key in fields:
        value = getattr(payload, key)
        if isinstance(value, Decimal):
            fields[key] = format(value.normalize(), "f") if value else "0"
    return hashlib.sha256(
        json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class PortfolioService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def owned(self, portfolio_id: UUID, *, lock: bool = False) -> Portfolio:
        statement = select(Portfolio).where(
            Portfolio.id == portfolio_id, Portfolio.user_id == self.user_id
        )
        if lock:
            statement = statement.with_for_update()
        portfolio = await self.db.scalar(statement)
        if portfolio is None:
            raise AppError(404, "PORTFOLIO_NOT_FOUND", "Portfolio not found")
        return portfolio

    async def portfolios(self) -> list[Portfolio]:
        return list(
            (
                await self.db.scalars(
                    select(Portfolio)
                    .where(Portfolio.user_id == self.user_id, Portfolio.archived_at.is_(None))
                    .order_by(Portfolio.created_at)
                )
            ).all()
        )

    async def create(self, payload: PortfolioCreate) -> Portfolio:
        if payload.benchmark_id and await self.db.get(Benchmark, payload.benchmark_id) is None:
            raise AppError(422, "BENCHMARK_NOT_FOUND", "Benchmark not found")
        record = Portfolio(user_id=self.user_id, **payload.model_dump())
        self.db.add(record)
        await self.db.flush()
        audit_service.record(
            self.db,
            event="portfolio.created",
            resource="portfolio",
            resource_id=str(record.id),
            actor_user_id=self.user_id,
        )
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def update(self, portfolio_id: UUID, changes: dict[str, object]) -> Portfolio:
        record = await self.owned(portfolio_id, lock=True)
        if record.archived_at:
            raise AppError(409, "PORTFOLIO_ARCHIVED", "Archived portfolio cannot be modified")
        if (
            "benchmark_id" in changes
            and changes["benchmark_id"] is not None
            and await self.db.get(Benchmark, changes["benchmark_id"]) is None
        ):
            raise AppError(422, "BENCHMARK_NOT_FOUND", "Benchmark not found")
        for key, value in changes.items():
            setattr(record, key, value)
        audit_service.record(
            self.db,
            event="portfolio.updated",
            resource="portfolio",
            resource_id=str(record.id),
            actor_user_id=self.user_id,
        )
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def archive(self, portfolio_id: UUID) -> Portfolio:
        record = await self.owned(portfolio_id, lock=True)
        if record.archived_at is None:
            record.archived_at = datetime.now(UTC)
            audit_service.record(
                self.db,
                event="portfolio.archived",
                resource="portfolio",
                resource_id=str(record.id),
                actor_user_id=self.user_id,
            )
            await self.db.commit()
            await self.db.refresh(record)
        return record

    async def accounts(self, portfolio_id: UUID) -> list[PortfolioAccount]:
        await self.owned(portfolio_id)
        return list(
            (
                await self.db.scalars(
                    select(PortfolioAccount)
                    .where(PortfolioAccount.portfolio_id == portfolio_id)
                    .order_by(PortfolioAccount.created_at)
                )
            ).all()
        )

    async def account(self, portfolio_id: UUID, account_id: UUID) -> PortfolioAccount:
        account = await self.db.scalar(
            select(PortfolioAccount).where(
                PortfolioAccount.id == account_id, PortfolioAccount.portfolio_id == portfolio_id
            )
        )
        if account is None:
            raise AppError(404, "ACCOUNT_NOT_FOUND", "Account not found")
        return account

    async def create_account(self, portfolio_id: UUID, payload: AccountCreate) -> PortfolioAccount:
        portfolio = await self.owned(portfolio_id, lock=True)
        if portfolio.archived_at:
            raise AppError(409, "PORTFOLIO_ARCHIVED", "Archived portfolio cannot be modified")
        account = PortfolioAccount(portfolio_id=portfolio_id, **payload.model_dump())
        self.db.add(account)
        await self.db.flush()
        audit_service.record(
            self.db,
            event="account.created",
            resource="portfolio_account",
            resource_id=str(account.id),
            actor_user_id=self.user_id,
        )
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def update_account(
        self, account_id: UUID, changes: dict[str, object]
    ) -> PortfolioAccount:
        account = await self.db.get(PortfolioAccount, account_id)
        if account is None:
            raise AppError(404, "ACCOUNT_NOT_FOUND", "Account not found")
        await self.owned(account.portfolio_id, lock=True)
        if account.archived_at:
            raise AppError(409, "ACCOUNT_ARCHIVED", "Archived account cannot be modified")
        for key, value in changes.items():
            setattr(account, key, value)
        audit_service.record(
            self.db,
            event="account.updated",
            resource="portfolio_account",
            resource_id=str(account.id),
            actor_user_id=self.user_id,
        )
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def archive_account(self, account_id: UUID) -> PortfolioAccount:
        account = await self.db.get(PortfolioAccount, account_id)
        if account is None:
            raise AppError(404, "ACCOUNT_NOT_FOUND", "Account not found")
        await self.owned(account.portfolio_id, lock=True)
        if account.archived_at is None:
            account.archived_at = datetime.now(UTC)
            audit_service.record(
                self.db,
                event="account.archived",
                resource="portfolio_account",
                resource_id=str(account.id),
                actor_user_id=self.user_id,
            )
            await self.db.commit()
            await self.db.refresh(account)
        return account

    async def transactions(self, portfolio_id: UUID) -> list[Transaction]:
        await self.owned(portfolio_id)
        return list(
            (
                await self.db.scalars(
                    select(Transaction)
                    .where(Transaction.portfolio_id == portfolio_id)
                    .order_by(Transaction.trade_date, Transaction.created_at, Transaction.id)
                )
            ).all()
        )

    async def _validate_input(self, portfolio_id: UUID, payload: TransactionInput) -> None:
        account = await self.account(portfolio_id, payload.account_id)
        if account.archived_at:
            raise AppError(409, "ACCOUNT_ARCHIVED", "Archived account cannot receive transactions")
        if payload.instrument_id:
            instrument = await self.db.get(Instrument, payload.instrument_id)
            if instrument is None or (
                payload.type in {"BUY", "SELL", "SPLIT", "OPENING_POSITION"}
                and instrument.currency != payload.currency
            ):
                raise AppError(
                    422, "INVALID_TRANSACTION", "Instrument missing or currency mismatch"
                )
            if payload.type in {"SPLIT", "DIVIDEND"}:
                application = await self.db.scalar(
                    select(PortfolioActionApplication.id).where(
                        PortfolioActionApplication.account_id == payload.account_id,
                        PortfolioActionApplication.instrument_id == payload.instrument_id,
                        PortfolioActionApplication.action_date == payload.trade_date,
                        PortfolioActionApplication.action_type.in_(
                            ["SPLIT", "REVERSE_SPLIT"] if payload.type == "SPLIT" else ["DIVIDEND"]
                        ),
                    )
                )
                if application:
                    raise AppError(
                        409, "DUPLICATE_ACTION_EFFECT", "Canonical effect already applied"
                    )

    async def _duplicate(
        self, portfolio_id: UUID, payload: TransactionInput, *, exclude: UUID | None = None
    ) -> None:
        statement = select(Transaction.id).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.account_id == payload.account_id,
            Transaction.status == "ACTIVE",
            Transaction.external_id == payload.external_id
            if payload.external_id
            else Transaction.fingerprint == transaction_fingerprint(payload),
        )
        if exclude:
            statement = statement.where(Transaction.id != exclude)
        if await self.db.scalar(statement):
            raise AppError(409, "DUPLICATE_TRANSACTION", "Transaction already exists")

    async def create_transaction(
        self,
        portfolio_id: UUID,
        payload: TransactionInput,
        *,
        raw_id: UUID | None = None,
        source: str = "MANUAL",
        commit: bool = True,
    ) -> Transaction:
        portfolio = await self.owned(portfolio_id, lock=True)
        if portfolio.archived_at:
            raise AppError(409, "PORTFOLIO_ARCHIVED", "Archived portfolio cannot be modified")
        await self._validate_input(portfolio_id, payload)
        await self._duplicate(portfolio_id, payload)
        row = Transaction(
            portfolio_id=portfolio_id,
            **payload.model_dump(),
            fingerprint=transaction_fingerprint(payload),
            raw_ingestion_id=raw_id,
            source=source,
            status="ACTIVE",
            system_generated=False,
            created_at=datetime.now(UTC),
        )
        self.db.add(row)
        await self.db.flush()
        await self._replay_check(portfolio_id)
        audit_service.record(
            self.db,
            event="transaction.created",
            resource="transaction",
            resource_id=str(row.id),
            actor_user_id=self.user_id,
            metadata={"source": source},
        )
        if commit:
            await self.db.commit()
        return row

    async def _replay_check(self, portfolio_id: UUID) -> None:
        rows = list(
            (
                await self.db.scalars(
                    select(Transaction).where(Transaction.portfolio_id == portfolio_id)
                )
            ).all()
        )
        ledger_state(rows, date.max, datetime.now(UTC))

    async def correct_transaction(
        self, transaction_id: UUID, payload: TransactionInput
    ) -> Transaction:
        old = await self.db.get(Transaction, transaction_id)
        if old is None:
            raise AppError(404, "TRANSACTION_NOT_FOUND", "Transaction not found")
        await self.owned(old.portfolio_id, lock=True)
        await self.db.refresh(old)
        linked = await self.db.scalar(
            select(PortfolioActionApplication.id).where(
                PortfolioActionApplication.transaction_id == old.id
            )
        )
        if old.status != "ACTIVE" or old.system_generated or linked:
            raise AppError(409, "TRANSACTION_NOT_CORRECTABLE", "Transaction cannot be corrected")
        await self._validate_input(old.portfolio_id, payload)
        await self._duplicate(old.portfolio_id, payload, exclude=old.id)
        now = datetime.now(UTC)
        old.status, old.voided_at = "VOIDED", now
        row = Transaction(
            portfolio_id=old.portfolio_id,
            **payload.model_dump(),
            fingerprint=transaction_fingerprint(payload),
            source=old.source,
            status="ACTIVE",
            replaces_transaction_id=old.id,
            raw_ingestion_id=old.raw_ingestion_id,
            system_generated=False,
            created_at=now,
        )
        self.db.add(row)
        await self.db.flush()
        await self._replay_check(old.portfolio_id)
        audit_service.record(
            self.db,
            event="transaction.updated",
            resource="transaction",
            resource_id=str(row.id),
            actor_user_id=self.user_id,
            metadata={"replaces": str(old.id)},
        )
        await self.db.commit()
        return row

    async def void_transaction(self, transaction_id: UUID) -> Transaction:
        row = await self.db.get(Transaction, transaction_id)
        if row is None:
            raise AppError(404, "TRANSACTION_NOT_FOUND", "Transaction not found")
        await self.owned(row.portfolio_id, lock=True)
        await self.db.refresh(row)
        linked = await self.db.scalar(
            select(PortfolioActionApplication.id).where(
                PortfolioActionApplication.transaction_id == row.id
            )
        )
        if row.status != "ACTIVE" or row.system_generated or linked:
            raise AppError(409, "TRANSACTION_NOT_VOIDABLE", "Transaction cannot be voided")
        row.status, row.voided_at = "VOIDED", datetime.now(UTC)
        await self.db.flush()
        await self._replay_check(row.portfolio_id)
        audit_service.record(
            self.db,
            event="transaction.deleted_or_voided",
            resource="transaction",
            resource_id=str(row.id),
            actor_user_id=self.user_id,
        )
        await self.db.commit()
        return row

    async def apply_action(
        self,
        portfolio_id: UUID,
        account_id: UUID,
        action_version_id: UUID,
        fee: Decimal | None = None,
        tax: Decimal | None = None,
        adopt_manual: bool = False,
    ) -> PortfolioActionApplication:
        portfolio = await self.owned(portfolio_id, lock=True)
        account = await self.account(portfolio_id, account_id)
        if portfolio.archived_at or account.archived_at:
            raise AppError(
                409, "PORTFOLIO_ARCHIVED", "Archived portfolio/account cannot apply actions"
            )
        action = await self.db.get(CorporateActionVersion, action_version_id)
        if (
            action is None
            or action.known_at > datetime.now(UTC)
            or action.action_date > datetime.now(UTC).date()
        ):
            raise AppError(404, "ACTION_NOT_FOUND", "Corporate action version not found")
        if action.action_type == "DIVIDEND" and (
            action.cash_amount is None or action.cash_amount < 0
        ):
            raise AppError(409, "ACTION_AMOUNT_UNAVAILABLE", "Dividend cash amount is unavailable")
        if action.action_type == "DIVIDEND" and (fee is None or tax is None):
            raise AppError(
                409,
                "ACTION_COST_REVIEW_REQUIRED",
                "Confirm actual dividend fee and withholding, including an explicit zero",
            )
        if action.action_type in {"SPLIT", "REVERSE_SPLIT"} and (
            action.ratio is None or action.ratio <= 0
        ):
            raise AppError(409, "ACTION_RATIO_UNAVAILABLE", "Split ratio is unavailable")
        if action.action_type == "DIVIDEND" and action.currency not in {None, "CHF", "EUR", "USD"}:
            raise AppError(409, "ACTION_CURRENCY_UNSUPPORTED", "Dividend currency is unsupported")
        current = await self.db.scalar(
            select(CorporateActionVersion)
            .where(
                CorporateActionVersion.instrument_id == action.instrument_id,
                CorporateActionVersion.action_date == action.action_date,
                CorporateActionVersion.action_type == action.action_type,
            )
            .order_by(CorporateActionVersion.known_at.desc())
            .limit(1)
        )
        if current is None or current.id != action.id:
            raise AppError(409, "ACTION_VERSION_SUPERSEDED", "Use the current action version")
        existing = await self.db.scalar(
            select(PortfolioActionApplication).where(
                PortfolioActionApplication.account_id == account_id,
                PortfolioActionApplication.instrument_id == action.instrument_id,
                PortfolioActionApplication.action_date == action.action_date,
                PortfolioActionApplication.action_type == action.action_type,
            )
        )
        if existing:
            if existing.action_version_id == action.id:
                if action.action_type == "DIVIDEND" and existing.transaction_id:
                    effect = await self.db.get(Transaction, existing.transaction_id)
                    if effect and (effect.fee != fee or effect.tax != tax):
                        raise AppError(
                            409,
                            "ACTION_CORRECTION_REVIEW",
                            "Confirmed dividend costs differ from the preserved effect",
                        )
                return existing
            raise AppError(
                409, "ACTION_CORRECTION_REVIEW", "Action correction requires explicit review"
            )
        rows = list(
            (
                await self.db.scalars(
                    select(Transaction).where(Transaction.portfolio_id == portfolio_id)
                )
            ).all()
        )
        # Apply earlier splits first: later entitlement depends on their share count.
        prior_splits = (
            await self.db.scalars(
                select(CorporateActionVersion)
                .where(
                    CorporateActionVersion.instrument_id == action.instrument_id,
                    CorporateActionVersion.action_type.in_(["SPLIT", "REVERSE_SPLIT"]),
                    CorporateActionVersion.action_date <= action.action_date,
                    CorporateActionVersion.known_at <= datetime.now(UTC),
                )
                .order_by(CorporateActionVersion.known_at.desc())
            )
        ).all()
        seen: set[tuple[date, str]] = set()
        for split in prior_splits:
            key = (split.action_date, split.action_type)
            if key in seen or split.id == action.id:
                continue
            seen.add(key)
            held = ledger_state(
                rows, split.action_date - timedelta(days=1), datetime.now(UTC)
            ).positions.get((account_id, action.instrument_id))
            if held is None or held.quantity <= 0:
                continue
            if split.action_date == action.action_date:
                raise AppError(
                    409,
                    "ACTION_SAME_DAY_REVIEW",
                    "Same-day split and income require explicit entitlement review",
                )
            applied = await self.db.scalar(
                select(PortfolioActionApplication).where(
                    PortfolioActionApplication.account_id == account_id,
                    PortfolioActionApplication.action_version_id == split.id,
                )
            )
            if applied is None:
                raise AppError(
                    409, "ACTION_DEPENDENCY_UNAPPLIED", "Apply or review earlier split first"
                )
        manual_effects = [
            row
            for row in rows
            if (
                row.account_id == account_id
                and row.instrument_id == action.instrument_id
                and row.trade_date == action.action_date
                and row.type
                == ("SPLIT" if action.action_type == "REVERSE_SPLIT" else action.action_type)
                and row.voided_at is None
            )
        ]
        if manual_effects and not adopt_manual:
            raise AppError(409, "DUPLICATE_ACTION_EFFECT", "A manual effect already exists")
        if adopt_manual and len(manual_effects) != 1:
            raise AppError(409, "MANUAL_ACTION_AMBIGUOUS", "Exactly one manual effect must match")
        before = ledger_state(rows, action.action_date - timedelta(days=1), datetime.now(UTC))
        position = before.positions.get((account_id, action.instrument_id))
        if position is None or position.quantity <= 0:
            raise AppError(409, "NO_ELIGIBLE_POSITION", "No shares held before the ex-date")
        manual_effect = manual_effects[0] if adopt_manual else None
        if manual_effect is not None:
            matches = (
                (
                    manual_effect.quantity == action.ratio
                    and manual_effect.currency == position.currency
                )
                if action.action_type in {"SPLIT", "REVERSE_SPLIT"}
                else (
                    manual_effect.amount == money(action.cash_amount * position.quantity)
                    and manual_effect.currency == (action.currency or position.currency)
                    and manual_effect.fee == fee
                    and manual_effect.tax == tax
                )
                if action.action_type == "DIVIDEND" and action.cash_amount is not None
                else False
            )
            if not matches:
                raise AppError(
                    409,
                    "MANUAL_ACTION_MISMATCH",
                    "Manual economic effect does not match reviewed canonical action",
                )
        application = PortfolioActionApplication(
            portfolio_id=portfolio_id,
            account_id=account_id,
            instrument_id=action.instrument_id,
            action_date=action.action_date,
            action_type=action.action_type,
            action_version_id=action.id,
            transaction_id=manual_effect.id if manual_effect is not None else None,
        )
        self.db.add(application)
        await self.db.flush()
        if manual_effect is None and action.action_type in {"SPLIT", "REVERSE_SPLIT", "DIVIDEND"}:
            amount = (
                money(action.cash_amount * position.quantity)
                if action.action_type == "DIVIDEND" and action.cash_amount is not None
                else None
            )
            payload = TransactionInput(
                account_id=account_id,
                instrument_id=action.instrument_id,
                type="DIVIDEND" if action.action_type == "DIVIDEND" else "SPLIT",
                trade_date=action.action_date,
                quantity=action.ratio if action.action_type != "DIVIDEND" else None,
                amount=amount,
                currency=(action.currency or position.currency)
                if action.action_type == "DIVIDEND"
                else position.currency,
                fee=fee if action.action_type == "DIVIDEND" and fee is not None else Decimal(0),
                tax=tax if action.action_type == "DIVIDEND" and tax is not None else Decimal(0),
            )
            transaction = Transaction(
                portfolio_id=portfolio_id,
                **payload.model_dump(),
                fingerprint=transaction_fingerprint(payload),
                source="CANONICAL_ACTION",
                status="ACTIVE",
                corporate_action_version_id=action.id,
                system_generated=True,
                created_at=datetime.now(UTC),
            )
            self.db.add(transaction)
            await self.db.flush()
            application.transaction_id = transaction.id
            await self._replay_check(portfolio_id)
        audit_service.record(
            self.db,
            event="portfolio.corporate_action_applied",
            resource="portfolio_action_application",
            resource_id=str(application.id),
            actor_user_id=self.user_id,
            metadata={
                "action_version_id": str(action.id),
                "fee": str(fee),
                "tax": str(tax),
                "cost_source": "USER_CONFIRMED" if action.action_type == "DIVIDEND" else None,
                "adopted_manual_transaction_id": str(manual_effect.id)
                if manual_effect is not None
                else None,
            },
        )
        await self.db.commit()
        return application

    async def action_preview(
        self, portfolio_id: UUID, account_id: UUID, version_id: UUID
    ) -> dict[str, object]:
        await self.owned(portfolio_id)
        await self.account(portfolio_id, account_id)
        action = await self.db.get(CorporateActionVersion, version_id)
        if action is None or action.known_at > datetime.now(UTC):
            raise AppError(404, "ACTION_NOT_FOUND", "Corporate action not found")
        rows = await self.transactions(portfolio_id)
        before = ledger_state(rows, action.action_date - timedelta(days=1), datetime.now(UTC))
        position = before.positions.get((account_id, action.instrument_id))
        instrument = await self.db.get(Instrument, action.instrument_id)
        manual_effects = [
            row
            for row in rows
            if row.account_id == account_id
            and row.instrument_id == action.instrument_id
            and row.trade_date == action.action_date
            and row.type
            == ("SPLIT" if action.action_type == "REVERSE_SPLIT" else action.action_type)
            and row.status == "ACTIVE"
            and not row.system_generated
        ]
        return {
            "id": action.id,
            "instrument_name": instrument.name if instrument else None,
            "type": action.action_type,
            "date": action.action_date,
            "ratio": action.ratio,
            "cash_amount_per_share": action.cash_amount,
            "currency": action.currency,
            "source_id": action.source_id,
            "raw_ingestion_id": action.raw_ingestion_id,
            "known_at": action.known_at,
            "ledger_quantity_before_ex_date": position.quantity if position else None,
            "entitlement_status": "REVIEW_REQUIRED",
            "cost_confirmation_required": action.action_type == "DIVIDEND",
            "manual_effect_count": len(manual_effects),
        }
