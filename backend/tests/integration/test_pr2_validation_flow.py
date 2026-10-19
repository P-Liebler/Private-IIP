"""Local persistence and blocked-real-data flows; no live providers."""

import asyncio
import secrets
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_engine, get_session_factory
from app.main import create_app
from app.models import (
    AuditEvent,
    CollectorJob,
    DatasetVersion,
    Instrument,
    MLModelVersion,
    MLTrainingRun,
    ModelPromotionReview,
    Portfolio,
    Prediction,
    PredictionOutcome,
    SessionRecord,
    UniverseDefinition,
    UniverseMembershipVersion,
    User,
    ValidationRecord,
)
from app.schemas.data_operations import CollectionInput
from app.schemas.validation import (
    ExperimentInput,
    ForwardInput,
    PilotInput,
    ReadinessInput,
    SourcePolicy,
)
from app.services.auth import AuthService
from app.services.backfill_jobs import BackfillJobService
from app.services.forward_validation import ForwardValidationService
from app.services.fundamentals import digest
from app.services.predictions import PredictionService
from app.services.real_data_pilots import RealDataPilotService
from app.services.real_data_readiness import RealDataReadinessService
from app.services.validation_experiments import ValidationExperimentService
from app.services.validation_records import ValidationRecords
from tests.unit.test_pr2_validation import candidate, protocol


@asynccontextmanager
async def fixture(monkeypatch):
    ids = [uuid4() for _ in range(4)]
    datasets, uid, oid, universe_id = [], None, None, uuid4()
    try:
        async with get_session_factory()() as db:
            user = await AuthService(db).create_user(
                "pr2_" + uuid4().hex[:12], secrets.token_urlsafe(30)
            )
            other = await AuthService(db).create_user(
                "pr2_" + uuid4().hex[:12], secrets.token_urlsafe(30)
            )
            uid, oid = user.id, other.id
            monkeypatch.setattr(
                get_settings(), "data_operator_usernames", [user.username, other.username]
            )
            monkeypatch.setattr(get_settings(), "ml_operator_usernames", [user.username])
            for iid in ids:
                db.add(
                    Instrument(
                        id=iid,
                        name="SYNTHETIC PR2 integration only",
                        asset_type="STOCK",
                        currency="CHF",
                        exchange=None,
                    )
                )
            db.add(
                UniverseDefinition(
                    id=universe_id,
                    user_id=uid,
                    name="SYNTHETIC PR2",
                    configuration={"synthetic": True},
                )
            )
            await db.flush()
            for horizon in (30, 90):
                config = {
                    "universe_id": str(universe_id),
                    "benchmark_id": str(ids[3]),
                    "start": "2024-01-01",
                    "end": "2024-01-05",
                    "target_horizon": horizon,
                    "base_currency": "CHF",
                    "availability_mode": "STRICT_PIT",
                    "data_context": "SYNTHETIC_SIMULATION_NOT_REAL_ARCHIVE",
                }
                manifest = {
                    "versions": {},
                    "version_hashes": {},
                    "feature_snapshot_ids": [],
                    "market": {},
                    "actions": {},
                }
                quality = {"survivorship_risk": True}
                dataset = DatasetVersion(
                    user_id=uid,
                    universe_id=universe_id,
                    configuration=config,
                    manifest=manifest,
                    rows=[],
                    quality=quality,
                    content_hash=digest(
                        {
                            "configuration": config,
                            "manifest": manifest,
                            "rows": [],
                            "quality": quality,
                        }
                    ),
                )
                db.add(dataset)
                await db.flush()
                datasets.append(dataset.id)
            portfolio = Portfolio(
                user_id=uid, name="SYNTHETIC PR2 empty ledger", base_currency="CHF"
            )
            db.add(portfolio)
            await db.commit()
            try:
                yield SimpleNamespace(
                    db=db,
                    user=user,
                    other=other,
                    uid=uid,
                    oid=oid,
                    ids=ids,
                    datasets=datasets,
                    universe_id=universe_id,
                    portfolio_id=portfolio.id,
                )
            finally:
                await db.rollback()
                users = [uid, oid]
                prediction_ids = select(Prediction.id).where(Prediction.user_id.in_(users))
                for model, condition in (
                    (ValidationRecord, ValidationRecord.user_id.in_(users)),
                    (PredictionOutcome, PredictionOutcome.prediction_id.in_(prediction_ids)),
                    (Prediction, Prediction.user_id.in_(users)),
                    (ModelPromotionReview, ModelPromotionReview.reviewer_id.in_(users)),
                    (MLModelVersion, MLModelVersion.user_id.in_(users)),
                    (MLTrainingRun, MLTrainingRun.user_id.in_(users)),
                    (CollectorJob, CollectorJob.user_id.in_(users)),
                    (DatasetVersion, DatasetVersion.user_id.in_(users)),
                    (
                        UniverseMembershipVersion,
                        UniverseMembershipVersion.universe_id == universe_id,
                    ),
                    (UniverseDefinition, UniverseDefinition.id == universe_id),
                    (Portfolio, Portfolio.user_id.in_(users)),
                    (SessionRecord, SessionRecord.user_id.in_(users)),
                    (AuditEvent, AuditEvent.actor_user_id.in_(users)),
                    (User, User.id.in_(users)),
                    (Instrument, Instrument.id.in_(ids)),
                ):
                    await db.execute(delete(model).where(condition))
                await db.commit()
    finally:
        await get_engine().dispose()


