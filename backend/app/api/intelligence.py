import asyncio
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_user
from app.api.research import view
from app.assistant.metrics import observe
from app.assistant.runtime import provider
from app.assistant.safety import render_answer
from app.core.errors import AppError
from app.db.session import get_session
from app.models import (
    AlertEvaluation,
    AlertEvent,
    AlertRule,
    DailyBrief,
    Notification,
    OptimizerRun,
)
from app.schemas.assistant import (
    AlertRuleInput,
    BriefConfigInput,
    EvidenceFact,
    OptimizerInput,
    TimeMachineInput,
)
from app.services.alerts import AlertEvaluationService
from app.services.auth import AuthContext
from app.services.daily_brief import DailyBriefService
from app.services.financial_events import FinancialEventService
from app.services.portfolio_optimizer import PortfolioOptimizerService
from app.services.portfolios import PortfolioService
from app.services.rate_limit import rate_limiter
from app.services.time_machine import TimeMachineService
from app.services.work_limits import work_slot

router = APIRouter(prefix="/api/v1", tags=["intelligence"])
DB = Annotated[AsyncSession, Depends(get_session)]
Auth = Annotated[AuthContext, Depends(require_user)]


@router.post("/alert-rules", status_code=201)
async def create_rule(request: AlertRuleInput, db: DB, context: Auth) -> dict[str, Any]:
    return view(await AlertEvaluationService(db, context.user.id).save(request))


@router.patch("/alert-rules/{identifier}")
async def update_rule(
    identifier: UUID, request: AlertRuleInput, db: DB, context: Auth
) -> dict[str, Any]:
    return view(await AlertEvaluationService(db, context.user.id).save(request, identifier))


@router.delete("/alert-rules/{identifier}", status_code=204)
async def archive_rule(identifier: UUID, db: DB, context: Auth) -> Response:
    row = await AlertEvaluationService(db, context.user.id).owned(identifier, lock=True)
    row.archived = True
    await db.commit()
    return Response(status_code=204)


@router.get("/alert-rules")
async def rules(db: DB, context: Auth) -> list[dict[str, Any]]:
    rows = (
        await db.scalars(
            select(AlertRule)
            .where(AlertRule.user_id == context.user.id)
            .order_by(AlertRule.created_at.desc())
            .limit(100)
        )
    ).all()
    result = []
    service = AlertEvaluationService(db, context.user.id)
    for row in rows:
        version = await service.latest(row.id)
        evaluation = await db.scalar(
            select(AlertEvaluation)
            .where(AlertEvaluation.rule_version_id == version.id)
            .order_by(AlertEvaluation.created_at.desc())
            .limit(1)
        )
        result.append(
            {
                **view(row),
                "version": view(version),
                "latest_evaluation": view(evaluation) if evaluation else None,
            }
        )
    return result


@router.post("/alert-rules/{identifier}/evaluate")
async def evaluate_rule(identifier: UUID, db: DB, context: Auth) -> dict[str, Any]:
    await rate_limiter.check_work("alert-evaluation", str(context.user.id), maximum=20)
    result = await AlertEvaluationService(db, context.user.id).evaluate(identifier)
    return view(result) if result else {"status": "DISABLED"}


@router.get("/alert-events")
async def events(
    db: DB, context: Auth, offset: Annotated[int, Query(ge=0)] = 0
) -> list[dict[str, Any]]:
    rows = (
        await db.scalars(
            select(AlertEvent)
            .where(AlertEvent.user_id == context.user.id)
            .order_by(AlertEvent.created_at.desc())
            .offset(offset)
            .limit(100)
        )
    ).all()
    return [view(row) for row in rows]


@router.get("/alert-rules/{identifier}/evaluations")
async def evaluation_history(
    identifier: UUID, db: DB, context: Auth, offset: Annotated[int, Query(ge=0)] = 0
) -> list[dict[str, Any]]:
    await AlertEvaluationService(db, context.user.id).owned(identifier)
    rows = (
        await db.scalars(
            select(AlertEvaluation)
            .where(
                AlertEvaluation.rule_id == identifier, AlertEvaluation.user_id == context.user.id
            )
            .order_by(AlertEvaluation.created_at.desc())
            .offset(offset)
            .limit(100)
        )
    ).all()
    return [view(row) for row in rows]


@router.get("/notifications")
async def notifications(
    db: DB, context: Auth, offset: Annotated[int, Query(ge=0)] = 0
) -> dict[str, Any]:
    rows = (
        await db.scalars(
            select(Notification)
            .where(Notification.user_id == context.user.id)
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(100)
        )
    ).all()
    unread = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == context.user.id, Notification.read_at.is_(None))
    )
    return {"items": [view(row) for row in rows], "unread_count": unread}


