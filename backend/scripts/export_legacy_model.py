"""Operator-only, read-only private export; redirect stdout to an ignored file.

Exports internal data-only JSON after hash/metadata checks, without executing it.
The host verifier then uses a separate exact image with --network none.
"""

import argparse
import asyncio
import base64
import json
from uuid import UUID

from sqlalchemy import select

from app.db.session import get_engine, get_session_factory
from app.models import User
from app.services.ml_registry import ModelRegistryService


async def export(model_id: UUID, username: str) -> dict[str, object]:
    async with get_session_factory()() as db:
        user = await db.scalar(select(User).where(User.username == username))
        if user is None:
            raise ValueError("LEGACY_OWNER_NOT_FOUND")
        service = ModelRegistryService(db)
        model = await service.owned(model_id, user.id)
        data, _ = await service.archived_bytes(model)
        return {
            "contract": "PR5_LEGACY_VERIFICATION_V1",
            "artifact_base64": base64.b64encode(data).decode(),
            "artifact_sha256": model.artifact_hash,
            "training_code": model.configuration["code"],
            "configuration": model.configuration["request"],
        }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", type=UUID, required=True)
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(await export(args.model_id, args.username)))
    finally:
        await get_engine().dispose()


if __name__ == "__main__":
    asyncio.run(main())
