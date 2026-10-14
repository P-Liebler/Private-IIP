import asyncio
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_user
from app.api.research import view
from app.backtesting.baselines import train_only_baselines
from app.backtesting.engine import run_backtest
from app.backtesting.validation import LabelInterval, WalkForwardSplitter
from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_session
from app.models import (
    BacktestRun,
    DatasetVersion,
    FeatureSnapshot,
    Instrument,
    PITJob,
    UniverseDefinition,
    UniverseMembershipVersion,
    WalkForwardSplit,
)
from app.schemas.pit import BacktestInput, DatasetInput, UniverseInput
from app.services.auth import AuthContext
from app.services.fundamentals import digest
from app.services.market_calendar import MarketCalendarService
from app.services.market_queries import pit_cutoff
from app.services.pit_datasets import DatasetBuilder, code_manifest
from app.services.pit_features import FeatureSnapshotService
from app.services.pit_jobs import execute_job
from app.services.pit_macro import MacroImportService
from app.services.pit_universe import UniverseService
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService

router = APIRouter(prefix="/api/v1", tags=["point-in-time / backtesting"])
DB = Annotated[AsyncSession, Depends(get_session)]
Auth = Annotated[AuthContext, Depends(require_user)]


class CommitInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raw_id: UUID


class SplitInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    validation_start: AwareDatetime
    test_start: AwareDatetime
    final_end: AwareDatetime
    embargo_sessions: int = Field(default=90, ge=30, le=252)


@router.post("/macro/imports/upload")
async def macro_upload(request: Request, db: DB, context: Auth) -> dict[str, Any]:
    source = await SourceService(db).get("MANUAL_PIT")
    SourceGate.require_enabled(source, "macro")
    data = await request.body()
    if len(data) > 5_000_000:
        raise AppError(413, "UPLOAD_TOO_LARGE", "Maximum 5MB")
    raw = await RawIngestionService(db).store(
        data=data,
        source_id=source.id,
        source_slug=source.slug,
        resource_type="macro_import",
        content_type="text/csv",
        request_metadata={"user_id": str(context.user.id)},
    )
    return {"raw_id": raw.id, "sha256": raw.sha256}


@router.post("/macro/imports/preview")
async def macro_preview(body: CommitInput, db: DB, context: Auth) -> dict[str, Any]:
    return await MacroImportService(db).preview(body.raw_id, context.user.id)


@router.post("/macro/imports/commit")
async def macro_commit(body: CommitInput, db: DB, context: Auth) -> dict[str, int]:
    return await MacroImportService(db).commit(body.raw_id, context.user.id)


@router.post("/datasets/{dataset_id}/splits")
async def split_dataset(
    dataset_id: UUID, body: SplitInput, db: DB, context: Auth
) -> dict[str, Any]:
    dataset = await DatasetBuilder(db).owned(dataset_id, context.user.id)
    # Cross-exchange universes are split conservatively per instrument calendar.
    calendar = MarketCalendarService()
    intervals = []
    embargos = []
    horizon = dataset.configuration["target_horizon"]
    for index, row in enumerate(dataset.rows):
        target = row["target"]
        if target["status"] != "AVAILABLE" or not row["eligible"]:
            continue
        instrument = await db.get(Instrument, UUID(row["instrument_id"]))
        assert instrument and instrument.exchange
        day = body.validation_start.date()
        for _ in range(body.embargo_sessions):
            day = calendar.previous_session(instrument.exchange, day)
        embargo = calendar.session_close(instrument.exchange, day)
        embargos.append(embargo)
        interval = LabelInterval(
            str(index),
            datetime.fromisoformat(target["signal_as_of"]),
            datetime.fromisoformat(target["label_start"]),
            datetime.fromisoformat(target["label_end"]),
            datetime.fromisoformat(target["label_available_at"]),
        )
        partitions = WalkForwardSplitter().split(
            [interval],
            body.validation_start,
            body.test_start,
            body.final_end,
            embargo,
            body.embargo_sessions,
            horizon,
            instrument.exchange,
        )
        intervals.append(
            {
                "row_id": index,
                "partition": next(k for k, v in partitions.items() if v),
                "label": target["classification"],
                "excess_return": target["excess_return"],
                "label_available_at": target["label_available_at"],
            }
        )
    training = [r for r in intervals if r["partition"] == "training"]
    baselines = (
        train_only_baselines(training, min(embargos))
        if embargos
        else {
            "constant_50": "0.5",
            "prevalence": None,
            "zero_excess_return": "0",
            "historical_mean": None,
        }
    )
    result = {
        "partitions": intervals,
        "baselines": baselines,
        "policy": "session-embargo+actual-label-purge-v1",
        "historical_data_limitations": dataset.configuration["availability_mode"] != "STRICT_PIT",
    }
    configuration = body.model_dump(mode="json")
    split = WalkForwardSplit(
        dataset_id=dataset_id,
        configuration=configuration,
        result=result,
        content_hash=digest(
            {"dataset": dataset.content_hash, "configuration": configuration, "result": result}
        ),
    )
    db.add(split)
    await db.commit()
    return view(split)