@router.post("/notifications/{identifier}/read")
async def read_notification(identifier: UUID, db: DB, context: Auth) -> dict[str, Any]:
    row = await db.get(Notification, identifier)
    if not row or row.user_id != context.user.id:
        raise AppError(404, "NOTIFICATION_NOT_FOUND", "Notification not found")
    row.read_at = row.read_at or datetime.now(UTC)
    await db.commit()
    return view(row)


@router.get("/daily-brief/configuration")
async def brief_config(db: DB, context: Auth) -> dict[str, Any]:
    return (await DailyBriefService(db, context.user.id).configuration()).model_dump(mode="json")


@router.patch("/daily-brief/configuration")
async def update_brief_config(request: BriefConfigInput, db: DB, context: Auth) -> dict[str, Any]:
    return view(await DailyBriefService(db, context.user.id).configure(request))


@router.post("/daily-brief/generate")
async def generate_brief(db: DB, context: Auth) -> dict[str, Any]:
    await rate_limiter.check_work("daily-brief", str(context.user.id), maximum=4)
    try:
        async with work_slot(608712), asyncio.timeout(90):
            return view(await DailyBriefService(db, context.user.id).generate())
    except TimeoutError as error:
        raise AppError(504, "BRIEF_TIMEOUT", "Brief generation exceeded its time budget") from error


@router.get("/daily-brief")
async def briefs(
    db: DB, context: Auth, offset: Annotated[int, Query(ge=0)] = 0
) -> list[dict[str, Any]]:
    rows = (
        await db.scalars(
            select(DailyBrief)
            .where(DailyBrief.user_id == context.user.id)
            .order_by(DailyBrief.local_date.desc())
            .offset(offset)
            .limit(100)
        )
    ).all()
    return [view(row) for row in rows]


@router.get("/daily-brief/{identifier}")
async def brief_detail(identifier: UUID, db: DB, context: Auth) -> dict[str, Any]:
    return view(await DailyBriefService(db, context.user.id).owned(identifier))


@router.post("/daily-brief/{identifier}/explain")
async def explain_brief(identifier: UUID, db: DB, context: Auth) -> dict[str, Any]:
    await rate_limiter.check_work("brief-explanation", str(context.user.id), maximum=4)
    row = await DailyBriefService(db, context.user.id).owned(identifier)
    facts = [EvidenceFact.model_validate(f) for f in row.result["facts"][:40]]
    try:
        async with work_slot(608710), asyncio.timeout(90):
            selection, version = await provider().select(
                "Explain only the supplied archived brief facts.",
                [f.model_dump(mode="json") for f in facts],
            )
            answer = render_answer(facts, selection)
        observe("brief_explanation", True)
        return {"text": answer, "model_version": version, "brief_hash": row.content_hash}
    except (AppError, TimeoutError):
        observe("brief_explanation", False)
        return {
            "status": "LLM_UNAVAILABLE",
            "text": None,
            "brief_hash": row.content_hash,
            "notice": "STRUCTURED_BRIEF_REMAINS_AVAILABLE",
        }


@router.post("/financial-events/import", status_code=201)
async def import_event(
    request: Request, db: DB, context: Auth, source_slug: str = Query(max_length=60)
) -> dict[str, Any]:
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 50000:
            raise AppError(413, "EVENT_SIZE_LIMIT", "Event JSON exceeds 50 KB")
    return view(
        await FinancialEventService(db, context.user.id).import_bytes(
            source_slug, bytes(body), context.user
        )
    )


@router.post("/portfolios/{portfolio_id}/optimizer")
async def optimize_portfolio(
    portfolio_id: UUID, request: OptimizerInput, db: DB, context: Auth
) -> dict[str, Any]:
    await rate_limiter.check_work("optimizer", str(context.user.id), maximum=4)
    async with work_slot(608713):
        return view(await PortfolioOptimizerService(db, context.user.id).run(portfolio_id, request))


@router.get("/portfolios/{portfolio_id}/optimizer")
async def optimizer_history(portfolio_id: UUID, db: DB, context: Auth) -> list[dict[str, Any]]:
    await PortfolioService(db, context.user.id).owned(portfolio_id)
    rows = (
        await db.scalars(
            select(OptimizerRun)
            .where(
                OptimizerRun.user_id == context.user.id, OptimizerRun.portfolio_id == portfolio_id
            )
            .order_by(OptimizerRun.created_at.desc())
            .limit(30)
        )
    ).all()
    return [view(row) for row in rows]


@router.post("/time-machine")
async def time_machine(request: TimeMachineInput, db: DB, context: Auth) -> dict[str, Any]:
    await rate_limiter.check_work("time-machine", str(context.user.id), maximum=10)
    try:
        async with work_slot(608714), asyncio.timeout(45):
            result = await TimeMachineService(db, context.user.id).inspect(request)
            observe("time_machine", result["status"] == "AVAILABLE_WITH_EXPLICIT_GAPS")
            return result
    except TimeoutError as error:
        observe("time_machine", False)
        raise AppError(
            504, "TIME_MACHINE_TIMEOUT", "Archive inspection exceeded its time budget"
        ) from error
