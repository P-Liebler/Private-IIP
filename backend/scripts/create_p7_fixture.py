"""Explicit local ML-kernel simulation; NOT a real historic financial archive.

The simulation deliberately has no tradable market store. Cost/backtest and
production gates must fail even when statistical model fitting succeeds.
"""

import asyncio
import json
import os
from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.jobs.celery_app import celery_app
from app.ml.promotion import PROMOTION_RULES
from app.ml.training import TrainingInput
from app.models import (
    DatasetVersion,
    DataSource,
    FeatureSnapshot,
    Instrument,
    MLTrainingRun,
    UniverseDefinition,
    UniverseMembershipVersion,
    User,
)
from app.services.fundamentals import digest
from app.services.pit_datasets import code_manifest
from app.services.pit_features import json_value
from app.services.raw_ingestion import RawIngestionService


async def main() -> None:
    username = os.environ.get("E2E_USERNAME", "")
    if get_settings().app_env not in {"local", "test"} or not username.startswith("restore_"):
        raise RuntimeError("Explicit local disposable restore user required")
    # Reuse the declared unit simulation, never a production feature generator.
    from tests.unit.test_p7_training import synthetic_rows, window

    rows = synthetic_rows()
    try:
        async with get_session_factory()() as db:
            user = (await db.scalars(select(User).where(User.username == username))).one()
            suffix = uuid4().hex[:10]
            source = DataSource(
                name="SYNTHETIC P7 kernel test only",
                slug="TEST_P7_" + suffix.upper(),
                type="MANUAL",
                trust_level="D",
                priority=1,
                enabled=True,
                gate_status="APPROVED",
                allowed_uses=["synthetic_fixture"],
                checked_at=datetime.now(UTC),
                decision_by="explicit local test",
                decision_note="No external rights; synthetic statistical kernel fixture",
            )
            universe = UniverseDefinition(
                user_id=user.id,
                name="SYNTHETIC P7 kernel " + suffix,
                configuration={"synthetic": True},
            )
            instrument = Instrument(
                name="SYNTHETIC P7 kernel " + suffix,
                asset_type="STOCK",
                currency="USD",
                exchange="NYSE",
                country="US",
            )
            db.add_all([source, universe, instrument])
            await db.flush()
            for row in rows:
                row["instrument_id"] = str(instrument.id)
            raw = await RawIngestionService(db).store(
                data=json.dumps(
                    {
                        "SYNTHETIC": True,
                        "contract": "ML_KERNEL_SIMULATION_NO_TRADABLE_MARKET",
                        "observations": rows,
                    }
                ).encode(),
                source_id=source.id,
                source_slug=source.slug,
                resource_type="synthetic_p7_kernel",
                request_metadata={"user_id": str(user.id)},
            )
            membership = UniverseMembershipVersion(
                universe_id=universe.id,
                instrument_id=instrument.id,
                valid_from=date(2015, 1, 2),
                valid_to=date(2024, 12, 31),
                known_at=datetime.now(UTC),
                observed_at=datetime.now(UTC),
                source_id=source.id,
                raw_ingestion_id=raw.id,
                membership_status="LISTED",
                row_key=digest(instrument.id),
                version="synthetic-kernel-v1",
                evidence={"SYNTHETIC": True},
            )
            db.add(membership)
            await db.flush()
            await db.refresh(membership)
            feature_ids = []
            for row in rows:
                result = {
                    "features": row["features"],
                    "SYNTHETIC": True,
                    "raw_id": str(raw.id),
                    "clock_contract": "SIMULATED_KNOWLEDGE_NOT_REAL_OBSERVATION",
                    "as_of": row["information_cutoff_at"],
                }
                snapshot = FeatureSnapshot(
                    id=uuid4(),
                    instrument_id=instrument.id,
                    as_of=datetime.fromisoformat(row["information_cutoff_at"]),
                    information_cutoff_at=datetime.fromisoformat(row["information_cutoff_at"]),
                    feature_set_version="synthetic-kernel-v1",
                    result=result,
                    content_hash=digest(result),
                )
                db.add(snapshot)
                row["feature_snapshot_id"] = str(snapshot.id)
                feature_ids.append(str(snapshot.id))
            manifest = {
                "versions": {"membership": [str(membership.id)]},
                "version_hashes": {
                    "membership": {
                        str(membership.id): digest(
                            json_value(
                                {
                                    c.name: getattr(membership, c.name)
                                    for c in membership.__table__.columns
                                }
                            )
                        )
                    }
                },
                "feature_snapshot_ids": feature_ids,
                "coverage_ids": [],
                "market": {},
                "actions": {},
                "simulation_contract": "ML_KERNEL_SIMULATION_NO_TRADABLE_MARKET",
                **code_manifest(),
            }
            configuration = {
                "universe_id": str(universe.id),
                "benchmark_id": str(instrument.id),
                "start": "2015-01-02",
                "end": "2024-12-31",
                "base_currency": "USD",
                "target_horizon": 30,
                "availability_mode": "STRICT_PIT",
                "feature_set_version": "synthetic-kernel-v1",
                "data_context": "SYNTHETIC_SIMULATION_NOT_REAL_ARCHIVE",
            }
            quality = {
                "total_observations": len(rows),
                "survivorship_risk": False,
                "simulation_only": True,
            }
            dataset = DatasetVersion(
                user_id=user.id,
                universe_id=universe.id,
                configuration=configuration,
                manifest=manifest,
                rows=rows,
                quality=quality,
                content_hash=digest(
                    {
                        "configuration": configuration,
                        "manifest": manifest,
                        "rows": rows,
                        "quality": quality,
                    }
                ),
            )
            db.add(dataset)
            await db.flush()
            config = TrainingInput(
                dataset_id=dataset.id,
                model_type="LOGISTIC",
                target="classification",
                feature_names=["test_feature"],
                required_features=["test_feature"],
                folds=[window()],
            )
            job = MLTrainingRun(
                id=uuid4(),
                user_id=user.id,
                dataset_id=dataset.id,
                configuration={
                    "request": config.model_dump(mode="json"),
                    "code": code_manifest(),
                    "promotion_rules": PROMOTION_RULES,
                },
                status="QUEUED",
                current_stage="QUEUED",
                progress=0,
            )
            job.celery_task_id = str(job.id)
            db.add(job)
            await db.commit()
            celery_app.send_task(
                "ml.train", args=[str(job.id)], task_id=job.celery_task_id, queue="ml"
            )
            print(
                json.dumps(
                    {
                        "data_context": configuration["data_context"],
                        "job_id": str(job.id),
                        "dataset_id": str(dataset.id),
                        "raw_id": str(raw.id),
                        "instrument_id": str(instrument.id),
                        "production_data_eligible": False,
                        "financial_backtest_status": "UNAVAILABLE_BY_DESIGN",
                    }
                )
            )
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    asyncio.run(main())