def request(f):
    return ReadinessInput(
        universe_id=f.universe_id,
        benchmark_id=f.ids[3],
        instrument_ids=f.ids[:3],
        start="2024-01-01",
        end="2024-01-05",
        dataset_id=f.datasets[0],
        source_policy=[{"source_slug": "MANUAL_CSV", "use": "manual_upload"}],
    )


@pytest.mark.integration
def test_pr2_real_audit_pilot_rights_owner_dedup_and_immutable_notes(monkeypatch):
    async def run():
        async with fixture(monkeypatch) as f:
            audit = await RealDataReadinessService(f.db, f.uid).report(request(f))
            assert audit["readiness_status"] == "BLOCKED_BY_REAL_DATA"
            assert "SYNTHETIC_OR_UNVERIFIED_INPUTS" in audit["blocking_reasons"]
            assert audit["counts"]["historical_sessions"] is None
            assert audit["counts"]["eligible_oos_samples"] is None
            assert audit["origins"]["all_real"] is False
            pilot = await RealDataPilotService(f.db, f.user).preview(
                PilotInput(
                    readiness=request(f).model_copy(
                        update={"source_policy": [SourcePolicy(source_slug="ECB", use="fx_rates")]}
                    ),
                    collections=[
                        CollectionInput(
                            source_slug="ECB", kind="ECB_FX", start="2024-01-01", end="2024-01-05"
                        )
                    ],
                )
            )
            assert pilot.result["status"] == "LIVE_SMOKE_BLOCKED_SOURCE_NOT_APPROVED"
            assert not (
                await f.db.scalars(select(CollectorJob).where(CollectorJob.user_id == f.uid))
            ).all()
            with pytest.raises(AppError) as denied:
                await ValidationRecords(f.db, f.oid).owned(pilot.id)
            assert denied.value.code == "VALIDATION_RECORD_NOT_FOUND"
            collection = CollectionInput(
                source_slug="MANUAL_CSV",
                kind="COVERAGE",
                instrument_ids=[f.ids[0]],
                start="2024-01-01",
                end="2024-01-05",
            )
            a = await BackfillJobService(f.db, f.user).start(collection)
            b = await BackfillJobService(f.db, f.other).start(collection)
            assert a.id != b.id and b.user_id == f.oid
            await BackfillJobService(f.db, f.user).control(a.id, "cancel")
            await BackfillJobService(f.db, f.other).control(b.id, "cancel")
            rid = pilot.id
            with pytest.raises(DBAPIError, match="PIT versions are immutable"):
                await f.db.execute(
                    text("UPDATE validation_records SET result='{}' WHERE id=:id"), {"id": rid}
                )
            await f.db.rollback()
            assert (await ValidationRecords(f.db, f.uid).owned(rid)).result[
                "status"
            ] == "LIVE_SMOKE_BLOCKED_SOURCE_NOT_APPROVED"
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=create_app()), base_url="http://testserver"
            ) as client:
                assert (await client.get("/api/v1/validation/overview")).status_code == 401
                assert (await client.get("/api/v1/validation/forward")).status_code == 401

    asyncio.run(run())


