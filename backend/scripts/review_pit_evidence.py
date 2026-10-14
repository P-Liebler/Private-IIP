"""Operator-only evidence review from a concrete UTF-8 JSON review file.

No network provider requests. Never rewrites prior financial observations.
"""

import argparse
import asyncio
import json
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.db.session import get_engine, get_session_factory
from app.models import ActionCoverageReview, CorporateActionVersion, RawIngestion, User
from app.services.pit_evidence import EvidenceService
from app.services.raw_ingestion import RawIngestionService


async def main(filename: str) -> None:
    value = json.loads(Path(filename).read_text(encoding="utf-8"))
    async with get_session_factory()() as db:
        reviewer = (await db.scalars(select(User).where(User.username == value["reviewer"]))).one()
        raw_id = UUID(value["raw_ingestion_id"])
        if value["entity_type"] == "action_coverage":
            await RawIngestionService(db).get_verified(raw_id)
            raw = await db.get(RawIngestion, raw_id)
            assert raw
            start = date.fromisoformat(value["start_date"])
            end = date.fromisoformat(value["end_date"])
            if end > datetime.now(UTC).date() or start > end:
                raise ValueError("Coverage cannot certify future sessions")
            ids = [str(UUID(i)) for i in value["action_version_ids"]]
            for i in ids:
                action = await db.get(CorporateActionVersion, UUID(i))
                if (
                    action is None
                    or action.instrument_id != UUID(value["instrument_id"])
                    or not start <= action.action_date <= end
                    or action.validation_status == "REJECTED"
                ):
                    raise ValueError("Coverage contains invalid action version")
            if len(value["rationale"].strip()) < 20 or not value.get("document_reference"):
                raise ValueError("Concrete coverage review and original evidence required")
            db.add(
                ActionCoverageReview(
                    instrument_id=UUID(value["instrument_id"]),
                    start_date=start,
                    end_date=end,
                    raw_ingestion_id=raw_id,
                    source_id=raw.source_id,
                    reviewer_id=reviewer.id,
                    action_version_ids=ids,
                    rationale=value["rationale"] + " Reference: " + value["document_reference"],
                )
            )
        else:
            await EvidenceService(db).review(
                value["entity_type"],
                UUID(value["entity_id"]),
                raw_id,
                reviewer.id,
                value["level"],
                value["rationale"],
                value["evidence"],
            )
        await db.commit()
    await get_engine().dispose()
    print("Append-only review stored; no historical observation rewritten")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    asyncio.run(main(parser.parse_args().file))
