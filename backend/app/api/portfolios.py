from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_user
from app.core.errors import AppError
from app.db.session import get_session
from app.models import (
    Benchmark,
    Instrument,
    Portfolio,
    PortfolioAccount,
    PortfolioSnapshot,
    Transaction,
)
from app.schemas.portfolio import (
    AccountCreate,
    AccountUpdate,
    PortfolioCreate,
    PortfolioUpdate,
    TransactionInput,
)
from app.services.auth import AuthContext
from app.services.portfolio_import import PortfolioImportService
from app.services.portfolio_performance import PortfolioPerformanceService
from app.services.portfolio_reconciliation import ReconciliationInput, reconcile
from app.services.portfolio_reporting import PortfolioReportingService
from app.services.portfolio_snapshots import PortfolioSnapshotService
from app.services.portfolio_summary import PortfolioSummaryService
from app.services.portfolio_valuation import PortfolioValuationService
from app.services.portfolios import PortfolioService

router = APIRouter(prefix="/api/v1", tags=["portfolios"])
DB = Annotated[AsyncSession, Depends(get_session)]
USER = Annotated[AuthContext, Depends(require_user)]


def portfolio_view(row: Portfolio) -> dict[str, object]:
    return {
        "id": row.id,
        "name": row.name,
        "base_currency": row.base_currency,
        "benchmark_id": row.benchmark_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "archived_at": row.archived_at,
    }


def account_view(row: PortfolioAccount) -> dict[str, object]:
    return {
        "id": row.id,
        "portfolio_id": row.portfolio_id,
        "name": row.name,
        "account_type": row.account_type,
        "default_currency": row.default_currency,
        "archived_at": row.archived_at,
    }


def transaction_view(row: Transaction) -> dict[str, object]:
    return {
        key: getattr(row, key)
        for key in (
            "id",
            "portfolio_id",
            "account_id",
            "instrument_id",
            "type",
            "trade_date",
            "settlement_date",
            "quantity",
            "price",
            "amount",
            "currency",
            "fee",
            "tax",
            "fx_rate_to_base",
            "external_id",
            "notes",
            "source",
            "status",
            "replaces_transaction_id",
            "corporate_action_version_id",
            "raw_ingestion_id",
            "system_generated",
            "created_at",
            "voided_at",
        )
    }


class BenchmarkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instrument_id: UUID


class ApplyAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: UUID
    action_version_id: UUID
    adopt_manual: bool = False
    fee: Decimal | None = Field(
        default=None, ge=0, max_digits=24, decimal_places=8, allow_inf_nan=False
    )
    tax: Decimal | None = Field(
        default=None, ge=0, max_digits=24, decimal_places=8, allow_inf_nan=False
    )


class ImportCommit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: UUID
    raw_ingestion_id: UUID
    mapping: dict[str, str]
    instrument_resolutions: dict[int, UUID] = Field(default_factory=dict)


@router.get("/benchmarks")
async def benchmarks(db: DB, _user: USER) -> list[dict[str, object]]:
    rows = (await db.scalars(select(Benchmark).order_by(Benchmark.name))).all()
    return [{"id": row.id, "name": row.name, "instrument_id": row.instrument_id} for row in rows]


@router.post("/benchmarks", status_code=201)
async def create_benchmark(payload: BenchmarkCreate, db: DB, _user: USER) -> dict[str, object]:
    instrument = await db.get(Instrument, payload.instrument_id, with_for_update=True)
    if instrument is None:
        raise AppError(422, "INSTRUMENT_NOT_FOUND", "Instrument not found")
    existing = await db.scalar(select(Benchmark).where(Benchmark.instrument_id == instrument.id))
    if existing:
        return {"id": existing.id, "name": existing.name, "instrument_id": existing.instrument_id}
    row = Benchmark(name=instrument.name, instrument_id=instrument.id)
    db.add(row)
    await db.commit()
    return {"id": row.id, "name": row.name, "instrument_id": row.instrument_id}


@router.get("/portfolios")
async def portfolios(db: DB, user: USER) -> list[dict[str, object]]:
    return [portfolio_view(row) for row in await PortfolioService(db, user.user.id).portfolios()]


@router.post("/portfolios", status_code=201)
async def create_portfolio(payload: PortfolioCreate, db: DB, user: USER) -> dict[str, object]:
    return portfolio_view(await PortfolioService(db, user.user.id).create(payload))


@router.get("/portfolio-dashboard")
async def dashboard(db: DB, user: USER) -> dict[str, object]:
    return await PortfolioReportingService(db, user.user.id).dashboard()


@router.get("/portfolios/{portfolio_id}")
async def get_portfolio(portfolio_id: UUID, db: DB, user: USER) -> dict[str, object]:
    return portfolio_view(await PortfolioService(db, user.user.id).owned(portfolio_id))