@pytest.mark.integration
def test_pr2_protocol_precedes_evaluation_and_never_queues_synthetic_data(monkeypatch):
    async def run():
        async with fixture(monkeypatch) as f:
            service = ValidationExperimentService(f.db, f.user)
            body = ExperimentInput.model_validate(protocol(f.datasets))
            record = await service.register(body)
            assert record.result["archive_kind"] == "RETROSPECTIVE_PIT_EXPERIMENT"
            assert record.result["promotion_rules"]["minimum_oos_signal_dates"] == 600
            blocked = await service.queue(record.id, 0)
            assert blocked.result["status"] == "BLOCKED_BY_REAL_DATA"
            assert not (
                await f.db.scalars(select(MLTrainingRun).where(MLTrainingRun.user_id == f.uid))
            ).all()
            evaluation = await service.evaluate(record.id)
            assert evaluation.result["status"] == "BLOCKED_BY_REAL_DATA"
            assert all(
                r["status"] == "NOT_RUN" and r["metrics"] is None
                for r in evaluation.result["comparisons"]
            )
            with pytest.raises(AppError) as exposed:
                await service.register(body)
            assert exposed.value.code == "OOS_ALREADY_RESERVED"
            original = await f.db.get(DatasetVersion, f.datasets[0])
            config = {**original.configuration, "end": "2024-01-06"}
            alias = DatasetVersion(
                user_id=f.uid,
                universe_id=f.universe_id,
                configuration=config,
                manifest=original.manifest,
                rows=[],
                quality=original.quality,
                content_hash=digest(
                    {
                        "configuration": config,
                        "manifest": original.manifest,
                        "rows": [],
                        "quality": original.quality,
                    }
                ),
            )
            f.db.add(alias)
            await f.db.commit()
            revised = body.model_dump(mode="json")
            for candidate in revised["candidates"]:
                if candidate["horizon"] == 30:
                    candidate["dataset_id"] = str(alias.id)
            with pytest.raises(AppError) as version_bypass:
                await service.register(ExperimentInput.model_validate(revised))
            assert version_bypass.value.code == "OOS_ALREADY_RESERVED"

    asyncio.run(run())


@pytest.mark.integration
def test_pr2_strategy_cannot_turn_synthetic_origin_into_real_metrics(monkeypatch):
    from app.schemas.recommendations import StrategyBacktestInput
    from app.services.validation_audit import validation_checkpoint

    async def run():
        async with fixture(monkeypatch) as f:
            result = await ValidationExperimentService(f.db, f.user).strategy(
                StrategyBacktestInput(
                    dataset_id=f.datasets[0],
                    portfolio_id=f.portfolio_id,
                    recommendation_ids=[uuid4()],
                )
            )
            assert result.result["status"] == "BLOCKED_BY_REAL_DATA"
            assert result.result["metrics"] is None
            before = await validation_checkpoint(f.db)
            assert before == await validation_checkpoint(f.db)
            assert before["records"] >= 1
            with pytest.raises(AppError) as private:
                await ValidationRecords(f.db, f.oid).owned(result.id)
            assert private.value.status_code == 404

    asyncio.run(run())


