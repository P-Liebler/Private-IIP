import asyncio
import json
import secrets
from contextlib import redirect_stdout
from datetime import UTC, datetime
from io import StringIO
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError

from app.core.errors import AppError
from app.db.session import get_engine, get_session_factory
from app.main import create_app
from app.models import (
    ActionCoverageReview,
    AuditEvent,
    AvailabilityReview,
    BacktestRun,
    DatasetVersion,
    DataSource,
    FeatureSnapshot,
    Instrument,
    PITJob,
    PriceDailyVersion,
    RawIngestion,
    ResearchMetric,
    ResearchSnapshot,
    SessionRecord,
    UniverseDefinition,
    UniverseMembershipVersion,
    User,
    WalkForwardSplit,
)
from app.schemas.pit import BacktestInput, DatasetInput
from app.services.auth import AuthService
from app.services.pit_datasets import DatasetBuilder
from app.services.pit_features import FeatureSnapshotService
from app.services.research import ResearchService
from scripts.create_p6_fixture import main as create_fixture
from tests.integration.test_market_foundation import MemoryStorage


@pytest.mark.integration
def test_pinned_dataset_rebuild_identity_ownership_source_gate_and_immutability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        memory = MemoryStorage()
        monkeypatch.setattr("app.services.raw_ingestion.get_storage", lambda: memory)
        password = secrets.token_urlsafe(32)
        username = "restore_" + uuid4().hex[:12]
        async with get_session_factory()() as db:
            user = await AuthService(db).create_user(username, password)
            other = await AuthService(db).create_user("p6_" + uuid4().hex[:12], password)
            users = [user.id, other.id]
        monkeypatch.setenv("E2E_USERNAME", username)
        output = StringIO()
        with redirect_stdout(output):
            await create_fixture()
        fixture = json.loads(output.getvalue())
        source_id = UUID(fixture["source_id"])
        async with get_session_factory()() as db:
            ids = list(
                (
                    await db.scalars(
                        select(Instrument.id).where(
                            Instrument.name.like("SYNTHETIC P6%"),
                            Instrument.name.endswith(fixture["universe_name"].split()[-1]),
                        )
                    )
                ).all()
            )
            universe_ids = [UUID(fixture["universe_id"]), UUID(fixture["unverified_universe_id"])]
            config = DatasetInput(
                universe_id=universe_ids[0],
                benchmark_id=fixture["benchmark_id"],
                start=fixture["start"],
                end=fixture["end"],
                base_currency="USD",
            )
            try:
                builder = DatasetBuilder(db)
                dataset = await builder.build(config, users[0])
                await db.commit()
                dataset_id = dataset.id
                original_hash = dataset.content_hash
                assert (
                    dataset.quality["valid_observations"] == 4
                    and dataset.quality["excluded_observations"] == 0
                )
                again = await builder.build(config, users[0])
                assert again.id == dataset_id
                await db.commit()
                assert (await builder.rebuild(dataset_id, users[0]))[
                    "content_hash"
                ] == original_hash
                for cutoff in [
                    datetime(2024, 1, 3, 21, 30, tzinfo=UTC),
                    datetime(2024, 1, 4, 21, 30, tzinfo=UTC),
                ]:
                    snap = await FeatureSnapshotService(db).build(
                        UUID(fixture["instrument_id"]), cutoff, "STRICT_PIT"
                    )
                    for pid in snap.result["input_version_ids"]["prices"]:
                        price = await db.get(PriceDailyVersion, UUID(pid))
                        assert price and price.known_at <= cutoff
                await db.commit()
                first = await ResearchService(db).materialize(UUID(fixture["instrument_id"]))
                second = await ResearchService(db).materialize(UUID(fixture["instrument_id"]))
                assert first.id == second.id
                with pytest.raises(DBAPIError):
                    await db.execute(
                        update(DatasetVersion)
                        .where(DatasetVersion.id == dataset_id)
                        .values(content_hash="0" * 64)
                    )
                await db.rollback()
                dataset = await builder.owned(dataset_id, users[0])
                assert dataset.content_hash == original_hash
                original_get = db.get
                missing_id = dataset.manifest["versions"]["price"][0]

                async def missing(model: object, key: object, **kwargs: object) -> object:
                    if model is PriceDailyVersion and str(key) == missing_id:
                        return None
                    return await original_get(model, key, **kwargs)

                monkeypatch.setattr(db, "get", missing)
                with pytest.raises(AppError, match="Missing pinned"):
                    await builder.rebuild(dataset_id, users[0])
                monkeypatch.setattr(db, "get", original_get)
                await db.rollback()
                app = create_app()
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://test",
                    headers={"Origin": "http://localhost:3000"},
                ) as client:
                    assert (await client.get("/api/v1/universes")).status_code == 401
                    assert (
                        await client.post(
                            "/api/v1/auth/login", json={"username": username, "password": password}
                        )
                    ).status_code == 200
                    response = await client.post(
                        "/api/v1/backtests",
                        json=BacktestInput(
                            dataset_id=dataset_id,
                            initial_capital="1000",
                            commission="1",
                            spread_bps=0,
                            slippage_bps=0,
                        ).model_dump(mode="json"),
                    )
                    assert response.status_code == 200, response.text
                    result = response.json()
                    assert result["result"]["status"] == "STRICT_PIT_VALID"
                    assert result["result"]["metrics"]["Total Return"].startswith("0.0989")
                    assert (await client.get(f"/api/v1/pit/jobs/{result['job_id']}")).json()[
                        "progress"
                    ] == 100
                    blocked = await client.post(
                        f"/api/v1/universes/{universe_ids[0]}/imports/upload",
                        content=b"instrument_id,valid_from\n",
                        headers={"Content-Type": "text/csv"},
                    )
                    assert blocked.status_code == 403
                    metrics = await client.get("/internal/metrics")
                    assert (
                        "private_iip_backtest_total" in metrics.text
                        and "private_iip_db_ready 0" not in metrics.text
                    )
                    await client.post("/api/v1/auth/logout")
                    other_row = await db.get(User, users[1])
                    assert other_row
                    assert (
                        await client.post(
                            "/api/v1/auth/login",
                            json={"username": other_row.username, "password": password},
                        )
                    ).status_code == 200
                    for path in [
                        f"/universes/{universe_ids[0]}/membership",
                        f"/datasets/{dataset_id}",
                        f"/backtests/{result['id']}",
                        f"/pit/jobs/{result['job_id']}",
                    ]:
                        assert (await client.get("/api/v1" + path)).status_code == 404
            finally:
                await db.rollback()
                dataset_ids = select(DatasetVersion.id).where(DatasetVersion.user_id.in_(users))
                await db.execute(
                    delete(WalkForwardSplit).where(WalkForwardSplit.dataset_id.in_(dataset_ids))
                )
                for model in [BacktestRun, DatasetVersion, PITJob]:
                    await db.execute(delete(model).where(model.user_id.in_(users)))
                await db.execute(
                    delete(FeatureSnapshot).where(FeatureSnapshot.instrument_id.in_(ids))
                )
                await db.execute(
                    delete(ResearchMetric).where(
                        ResearchMetric.snapshot_id.in_(
                            select(ResearchSnapshot.id).where(
                                ResearchSnapshot.instrument_id.in_(ids)
                            )
                        )
                    )
                )
                await db.execute(
                    delete(ResearchSnapshot).where(ResearchSnapshot.instrument_id.in_(ids))
                )
                await db.execute(
                    delete(UniverseMembershipVersion).where(
                        UniverseMembershipVersion.universe_id.in_(universe_ids)
                    )
                )
                await db.execute(
                    delete(UniverseDefinition).where(UniverseDefinition.id.in_(universe_ids))
                )
                await db.execute(
                    delete(AvailabilityReview).where(AvailabilityReview.reviewer_id.in_(users))
                )
                await db.execute(
                    delete(ActionCoverageReview).where(ActionCoverageReview.instrument_id.in_(ids))
                )
                await db.execute(
                    delete(PriceDailyVersion).where(PriceDailyVersion.instrument_id.in_(ids))
                )
                await db.execute(delete(RawIngestion).where(RawIngestion.source_id == source_id))
                await db.execute(delete(Instrument).where(Instrument.id.in_(ids)))
                await db.execute(delete(DataSource).where(DataSource.id == source_id))
                await db.execute(delete(AuditEvent).where(AuditEvent.actor_user_id.in_(users)))
                await db.execute(delete(SessionRecord).where(SessionRecord.user_id.in_(users)))
                await db.execute(delete(User).where(User.id.in_(users)))
                await db.commit()
        await get_engine().dispose()

    async def run_with_disposal() -> None:
        try:
            await run()
        finally:
            await get_engine().dispose()

    asyncio.run(run_with_disposal())
