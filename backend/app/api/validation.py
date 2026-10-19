import asyncio
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.routing import APIRoute

from app.api.data_operations import DB, Auth
from app.api.research import view
from app.assistant.documents import require_data_operator
from app.core.errors import AppError
from app.schemas.validation import (
    ChecklistInput,
    ExperimentInput,
    ForwardInput,
    PilotInput,
    RawEvidenceInput,
    ReadinessInput,
    SourcePolicy,
    ValidationStrategyInput,
)
from app.services.forward_validation import ForwardValidationService
from app.services.real_data_pilots import RealDataPilotService
from app.services.real_data_readiness import (
    CHECKLIST_FIELDS,
    RealDataReadinessService,
    source_preconditions,
)
from app.services.validation_experiments import ValidationExperimentService
from app.services.validation_records import ValidationRecords
from app.services.work_limits import work_slot


class BoundedValidationRoute(APIRoute):
    def get_route_handler(self) -> Any:
        handler = super().get_route_handler()

        async def bounded(request: Request) -> Any:
            try:
                async with asyncio.timeout(180):
                    return await handler(request)
            except TimeoutError as error:
                raise AppError(503, "VALIDATION_TIMEOUT", "Bounded validation timed out") from error

        return bounded


router = APIRouter(
    prefix="/api/v1/validation", tags=["historical validation"], route_class=BoundedValidationRoute
)


@router.get("/overview")
async def overview(db: DB, context: Auth) -> dict[str, Any]:
    from app.core.config import get_settings

    settings = get_settings()
    records = ValidationRecords(db, context.user.id)
    notes: dict[str, dict[str, str]] = {}
    for entry in await records.list("SOURCE_CHECKLIST", 1000):
        notes.setdefault(entry.request["source_slug"], entry.request["items"])
    sources = await source_preconditions(
        db,
        [
            SourcePolicy(source_slug=s, use=u)
            for s, u in (
                ("SEC_EDGAR", "fundamentals"),
                ("ECB", "fx_rates"),
                ("OPENFIGI", "mapping"),
                ("SNB", "macro"),
                ("COMPANY_IR", "fundamentals"),
                ("ALPHAVANTAGE", "prices"),
                ("MANUAL_CSV", "manual_upload"),
            )
        ],
    )
    for source in sources:
        source["operator_notes"] = notes.get(source["source_slug"], {})
    return {
        "technical_status": "PR2_VALIDATION_INFRASTRUCTURE",
        "is_data_operator": context.user.username in settings.data_operator_usernames,
        "is_ml_operator": context.user.username in settings.ml_operator_usernames,
        "real_readiness": "REQUIRES_EXPLICIT_AUDIT",
        "model_validation": "NOT_ESTABLISHED",
        "strategy_validation": "V3 RECOMMENDATIONS GATED",
        "production": "NOT_RELEASED",
        "forward_scheduling_enabled": settings.forward_shadow_enabled,
        "forward_policies": await ForwardValidationService(db, context.user).policies(),
        "sources": sources,
        "records": [
            {
                "id": str(r.id),
                "kind": r.kind,
                "parent_id": str(r.parent_id) if r.parent_id else None,
                "created_at": r.created_at,
                "result": {
                    "status": r.result.get("status", r.result.get("readiness_status")),
                    "blocking_reasons": r.result.get("blocking_reasons", []),
                    "candidate_count": len(r.request.get("candidates", [])),
                },
            }
            for r in await records.list()
        ],
    }


@router.get("/records/{identifier}")
async def record(identifier: UUID, db: DB, context: Auth) -> dict[str, Any]:
    return view(await ValidationRecords(db, context.user.id).owned(identifier))


@router.post("/readiness", status_code=201)
async def readiness(body: ReadinessInput, db: DB, context: Auth) -> dict[str, Any]:
    try:
        async with work_slot(917013), asyncio.timeout(180):
            report = await RealDataReadinessService(db, context.user.id).report(body)
            return view(
                await ValidationRecords(db, context.user.id).append(
                    "READINESS_AUDIT", body.model_dump(mode="json"), report
                )
            )
    except TimeoutError as error:
        raise AppError(
            503, "READINESS_TIMEOUT", "Bounded audit timed out; no readiness established"
        ) from error