@pytest.mark.integration
def test_pr2_original_attestation_preserves_privacy_and_synthetic_identity(monkeypatch):
    from app.models import DataSource
    from app.schemas.validation import RawEvidenceInput

    async def run():
        async with fixture(monkeypatch) as f:
            source = await f.db.scalar(select(DataSource).where(DataSource.slug == "MANUAL_CSV"))
            raw = SimpleNamespace(
                id=uuid4(),
                source_id=source.id,
                request_metadata={"user_id": str(f.oid)},
                sha256="a" * 64,
                received_at=datetime.now(UTC),
                http_status=None,
                requested_at=None,
            )
            monkeypatch.setattr(
                "app.services.raw_ingestion.RawIngestionService.get", AsyncMock(return_value=raw)
            )
            original = AsyncMock(return_value=b"SYNTHETIC test original")
            monkeypatch.setattr(
                "app.services.raw_ingestion.RawIngestionService.get_verified", original
            )
            body = RawEvidenceInput(
                raw_ids=[raw.id],
                classification="REAL_MANUAL",
                provenance_reference="Explicit synthetic fixture, never production evidence.",
                rights_reference="Technical test permission, not a financial data license.",
            )
            service = RealDataPilotService(f.db, f.user)
            with pytest.raises(AppError) as private:
                await service.evidence(body)
            assert private.value.status_code == 404
            original.assert_not_awaited()
            raw.request_metadata = {"user_id": str(f.uid), "filename": "SYNTHETIC.csv"}
            with pytest.raises(AppError) as synthetic:
                await service.evidence(body)
            assert synthetic.value.code == "SYNTHETIC_EVIDENCE_FORBIDDEN"
            result = await service.evidence(body.model_copy(update={"classification": "SYNTHETIC"}))
            assert result.result["originals"][0]["sha256"] == raw.sha256
            assert result.result["public_availability"] == "UNCHANGED_REQUIRES_P6_EVIDENCE"
            assert source.gate_status == "APPROVED"

    asyncio.run(run())


