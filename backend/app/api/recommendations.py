import asyncio
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_user
from app.api.research import view
from app.core.errors import AppError
from app.db.session import get_session
from app.models.recommendations import Recommendation
from app.recommendations.backtesting import RecommendationBacktestingService, replay_archived
from app.recommendations.contracts import RULE_CONFIG, RULE_ID
from app.recommendations.preferences import PreferenceService
from app.schemas.recommendations import (
    ProfileUpdate,
    RecommendationInput,
    StrategyBacktestInput,
    StrategyReviewInput,
)
from app.services.auth import AuthContext
from app.services.portfolios import PortfolioService
from app.services.rate_limit import rate_limiter
from app.services.recommendations import RecommendationService
from app.services.work_limits import work_slot

router = APIRouter(prefix="/api/v1", tags=["recommendations"])
DB = Annotated[AsyncSession, Depends(get_session)]
Auth = Annotated[AuthContext, Depends(require_user)]


@router.get("/investment-profile")
async def profile(db: DB, context: Auth) -> dict[str, Any]:
    return await PreferenceService(db, context.user.id).current()


@router.patch("/investment-profile")
async def update_profile(request: ProfileUpdate, db: DB, context: Auth) -> dict[str, Any]:
    await PreferenceService(db, context.user.id).save(request)
    return await profile(db, context)


@router.get("/recommendations/strategies")
async def strategies(db: DB, context: Auth) -> dict[str, Any]:
    review = await RecommendationService(db, context.user.id).strategy()
    return {
        "id": RULE_ID,
        "configuration": RULE_CONFIG,
        "status": review.status if review else "UNREVIEWED",
        "review": view(review) if review else None,
    }


@router.get("/recommendations/history")
@router.get("/recommendations")
async def history(
    db: DB, context: Auth, portfolio_id: UUID | None = None, offset: Annotated[int, Query(ge=0)] = 0
) -> list[dict[str, Any]]:
    statement = select(Recommendation).where(Recommendation.user_id == context.user.id)
    if portfolio_id:
        await PortfolioService(db, context.user.id).owned(portfolio_id)
        statement = statement.where(Recommendation.portfolio_id == portfolio_id)
    rows = (
        await db.scalars(
            statement.order_by(Recommendation.created_at.desc(), Recommendation.id.desc())
            .offset(offset)
            .limit(100)
        )
    ).all()
    return [
        {
            "id": r.id,
            "instrument_id": r.instrument_id,
            "portfolio_id": r.portfolio_id,
            "category": r.category,
            "eligibility": r.eligibility,
            "generated_at": r.generated_at,
            "input_manifest_hash": r.input_manifest_hash,
        }
        for r in rows
    ]


@router.get("/recommendations/eligibility")
async def eligibility(db: DB, context: Auth) -> dict[str, Any]:
    strategy = await strategies(db, context)
    return {
        "status": "NO_VALIDATED_INVESTMENT_RECOMMENDATIONS"
        if strategy["status"] != "PRODUCTION"
        else "CANDIDATE_GATES_REQUIRED",
        "required": [
            "Validated production forecasts",
            "Real historical strategy evidence",
            "Confirmed investment profile",
            "Complete candidate and portfolio data",
        ],
        "strategy": strategy,
        "profile": await profile(db, context),
    }


@router.post("/recommendations/evaluate")
async def generate(request: RecommendationInput, db: DB, context: Auth) -> list[dict[str, Any]]:
    return [view(r) for r in await RecommendationService(db, context.user.id).run(request)]


@router.post("/recommendations/backtests")
async def backtest(request: StrategyBacktestInput, db: DB, context: Auth) -> dict[str, Any]:
    await rate_limiter.check_work("recommendation-backtests", str(context.user.id), maximum=2)
    try:
        async with work_slot(608690), asyncio.timeout(120):
            return view(await RecommendationBacktestingService(db, context.user.id).run(request))
    except TimeoutError as error:
        await db.rollback()
        raise AppError(
            503, "RECOMMENDATION_BACKTEST_TIMEOUT", "Historical evaluation timed out"
        ) from error


@router.post("/recommendations/strategy-reviews")
async def review(request: StrategyReviewInput, db: DB, context: Auth) -> dict[str, Any]:
    return view(await RecommendationBacktestingService(db, context.user.id).review(request))


@router.get("/recommendations/{identifier}")
async def detail(identifier: UUID, db: DB, context: Auth) -> dict[str, Any]:
    return view(await RecommendationService(db, context.user.id).owned(identifier))


@router.post("/recommendations/{identifier}/replay")
async def replay(identifier: UUID, db: DB, context: Auth) -> dict[str, Any]:
    return replay_archived(await RecommendationService(db, context.user.id).owned(identifier))