@router.post("/source-checklists", status_code=201)
async def checklist(body: ChecklistInput, db: DB, context: Auth) -> dict[str, Any]:
    require_data_operator(context.user)
    from app.services.sources import SourceService

    await SourceService(db).get(body.source_slug)
    notes: dict[str, str] = {str(key): value for key, value in body.items.items()}
    return view(
        await ValidationRecords(db, context.user.id).append(
            "SOURCE_CHECKLIST",
            body.model_dump(mode="json"),
            {
                "status": "OPERATOR_NOTES_ONLY",
                "open_items": [key for key in CHECKLIST_FIELDS if not notes.get(key, "").strip()],
                "source_gate_changed": False,
                "reviewer_id": str(context.user.id),
            },
        )
    )


@router.post("/raw-evidence", status_code=201)
async def raw_evidence(body: RawEvidenceInput, db: DB, context: Auth) -> dict[str, Any]:
    return view(await RealDataPilotService(db, context.user).evidence(body))


@router.post("/pilots", status_code=201)
async def pilot(body: PilotInput, db: DB, context: Auth) -> dict[str, Any]:
    return view(await RealDataPilotService(db, context.user).preview(body))


@router.post("/pilots/{identifier}/{action}", status_code=201)
async def pilot_action(
    identifier: UUID, action: Literal["start", "assess"], db: DB, context: Auth
) -> dict[str, Any]:
    service = RealDataPilotService(db, context.user)
    return view(
        await (service.start(identifier) if action == "start" else service.assess(identifier))
    )


@router.post("/experiments", status_code=201)
async def experiment(body: ExperimentInput, db: DB, context: Auth) -> dict[str, Any]:
    return view(await ValidationExperimentService(db, context.user).register(body))


@router.post("/experiments/{identifier}/candidates/{index}", status_code=201)
async def queue(identifier: UUID, index: int, db: DB, context: Auth) -> dict[str, Any]:
    return view(await ValidationExperimentService(db, context.user).queue(identifier, index))


@router.post("/experiments/{identifier}/evaluate", status_code=201)
async def evaluate(identifier: UUID, db: DB, context: Auth) -> dict[str, Any]:
    return view(await ValidationExperimentService(db, context.user).evaluate(identifier))


@router.post("/strategies", status_code=201)
async def strategy(body: ValidationStrategyInput, db: DB, context: Auth) -> dict[str, Any]:
    return view(await ValidationExperimentService(db, context.user).strategy(body))


@router.get("/forward")
async def forward_report(
    db: DB,
    context: Auth,
    offset: int = Query(default=0, ge=0, le=1000000),
    limit: int = Query(default=100, ge=1, le=200),
) -> dict[str, Any]:
    return await ForwardValidationService(db, context.user).report(offset, limit)


@router.post("/forward/policies", status_code=201)
async def forward_policy(body: ForwardInput, db: DB, context: Auth) -> dict[str, Any]:
    return view(await ForwardValidationService(db, context.user).register(body))


@router.post("/forward/policies/{identifier}/run", status_code=201)
async def forward_run(identifier: UUID, db: DB, context: Auth) -> dict[str, Any]:
    return view(await ForwardValidationService(db, context.user).run(identifier))


@router.post("/forward/outcomes", status_code=201)
async def outcomes(db: DB, context: Auth) -> dict[str, Any]:
    return view(await ForwardValidationService(db, context.user).outcomes())


@router.post("/forward/policies/{identifier}/scheduling/{action}", status_code=201)
async def forward_scheduling(
    identifier: UUID, action: Literal["enable", "disable"], db: DB, context: Auth
) -> dict[str, Any]:
    return view(
        await ForwardValidationService(db, context.user).scheduling(identifier, action == "enable")
    )
