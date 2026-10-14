import asyncio
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_user
from app.api.research import view
from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_session
from app.models import RiskSnapshot, ScenarioDefinition, ScenarioRun, WhatIfRun
from app.schemas.risk import RiskInput, ScenarioInput, WhatIfInput
from app.services.auth import AuthContext
from app.services.portfolio_risk import PortfolioRiskService
from app.services.portfolios import PortfolioService
from app.services.risk_simulations import RiskSimulationService

router = APIRouter(prefix="/api/v1", tags=["portfolio-risk"])
DB = Annotated[AsyncSession, Depends(get_session)]
Auth = Annotated[AuthContext, Depends(require_user)]


@router.post("/portfolios/{portfolio_id}/risk")
async def calculate(
    portfolio_id: UUID, request: RiskInput, db: DB, context: Auth
) -> dict[str, Any]:
    try:
        async with asyncio.timeout(get_settings().p8_timeout_seconds):
            return view(
                await PortfolioRiskService(db, context.user.id).calculate(portfolio_id, request)
            )
    except TimeoutError as error:
        await db.rollback()
        raise AppError(
            503, "RISK_TIMEOUT", "Risk calculation exceeded its resource limit"
        ) from error


@router.get("/portfolios/{portfolio_id}/risk/history")
@router.get("/portfolios/{portfolio_id}/risk-history", include_in_schema=False)
async def history(
    portfolio_id: UUID, db: DB, context: Auth, offset: Annotated[int, Query(ge=0)] = 0
) -> list[dict[str, Any]]:
    await PortfolioService(db, context.user.id).owned(portfolio_id)
    rows = (
        (
            await db.execute(
                select(
                    RiskSnapshot.id,
                    RiskSnapshot.created_at,
                    RiskSnapshot.as_of,
                    RiskSnapshot.content_hash,
                    RiskSnapshot.result["status"].astext.label("status"),
                )
                .where(
                    RiskSnapshot.portfolio_id == portfolio_id,
                    RiskSnapshot.user_id == context.user.id,
                )
                .order_by(RiskSnapshot.created_at.desc(), RiskSnapshot.id.desc())
                .offset(offset)
                .limit(100)
            )
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]


@router.get("/portfolios/{portfolio_id}/risk")
async def latest(portfolio_id: UUID, db: DB, context: Auth) -> dict[str, Any]:
    rows = await history(portfolio_id, db, context)
    return (
        view(
            await PortfolioRiskService(db, context.user.id).owned_snapshot(
                portfolio_id, rows[0]["id"]
            )
        )
        if rows
        else {"status": "RISK_UNAVAILABLE", "reason": "NO_SAVED_RISK_SNAPSHOT"}
    )


@router.get("/portfolios/{portfolio_id}/correlations")
async def correlation_view(
    portfolio_id: UUID, db: DB, context: Auth, snapshot_id: UUID | None = None
) -> dict[str, Any]:
    row = (
        view(
            await PortfolioRiskService(db, context.user.id).owned_snapshot(
                portfolio_id, snapshot_id
            )
        )
        if snapshot_id
        else await latest(portfolio_id, db, context)
    )
    return (
        {"snapshot_id": row.get("id"), "matrices": row["result"]["correlations"]}
        if "result" in row
        else row
    )


@router.get("/portfolios/{portfolio_id}/exposures")
async def exposure_view(
    portfolio_id: UUID, db: DB, context: Auth, snapshot_id: UUID | None = None
) -> dict[str, Any]:
    row = (
        view(
            await PortfolioRiskService(db, context.user.id).owned_snapshot(
                portfolio_id, snapshot_id
            )
        )
        if snapshot_id
        else await latest(portfolio_id, db, context)
    )
    return (
        {"snapshot_id": row.get("id"), "exposures": row["result"]["exposures"]}
        if "result" in row
        else row
    )


@router.get("/portfolios/{portfolio_id}/risk/{snapshot_id}")
async def detail(portfolio_id: UUID, snapshot_id: UUID, db: DB, context: Auth) -> dict[str, Any]:
    return view(
        await PortfolioRiskService(db, context.user.id).owned_snapshot(portfolio_id, snapshot_id)
    )


@router.get("/scenario-definitions")
async def definitions(db: DB, context: Auth) -> list[dict[str, Any]]:
    return [
        view(row)
        for row in (
            await db.scalars(select(ScenarioDefinition).order_by(ScenarioDefinition.slug))
        ).all()
    ]


@router.post("/portfolios/{portfolio_id}/scenarios")
async def run_scenario(
    portfolio_id: UUID, request: ScenarioInput, db: DB, context: Auth
) -> dict[str, Any]:
    return view(await RiskSimulationService(db, context.user.id).scenario(portfolio_id, request))


@router.post("/portfolios/{portfolio_id}/what-if")
async def run_whatif(
    portfolio_id: UUID, request: WhatIfInput, db: DB, context: Auth
) -> dict[str, Any]:
    try:
        async with asyncio.timeout(get_settings().p8_timeout_seconds):
            return view(
                await RiskSimulationService(db, context.user.id).whatif(portfolio_id, request)
            )
    except TimeoutError as error:
        await db.rollback()
        raise AppError(
            503, "WHATIF_TIMEOUT", "What-if calculation exceeded its resource limit"
        ) from error


@router.get("/portfolios/{portfolio_id}/simulation-history")
async def simulation_history(
    portfolio_id: UUID, db: DB, context: Auth, offset: Annotated[int, Query(ge=0)] = 0
) -> dict[str, Any]:
    await PortfolioService(db, context.user.id).owned(portfolio_id)
    result = {}
    for key, model in (("scenarios", ScenarioRun), ("what_if", WhatIfRun)):
        rows = (
            (
                await db.execute(
                    select(
                        model.id,
                        model.created_at,
                        model.risk_snapshot_id,
                        model.content_hash,
                        model.result["status"].astext.label("status"),
                    )
                    .where(model.portfolio_id == portfolio_id, model.user_id == context.user.id)
                    .order_by(model.created_at.desc(), model.id.desc())
                    .offset(offset)
                    .limit(100)
                )
            )
            .mappings()
            .all()
        )
        result[key] = [dict(row) for row in rows]
    return result


async def simulation_detail(
    portfolio_id: UUID, run_id: UUID, model: Any, db: AsyncSession, context: AuthContext
) -> dict[str, Any]:
    await PortfolioService(db, context.user.id).owned(portfolio_id)
    row = await db.get(model, run_id)
    if row is None or row.user_id != context.user.id or row.portfolio_id != portfolio_id:
        raise AppError(404, "SIMULATION_NOT_FOUND", "Simulation not found")
    return view(row)


@router.get("/portfolios/{portfolio_id}/scenarios/{run_id}")
async def scenario_detail(
    portfolio_id: UUID, run_id: UUID, db: DB, context: Auth
) -> dict[str, Any]:
    return await simulation_detail(portfolio_id, run_id, ScenarioRun, db, context)


@router.get("/portfolios/{portfolio_id}/what-if/{run_id}")
async def whatif_detail(portfolio_id: UUID, run_id: UUID, db: DB, context: Auth) -> dict[str, Any]:
    return await simulation_detail(portfolio_id, run_id, WhatIfRun, db, context)