@router.get("/universes")
async def universes(db: DB, context: Auth) -> list[dict[str, Any]]:
    return [
        view(r)
        for r in (
            await db.scalars(
                select(UniverseDefinition)
                .where(UniverseDefinition.user_id == context.user.id)
                .order_by(UniverseDefinition.created_at.desc())
                .limit(100)
            )
        ).all()
    ]


@router.post("/universes", status_code=201)
async def create_universe(body: UniverseInput, db: DB, context: Auth) -> dict[str, Any]:
    row = UniverseDefinition(
        user_id=context.user.id,
        name=body.name,
        configuration={"kind": body.kind, "history": "UNVERIFIED UNTIL DOCUMENTED REVIEW"},
    )
    db.add(row)
    await db.commit()
    return view(row)


@router.get("/universes/{universe_id}/membership")
async def membership(universe_id: UUID, db: DB, context: Auth) -> list[dict[str, Any]]:
    await UniverseService(db).owned(universe_id, context.user.id)
    return [
        view(r)
        for r in (
            await db.scalars(
                select(UniverseMembershipVersion)
                .where(UniverseMembershipVersion.universe_id == universe_id)
                .order_by(UniverseMembershipVersion.observed_at.desc())
                .limit(1000)
            )
        ).all()
    ]


@router.post("/universes/{universe_id}/imports/upload")
async def membership_upload(
    universe_id: UUID, request: Request, db: DB, context: Auth
) -> dict[str, Any]:
    data = await request.body()
    if len(data) > 5_000_000:
        raise AppError(413, "UPLOAD_TOO_LARGE", "Maximum 5MB")
    raw = await UniverseService(db).upload(universe_id, context.user.id, data)
    return {"raw_id": str(raw.id), "sha256": raw.sha256}


@router.post("/universes/{universe_id}/imports/preview")
async def membership_preview(
    universe_id: UUID, body: CommitInput, db: DB, context: Auth
) -> dict[str, Any]:
    return await UniverseService(db).preview(universe_id, context.user.id, body.raw_id)


@router.post("/universes/{universe_id}/imports/commit")
async def membership_commit(
    universe_id: UUID, body: CommitInput, db: DB, context: Auth
) -> dict[str, int]:
    return await UniverseService(db).commit(universe_id, context.user.id, body.raw_id)


@router.get("/datasets")
async def datasets(db: DB, context: Auth) -> list[dict[str, Any]]:
    return [
        {
            "id": r.id,
            "content_hash": r.content_hash,
            "configuration": r.configuration,
            "quality": r.quality,
            "created_at": r.created_at,
        }
        for r in (
            await db.scalars(
                select(DatasetVersion)
                .where(DatasetVersion.user_id == context.user.id)
                .order_by(DatasetVersion.created_at.desc())
                .limit(100)
            )
        ).all()
    ]


@router.post("/datasets/build")
async def build_dataset(body: DatasetInput, db: DB, context: Auth) -> dict[str, Any]:
    try:
        row, job_id = await execute_job(
            db,
            context.user.id,
            "DATASET_BUILD",
            lambda: DatasetBuilder(db).build(body, context.user.id),
        )
    except TimeoutError as error:
        await db.rollback()
        raise AppError(408, "BUILD_TIMEOUT", "Bounded dataset build timed out") from error
    await db.commit()
    return {
        "id": row.id,
        "job_id": job_id,
        "content_hash": row.content_hash,
        "quality": row.quality,
        "status": "COMPLETED",
    }


@router.get("/datasets/{dataset_id}")
async def dataset_detail(dataset_id: UUID, db: DB, context: Auth) -> dict[str, Any]:
    return view(await DatasetBuilder(db).owned(dataset_id, context.user.id))


@router.get("/datasets/{dataset_id}/quality")
async def dataset_quality(dataset_id: UUID, db: DB, context: Auth) -> dict[str, Any]:
    return (await DatasetBuilder(db).owned(dataset_id, context.user.id)).quality


@router.post("/datasets/{dataset_id}/rebuild")
async def dataset_rebuild(dataset_id: UUID, db: DB, context: Auth) -> dict[str, Any]:
    return await DatasetBuilder(db).rebuild(dataset_id, context.user.id)