@router.patch("/portfolios/{portfolio_id}")
async def update_portfolio(
    portfolio_id: UUID, payload: PortfolioUpdate, db: DB, user: USER
) -> dict[str, object]:
    return portfolio_view(
        await PortfolioService(db, user.user.id).update(
            portfolio_id, payload.model_dump(exclude_unset=True)
        )
    )


@router.delete("/portfolios/{portfolio_id}")
async def archive_portfolio(portfolio_id: UUID, db: DB, user: USER) -> dict[str, object]:
    return portfolio_view(await PortfolioService(db, user.user.id).archive(portfolio_id))


@router.get("/portfolios/{portfolio_id}/accounts")
async def accounts(portfolio_id: UUID, db: DB, user: USER) -> list[dict[str, object]]:
    return [
        account_view(row) for row in await PortfolioService(db, user.user.id).accounts(portfolio_id)
    ]


@router.post("/portfolios/{portfolio_id}/reconciliation")
async def reconcile_statement(
    portfolio_id: UUID, payload: ReconciliationInput, db: DB, user: USER
) -> dict[str, object]:
    return await reconcile(db, user.user.id, portfolio_id, payload)


@router.post("/portfolios/{portfolio_id}/accounts", status_code=201)
async def create_account(
    portfolio_id: UUID, payload: AccountCreate, db: DB, user: USER
) -> dict[str, object]:
    return account_view(
        await PortfolioService(db, user.user.id).create_account(portfolio_id, payload)
    )


@router.patch("/accounts/{account_id}")
async def update_account(
    account_id: UUID, payload: AccountUpdate, db: DB, user: USER
) -> dict[str, object]:
    return account_view(
        await PortfolioService(db, user.user.id).update_account(
            account_id, payload.model_dump(exclude_unset=True)
        )
    )


@router.delete("/accounts/{account_id}")
async def archive_account(account_id: UUID, db: DB, user: USER) -> dict[str, object]:
    return account_view(await PortfolioService(db, user.user.id).archive_account(account_id))


@router.get("/portfolios/{portfolio_id}/transactions")
async def transactions(portfolio_id: UUID, db: DB, user: USER) -> list[dict[str, object]]:
    service = PortfolioService(db, user.user.id)
    portfolio = await service.owned(portfolio_id)
    reporting = PortfolioReportingService(db, user.user.id)
    result = []
    for row in await service.transactions(portfolio_id):
        item = transaction_view(row)
        if row.instrument_id:
            instrument = await db.get(Instrument, row.instrument_id)
            item["instrument_name"] = instrument.name if instrument else None
        item.update(await reporting.transaction_amounts(row, portfolio.base_currency))
        result.append(item)
    return result


@router.post("/portfolios/{portfolio_id}/transactions", status_code=201)
async def create_transaction(
    portfolio_id: UUID, payload: TransactionInput, db: DB, user: USER
) -> dict[str, object]:
    return transaction_view(
        await PortfolioService(db, user.user.id).create_transaction(portfolio_id, payload)
    )


@router.post("/portfolios/{portfolio_id}/transactions/import/preview")
async def preview_transactions(
    portfolio_id: UUID,
    account_id: UUID,
    request: Request,
    db: DB,
    user: USER,
    column_mapping: str | None = None,
    instrument_resolutions: str | None = None,
) -> dict[str, object]:
    if request.headers.get("Content-Type", "").split(";", 1)[0].lower() != "text/csv":
        raise AppError(415, "CSV_CONTENT_TYPE_REQUIRED", "Upload a text/csv file")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 5_000_000:
            raise AppError(413, "CSV_SIZE_INVALID", "CSV exceeds 5 MB")
    mapping = None
    if column_mapping is not None:
        try:
            mapping = json.loads(column_mapping)
        except ValueError as error:
            raise AppError(422, "CSV_MAPPING_INVALID", "Mapping must be JSON") from error
        if not isinstance(mapping, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()
        ):
            raise AppError(422, "CSV_MAPPING_INVALID", "Mapping must contain string fields")
    resolutions: dict[int, UUID] = {}
    if instrument_resolutions is not None:
        try:
            supplied = json.loads(instrument_resolutions)
            if not isinstance(supplied, dict) or len(supplied) > 10000:
                raise ValueError("Invalid resolutions")
            resolutions = {int(k): UUID(v) for k, v in supplied.items()}
            if any(line < 2 or line > 10001 for line in resolutions):
                raise ValueError("Invalid CSV line")
        except (ValueError, TypeError, AttributeError) as error:
            raise AppError(
                422, "CSV_RESOLUTION_INVALID", "Use explicit instrument choices by CSV line"
            ) from error
    return await PortfolioImportService(db, user.user.id).preview(
        portfolio_id,
        account_id,
        bytes(data),
        request.headers.get("X-Filename", "transactions.csv"),
        mapping,
        resolutions,
    )


@router.post("/portfolios/{portfolio_id}/transactions/import/commit")
async def commit_transactions(
    portfolio_id: UUID, payload: ImportCommit, db: DB, user: USER
) -> dict[str, object]:
    return await PortfolioImportService(db, user.user.id).commit(
        portfolio_id,
        payload.account_id,
        payload.raw_ingestion_id,
        payload.mapping,
        payload.instrument_resolutions,
    )