@pytest.mark.integration
def test_pr2_forward_abstention_maturity_outcomes_and_restart_dedup(monkeypatch):
    async def run():
        async with fixture(monkeypatch) as f:
            models = []
            for kind, target in (("LOGISTIC", "classification"), ("LINEAR", "excess_return")):
                job = MLTrainingRun(
                    user_id=f.uid,
                    dataset_id=f.datasets[0],
                    configuration={"request": candidate(f.datasets[0], kind, target)},
                    status="COMPLETED",
                    progress=100,
                    current_stage="SYNTHETIC_NO_FITTED_MODEL",
                )
                f.db.add(job)
                await f.db.flush()
                model = MLModelVersion(
                    user_id=f.uid,
                    training_run_id=job.id,
                    dataset_id=f.datasets[0],
                    model_type=kind,
                    target_type=target,
                    horizon=30,
                    content_hash="0" * 64,
                    configuration=job.configuration,
                    evaluation={
                        "promotion_evidence": {
                            "synthetic_evidence": True,
                            "production_data_eligible": False,
                        }
                    },
                    artifact_key="SYNTHETIC_NOT_LOADABLE",
                    artifact_hash="0" * 64,
                )
                f.db.add(model)
                await f.db.flush()
                f.db.add(
                    ModelPromotionReview(
                        model_id=model.id,
                        reviewer_id=f.uid,
                        status="SHADOW",
                        evidence={"SYNTHETIC": True},
                    )
                )
                models.append(model.id)
            await f.db.commit()
            policy = await ForwardValidationService(f.db, f.user).register(
                ForwardInput(
                    classifier_id=models[0],
                    regressor_id=models[1],
                    instrument_ids=[f.ids[0]],
                    source_policy=[{"source_slug": "MANUAL_CSV", "use": "manual_upload"}],
                )
            )
            first = await ForwardValidationService(f.db, f.user).run(policy.id)
            second = await ForwardValidationService(f.db, f.user).run(policy.id)
            assert first.result["predictions"] == second.result["predictions"]
            from app.jobs.validation import dispatch

            with monkeypatch.context() as schedule_patch:
                schedule_patch.setattr(get_settings(), "forward_shadow_enabled", True)
                scheduled_run, scheduled_outcomes = AsyncMock(), AsyncMock()
                schedule_patch.setattr(ForwardValidationService, "run", scheduled_run)
                schedule_patch.setattr(ForwardValidationService, "outcomes", scheduled_outcomes)
                assert (await dispatch())["policies"] == 0
                await ForwardValidationService(f.db, f.user).scheduling(policy.id, True)
                assert (await dispatch())["policies"] == 1
                scheduled_run.assert_awaited_once()
                await ForwardValidationService(f.db, f.user).scheduling(policy.id, False)
                assert (await ForwardValidationService(f.db, f.user).policies())[0][
                    "enabled"
                ] is False
                assert (await dispatch())["policies"] == 0
                assert scheduled_run.await_count == 1
            assert first.result["predictions"][0]["status"] == "ABSTAINED"
            assert first.result["predictions"][0]["reason"] == "REAL_SHADOW_EVIDENCE_REQUIRED"
            report = await ForwardValidationService(f.db, f.user).report()
            assert report["groups"][0]["abstentions"] == 1
            assert report["groups"][0]["metrics"] is None
            instrument = await f.db.get(Instrument, f.ids[0])
            instrument.exchange = "NYSE"
            now = datetime.now(UTC)
            pred = Prediction(
                user_id=f.uid,
                instrument_id=f.ids[0],
                horizon=30,
                generated_at=now,
                information_cutoff_at=now,
                result={
                    "archive_kind": "FORWARD_ARCHIVED_SHADOW",
                    "confidence_status": "EXPERIMENTAL_SHADOW",
                    "SYNTHETIC_TEST_ONLY": True,
                    "forward_source_policy": [
                        {"source_slug": "MANUAL_CSV", "use": "manual_upload"}
                    ],
                    "signal_day": now.date().isoformat(),
                    "target_configuration": (
                        await f.db.get(DatasetVersion, f.datasets[0])
                    ).configuration,
                    "probability_outperform": 0.7,
                    "expected_excess_return": 0.02,
                },
            )
            f.db.add(pred)
            await f.db.commit()
            pid = pred.id
            assert await PredictionService(f.db).outcome(pid, f.uid) is None
            target = {
                "status": "AVAILABLE",
                "horizon_sessions": 30,
                "label_available_at": now.isoformat(),
                "instrument_return": "-.02",
                "benchmark_return": "0.01",
                "excess_return": "-.03",
                "classification": 0,
            }
            monkeypatch.setattr(
                "app.services.pit_datasets.DatasetBuilder.target", AsyncMock(return_value=target)
            )
            outcome = await PredictionService(f.db).outcome(pid, f.uid)
            assert outcome.result["correct"] is False
            assert (await PredictionService(f.db).outcome(pid, f.uid)).id == outcome.id
            changed = {**target, "excess_return": "-.04"}
            monkeypatch.setattr(
                "app.services.pit_datasets.DatasetBuilder.target", AsyncMock(return_value=changed)
            )
            correction = await PredictionService(f.db).outcome(pid, f.uid)
            assert correction.replaces_id == outcome.id
            assert (await f.db.get(Prediction, pid)).result["probability_outperform"] == 0.7
            with pytest.raises(DBAPIError, match="immutable"):
                await f.db.execute(
                    text("UPDATE prediction_outcomes SET result='{}' WHERE id=:id"),
                    {"id": correction.id},
                )

    asyncio.run(run())