@router.get("/features/{instrument_id}")
async def instrument_features(
    instrument_id: UUID,
    db: DB,
    _context: Auth,
    as_of: datetime | None = None,
    availability_mode: Literal["STRICT_PIT", "RECONSTRUCTED_HISTORICAL"] = "STRICT_PIT",
) -> dict[str, Any]:
    snapshot = await FeatureSnapshotService(db).build(
        instrument_id, pit_cutoff(as_of), availability_mode
    )
    await db.commit()
    return view(snapshot)


@router.get("/features/{instrument_id}/history")
async def feature_history(
    instrument_id: UUID, db: DB, _context: Auth, limit: int = Query(50, ge=1, le=100)
) -> list[dict[str, Any]]:
    return [
        view(r)
        for r in (
            await db.scalars(
                select(FeatureSnapshot)
                .where(FeatureSnapshot.instrument_id == instrument_id)
                .order_by(FeatureSnapshot.as_of.desc())
                .limit(limit)
            )
        ).all()
    ]


@router.post("/backtests")
async def create_backtest(body: BacktestInput, db: DB, context: Auth) -> dict[str, Any]:
    dataset = await DatasetBuilder(db).owned(body.dataset_id, context.user.id)
    pinned = {
        "configuration": dataset.configuration,
        "rows": dataset.rows,
        "market": dataset.manifest["market"],
        "actions": dataset.manifest["actions"],
        "quality": dataset.quality,
    }

    async def simulate() -> BacktestRun:
        async with asyncio.timeout(get_settings().p6_timeout_seconds):
            result = await asyncio.to_thread(run_backtest, pinned, body)
            config = {
                **body.model_dump(mode="json"),
                "code_version": code_manifest(),
                "strategy_version": "deterministic-baselines-v1",
                "cost_model_version": "commission-spread-slippage-v1",
                "execution_policy_version": "next-session-v1",
            }
            row = BacktestRun(
                user_id=context.user.id,
                dataset_id=dataset.id,
                configuration=config,
                content_hash=digest(
                    {"dataset": dataset.content_hash, "config": config, "result": result}
                ),
                result=result,
            )
            db.add(row)
            await db.flush()
            return row

    row, job_id = await execute_job(db, context.user.id, "BACKTEST", simulate)
    return {**view(row), "job_id": job_id}


@router.get("/backtests")
async def backtests(db: DB, context: Auth) -> list[dict[str, Any]]:
    return [
        {
            "id": r.id,
            "dataset_id": r.dataset_id,
            "configuration": r.configuration,
            "status": r.result["status"],
            "created_at": r.created_at,
        }
        for r in (
            await db.scalars(
                select(BacktestRun)
                .where(BacktestRun.user_id == context.user.id)
                .order_by(BacktestRun.created_at.desc())
                .limit(100)
            )
        ).all()
    ]


@router.get("/pit/jobs/{job_id}")
async def job_status(job_id: UUID, db: DB, context: Auth) -> dict[str, Any]:
    job = await db.get(PITJob, job_id)
    if job is None or job.user_id != context.user.id:
        raise AppError(404, "JOB_NOT_FOUND", "Job not found")
    from datetime import UTC, timedelta

    if job.status == "RUNNING" and job.started_at < datetime.now(UTC) - timedelta(
        seconds=get_settings().p6_timeout_seconds + 30
    ):
        job.status = "FAILED"
        job.error_code = "PROCESS_INTERRUPTED"
        job.completed_at = datetime.now(UTC)
        await db.commit()
    return view(job)


async def owned_run(run_id: UUID, db: AsyncSession, user_id: UUID) -> BacktestRun:
    row = await db.get(BacktestRun, run_id)
    if row is None or row.user_id != user_id:
        raise AppError(404, "BACKTEST_NOT_FOUND", "Backtest not found")
    return row


@router.get("/backtests/{run_id}")
async def backtest_detail(run_id: UUID, db: DB, context: Auth) -> dict[str, Any]:
    return view(await owned_run(run_id, db, context.user.id))


@router.get("/backtests/{run_id}/trades")
async def backtest_trades(run_id: UUID, db: DB, context: Auth) -> dict[str, Any]:
    row = await owned_run(run_id, db, context.user.id)
    return {
        "orders": row.result["orders"],
        "fills": row.result["fills"],
        "signals": row.result["signals"],
    }


@router.get("/backtests/{run_id}/metrics")
async def backtest_metrics(run_id: UUID, db: DB, context: Auth) -> dict[str, Any]:
    return dict((await owned_run(run_id, db, context.user.id)).result["metrics"])
