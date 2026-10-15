"""Read-only archive inspection. Reconstruction never backdates a model or prediction."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.research import view
from app.assistant.documents import cutoff_time
from app.assistant.news import archived_news
from app.assistant.tools import ToolRegistry
from app.models import (
    AnalystEstimate,
    FundamentalFact,
    Instrument,
    MLModelVersion,
    Prediction,
    PredictionOutcome,
    PriceDailyVersion,
    Recommendation,
    ResearchDocument,
    ResearchSnapshot,
    RiskSnapshot,
)
from app.schemas.assistant import TimeMachineInput
from app.services.portfolios import PortfolioService
from app.services.raw_ingestion import RawIngestionService


def existed(row: Any, cutoff: datetime) -> bool:
    return all(
        getattr(row, name) <= cutoff
        for name in (
            "known_at",
            "observed_at",
            "retrieved_at",
            "created_at",
            "generated_at",
            "information_cutoff_at",
        )
        if getattr(row, name, None) is not None
    )


class TimeMachineService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db, self.user_id = db, user_id

    async def inspect(self, request: TimeMachineInput) -> dict[str, Any]:
        cutoff = cutoff_time(request.as_of)
        now = datetime.now(UTC)
        iid, pid = request.instrument_id, request.portfolio_id
        result: dict[str, Any] = {
            "mode": request.mode,
            "as_of": cutoff.isoformat(),
            "generated_at": now.isoformat(),
            "status": "HISTORICAL_DATA_UNAVAILABLE",
            "sections": {},
            "notice": "ONLY_ARCHIVED_KNOWLEDGE_NO_BACKCAST_PREDICTIONS",
            "archive_policy": "PUBLIC_AND_FIRST_OBSERVED_AND_RETRIEVED_AND_CREATED_BEFORE_CUTOFF",
        }
        sections = result["sections"]
        model: Any
        row: Any
        rows: Any
        if pid:
            portfolio = await PortfolioService(self.db, self.user_id).owned(pid)
            if portfolio.created_at > cutoff:
                sections["portfolio"] = {"status": "NOT_ARCHIVED_AT_SELECTED_DATE", "value": None}
            else:
                # P4 replays only ledger versions that were known at the cutoff.
                valuation = await ToolRegistry(self.db, self.user_id).value(pid, cutoff)
                sections["portfolio"] = {
                    "status": valuation["status"],
                    "value": valuation,
                    "context": "REPLAY_OF_ORIGINAL_KNOWN_LEDGER_AND_PRICE_VERSIONS",
                }
            for key, model in (("risk", RiskSnapshot), ("recommendations", Recommendation)):
                rows = (
                    await self.db.scalars(
                        select(model)
                        .where(
                            model.user_id == self.user_id,
                            model.portfolio_id == pid,
                            model.created_at <= cutoff,
                        )
                        .order_by(model.created_at.desc())
                        .limit(20)
                    )
                ).all()
                rows = [
                    r
                    for r in rows
                    if existed(r, cutoff) and (getattr(r, "as_of", cutoff) <= cutoff)
                ]
                sections[key] = self.section(
                    [view(r) for r in rows], "NOT_ARCHIVED_AT_SELECTED_DATE"
                )
        if iid:
            instrument = await self.db.get(Instrument, iid)
            sections["instrument_metadata"] = {
                "status": "AVAILABLE"
                if instrument and instrument.updated_at <= cutoff
                else "NOT_ARCHIVED_AT_SELECTED_DATE",
                "value": view(instrument)
                if instrument and instrument.updated_at <= cutoff
                else None,
            }
            prices = (
                await self.db.scalars(
                    select(PriceDailyVersion)
                    .where(
                        PriceDailyVersion.instrument_id == iid,
                        PriceDailyVersion.trading_date <= cutoff.date(),
                        PriceDailyVersion.known_at <= cutoff,
                        PriceDailyVersion.observed_at <= cutoff,
                        PriceDailyVersion.created_at <= cutoff,
                        PriceDailyVersion.retrieved_at <= cutoff,
                    )
                    .order_by(
                        PriceDailyVersion.trading_date.desc(),
                        PriceDailyVersion.known_at.desc(),
                        PriceDailyVersion.created_at.desc(),
                        PriceDailyVersion.id.desc(),
                    )
                    .limit(500)
                )
            ).all()
            # Preserve rejected/conflicting heads; do not fall back to superseded accepted rows.
            heads: dict[str, Any] = {}
            for row in prices:
                heads.setdefault(str(row.trading_date), row)
            sections["prices"] = await self.provenance_section(list(heads.values())[:60])
            for key, model in (("fundamentals", FundamentalFact), ("estimates", AnalystEstimate)):
                rows = (
                    await self.db.scalars(
                        select(model)
                        .where(
                            model.instrument_id == iid,
                            model.known_at <= cutoff,
                            model.observed_at <= cutoff,
                            model.retrieved_at <= cutoff,
                            model.created_at <= cutoff,
                        )
                        .order_by(model.created_at.desc())
                        .limit(200)
                    )
                ).all()
                replaced = {r.replaces_version_id for r in rows if r.replaces_version_id}
                sections[key] = await self.provenance_section(
                    [r for r in rows if r.id not in replaced]
                )
            news = await archived_news(self.db, iid, cutoff, 30)
            sections["news"] = await self.provenance_section(list(news))
            sections["news"]["mapping_policy"] = (
                "P6_MAPPING_VERSION_OBSERVED_AND_CREATED_BEFORE_CUTOFF"
            )
            snapshots = (
                await self.db.scalars(
                    select(ResearchSnapshot)
                    .where(
                        ResearchSnapshot.instrument_id == iid,
                        ResearchSnapshot.created_at <= cutoff,
                        ResearchSnapshot.as_of <= cutoff,
                    )
                    .order_by(ResearchSnapshot.created_at.desc())
                    .limit(10)
                )
            ).all()
            sections["research"] = self.section(
                [view(r) for r in snapshots], "NOT_ARCHIVED_AT_SELECTED_DATE"
            )
            predictions = (
                await self.db.scalars(
                    select(Prediction)
                    .where(
                        Prediction.user_id == self.user_id,
                        Prediction.instrument_id == iid,
                        Prediction.created_at <= cutoff,
                        Prediction.generated_at <= cutoff,
                        Prediction.information_cutoff_at <= cutoff,
                    )
                    .order_by(Prediction.generated_at.desc())
                    .limit(50)
                )
            ).all()
            archived: list[dict[str, Any]] = []
            later_outcomes: list[dict[str, Any]] = []
            known_outcomes: list[dict[str, Any]] = []
            for row in predictions:
                ids = list(row.result.get("model_versions", []))
                if row.model_id and str(row.model_id) not in ids:
                    ids.append(str(row.model_id))
                models = [await self.db.get(MLModelVersion, UUID(m)) for m in ids]
                if any(
                    m is None or m.created_at > cutoff or m.user_id != self.user_id for m in models
                ):
                    continue
                archived.append(view(row))
                outcomes = (
                    await self.db.scalars(
                        select(PredictionOutcome).where(PredictionOutcome.prediction_id == row.id)
                    )
                ).all()
                later_outcomes.extend(view(o) for o in outcomes if o.created_at > cutoff)
                known_outcomes.extend(view(o) for o in outcomes if o.created_at <= cutoff)
            sections["predictions"] = self.section(archived, "NO HISTORICAL PREDICTION")
            sections["prediction_outcomes_known_then"] = self.section(
                known_outcomes, "NOT_ARCHIVED_AT_SELECTED_DATE"
            )
            result["later_outcomes_separate_not_known_at_cutoff"] = later_outcomes
        docs_query = select(ResearchDocument).where(
            ResearchDocument.user_id == self.user_id,
            ResearchDocument.created_at <= cutoff,
            ResearchDocument.known_at <= cutoff,
            ResearchDocument.observed_at <= cutoff,
        )
        if iid:
            docs_query = docs_query.where(ResearchDocument.instrument_id == iid)
        documents = (
            await self.db.scalars(docs_query.order_by(ResearchDocument.created_at.desc()).limit(30))
        ).all()
        sections["documents"] = await self.provenance_section(list(documents))
        if request.mode == "RECONSTRUCTED_HISTORICAL":
            # Only price/fundamental versions may be reconstructed; all other archives
            # keep the strict cutoff above, especially models, predictions and estimates.
            reconstruction: dict[str, Any] = {
                "status": "HISTORICAL_AVAILABILITY_UNVERIFIED",
                "notice": "IMPORTED_LATER_NOT_ORIGINAL_PIT_KNOWLEDGE",
            }
            if iid:
                for key, model, date_column in (
                    ("prices", PriceDailyVersion, PriceDailyVersion.trading_date),
                    ("fundamentals", FundamentalFact, FundamentalFact.period_end),
                ):
                    rows = (
                        await self.db.scalars(
                            select(model)
                            .where(
                                model.instrument_id == iid,
                                date_column <= cutoff.date(),
                                model.created_at <= now,
                                model.observed_at > cutoff,
                            )
                            .order_by(model.created_at.desc())
                            .limit(100)
                        )
                    ).all()
                    reconstruction[key] = await self.provenance_section(list(rows))
            result["reconstruction_separate"] = reconstruction
        result["status"] = (
            "AVAILABLE_WITH_EXPLICIT_GAPS"
            if any(
                section.get("status") in {"AVAILABLE", "COMPLETE", "PARTIAL"}
                for section in sections.values()
            )
            else "HISTORICAL_DATA_UNAVAILABLE"
        )
        return result

    @staticmethod
    def section(rows: list[dict[str, Any]], missing: str) -> dict[str, Any]:
        return {"status": "AVAILABLE" if rows else missing, "items": rows, "bounded": True}

    async def provenance_section(self, rows: list[Any]) -> dict[str, Any]:
        raw = RawIngestionService(self.db)
        verified, missing = [], []
        for row in rows:
            identifier = getattr(row, "raw_ingestion_id", None)
            if not identifier:
                missing.append({"id": str(row.id), "status": "HISTORICAL_AVAILABILITY_UNVERIFIED"})
                continue
            try:
                await raw.get_verified(identifier)
            except Exception:
                missing.append(
                    {
                        "id": str(row.id),
                        "status": "HISTORICAL_DATA_UNAVAILABLE",
                        "reason": "ORIGINAL_RAW_BYTES_UNAVAILABLE_OR_HASH_INVALID",
                    }
                )
                continue
            verified.append(view(row))
        return {**self.section(verified, "HISTORICAL_DATA_UNAVAILABLE"), "unavailable": missing}
