"""Read-only audit of an existing owned dataset; never generates financial data."""

import argparse
import asyncio
import json
from uuid import UUID

from app.db.session import get_engine, get_session_factory
from app.services.ml_readiness import P7DataReadinessService
from app.services.pit_datasets import DatasetBuilder


async def audit(dataset_id: UUID) -> None:
    try:
        async with get_session_factory()() as db:
            from app.models import DatasetVersion

            dataset = await db.get(DatasetVersion, dataset_id)
            if dataset is None:
                raise ValueError("DATASET_NOT_FOUND")
            report = await P7DataReadinessService(db).report(
                dataset.id,
                dataset.user_id,
                ["momentum_20d", "volatility_20"],
                dataset.configuration["target_horizon"],
            )
            await DatasetBuilder(db).rebuild(dataset.id, dataset.user_id)
            print(json.dumps(report, indent=2))
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_id", type=UUID)
    args = parser.parse_args()
    asyncio.run(audit(args.dataset_id))