@router.patch("/transactions/{transaction_id}")
async def correct_transaction(
    transaction_id: UUID, payload: TransactionInput, db: DB, user: USER
) -> dict[str, object]:
    return transaction_view(
        await PortfolioService(db, user.user.id).correct_transaction(transaction_id, payload)
    )


@router.delete("/transactions/{transaction_id}")
async def void_transaction(transaction_id: UUID, db: DB, user: USER) -> dict[str, object]:
    return transaction_view(
        await PortfolioService(db, user.user.id).void_transaction(transaction_id)
    )


@router.post("/portfolios/{portfolio_id}/corporate-actions/apply")
async def apply_action(
    portfolio_id: UUID, payload: ApplyAction, db: DB, user: USER
) -> dict[str, object]:
    row = await PortfolioService(db, user.user.id).apply_action(
        portfolio_id,
        payload.account_id,
        payload.action_version_id,
        payload.fee,
        payload.tax,
        payload.adopt_manual,
    )
    return {
        "id": row.id,
        "action_version_id": row.action_version_id,
        "transaction_id": row.transaction_id,
        "applied_at": row.applied_at,
    }


@router.get("/portfolios/{portfolio_id}/corporate-actions/{version_id}/preview")
async def preview_action(
    portfolio_id: UUID, version_id: UUID, account_id: UUID, db: DB, user: USER
) -> dict[str, object]:
    return await PortfolioService(db, user.user.id).action_preview(
        portfolio_id, account_id, version_id
    )


@router.get("/portfolios/{portfolio_id}/valuation")
async def valuation(
    portfolio_id: UUID,
    db: DB,
    user: USER,
    on_date: date | None = None,
    as_of: datetime | None = None,
) -> dict[str, object]:
    return await PortfolioValuationService(db, user.user.id).value(portfolio_id, on_date, as_of)


@router.get("/portfolios/{portfolio_id}/holdings")
async def holdings(
    portfolio_id: UUID,
    db: DB,
    user: USER,
    on_date: date | None = None,
    as_of: datetime | None = None,
) -> dict[str, object]:
    result = await PortfolioValuationService(db, user.user.id).value(portfolio_id, on_date, as_of)
    return {
        "status": result["status"],
        "issues": result["issues"],
        "holdings": result["holdings"],
        "as_of": result["as_of"],
    }


@router.get("/portfolios/{portfolio_id}/summary")
async def summary(portfolio_id: UUID, db: DB, user: USER) -> dict[str, object]:
    return await PortfolioSummaryService(db, user.user.id).summary(portfolio_id)


@router.get("/portfolios/{portfolio_id}/allocation")
async def allocation(
    portfolio_id: UUID, db: DB, user: USER, on_date: date | None = None
) -> dict[str, object]:
    return await PortfolioReportingService(db, user.user.id).allocation(portfolio_id, on_date)


@router.get("/portfolios/{portfolio_id}/performance")
async def performance(
    portfolio_id: UUID,
    start: date,
    end: date,
    db: DB,
    user: USER,
    as_of: datetime | None = None,
    frequency: str = "daily",
) -> dict[str, object]:
    return await PortfolioPerformanceService(db, user.user.id).performance(
        portfolio_id, start, end, as_of, frequency
    )


@router.post("/portfolios/{portfolio_id}/snapshots/{day}")
async def rebuild_snapshot(
    portfolio_id: UUID, day: date, db: DB, user: USER, as_of: datetime | None = None
) -> dict[str, object]:
    row = await PortfolioSnapshotService(db, user.user.id).rebuild(portfolio_id, day, as_of)
    return {
        "id": row.id,
        "date": row.snapshot_date,
        "status": row.completeness_status,
        "value_base": row.total_value_base,
        "input_hash": row.input_hash,
        "knowledge_cutoff": row.knowledge_cutoff,
    }


@router.get("/portfolios/{portfolio_id}/snapshots")
async def snapshots(portfolio_id: UUID, db: DB, user: USER) -> list[dict[str, object]]:
    await PortfolioService(db, user.user.id).owned(portfolio_id)
    rows = (
        await db.scalars(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio_id)
            .order_by(PortfolioSnapshot.snapshot_date.desc(), PortfolioSnapshot.created_at.desc())
        )
    ).all()
    return [
        {
            "id": row.id,
            "date": row.snapshot_date,
            "status": row.completeness_status,
            "value_base": row.total_value_base,
            "input_hash": row.input_hash,
            "knowledge_cutoff": row.knowledge_cutoff,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/portfolios/{portfolio_id}/benchmark")
async def benchmark_comparison(
    portfolio_id: UUID, start: date, end: date, db: DB, user: USER, as_of: datetime | None = None
) -> dict[str, object]:
    return await PortfolioPerformanceService(db, user.user.id).benchmark(
        portfolio_id, start, end, as_of
    )
