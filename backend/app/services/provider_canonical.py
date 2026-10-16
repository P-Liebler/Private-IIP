"""Reuse existing canonical writers; cache validators advance only after parsing succeeds."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import DataQuarantine, DataSource, MacroObservation, ProviderSyncState, RawIngestion
from app.services.fundamentals import digest
from app.services.market_import import MarketImportService, ParsedRow


def counters() -> dict[str, int]:
    return dict.fromkeys(
        (
            "inserted",
            "corrected",
            "observed_only",
            "unchanged",
            "quarantined",
            "warning_rows",
            "rejected_rows",
            "new_versions",
        ),
        0,
    )


async def persist_fx(
    db: AsyncSession,
    raw: RawIngestion,
    source: DataSource,
    observations: list[dict[str, object]],
    parser: str,
) -> dict[str, Any]:
    result = counters()
    service = MarketImportService(db, parser_version=parser)
    await db.execute(text("LOCK TABLE fx_rates IN SHARE ROW EXCLUSIVE MODE"))
    for line, item in enumerate(observations, 2):
        try:
            await service._fx(
                ParsedRow(line, {}, item, None, [], []),
                raw.id,
                source.id,
                source.priority,
                raw.received_at,
                "REJECT",
                result,
            )
        except AppError as error:
            if error.code != "FX_CONFLICT_REVIEW":
                raise
            db.add(
                DataQuarantine(
                    raw_ingestion_id=raw.id,
                    source_id=source.id,
                    row_number=line,
                    data_type="fx",
                    record_key=f"{item['base_currency']}:{item['quote_currency']}:{item['rate_date']}",
                    reason="FX_CONFLICT_REVIEW",
                    severity="REVIEW",
                    row_data={str(k): str(v) for k, v in item.items()},
                )
            )
            result["quarantined"] += 1
    # Exact response parser is recorded on the raw request as well as the sync state.
    source.last_success = datetime.now(UTC)
    await db.commit()
    return {
        "status": "PARTIAL" if result["quarantined"] else "SUCCESS",
        "observations": len(observations),
        "actual_range": [
            min(str(row["rate_date"]) for row in observations),
            max(str(row["rate_date"]) for row in observations),
        ]
        if observations
        else None,
        "raw_ingestion_id": str(raw.id),
        "parser_version": parser,
        **result,
    }


async def persist_macro(
    db: AsyncSession, raw: RawIngestion, observations: list[dict[str, Any]], parser: str
) -> dict[str, Any]:
    await db.execute(text("LOCK TABLE macro_observation_versions IN SHARE ROW EXCLUSIVE MODE"))
    count = 0
    quarantined = 0
    ids: list[str] = []
    for item in observations:
        previous = (
            await db.scalars(
                select(MacroObservation)
                .where(
                    MacroObservation.series == item["series"],
                    MacroObservation.observation_date == item["observation_date"],
                )
                .order_by(MacroObservation.observed_at.desc(), MacroObservation.id.desc())
                .limit(1)
            )
        ).first()
        if previous and previous.source_id != raw.source_id:
            db.add(
                DataQuarantine(
                    raw_ingestion_id=raw.id,
                    source_id=raw.source_id,
                    row_number=len(ids) + quarantined + 1,
                    data_type="macro",
                    record_key=f"{item['series']}:{item['observation_date']}",
                    reason="MACRO_CONFLICT_REVIEW",
                    severity="REVIEW",
                    row_data={str(k): str(v) for k, v in item.items()},
                )
            )
            quarantined += 1
            continue
        if previous and previous.value == str(item["value"]) and previous.unit == item["unit"]:
            ids.append(str(previous.id))
            continue
        row = MacroObservation(
            **item,
            observed_at=raw.received_at,
            source_id=raw.source_id,
            raw_ingestion_id=raw.id,
            row_key=digest((item["series"], item["observation_date"])),
            replaces_id=previous.id if previous else None,
        )
        db.add(row)
        await db.flush()
        ids.append(str(row.id))
        count += 1
    await db.commit()
    return {
        "status": "PARTIAL" if quarantined else "SUCCESS",
        "quarantined": quarantined,
        "observations": len(observations),
        "actual_range": [
            str(min(row["observation_date"] for row in observations)),
            str(max(row["observation_date"] for row in observations)),
        ]
        if observations
        else None,
        "raw_ingestion_id": str(raw.id),
        "inserted": count,
        "canonical_ids": ids,
        "parser_version": parser,
    }


async def sync_state(db: AsyncSession, source: DataSource, key: str) -> ProviderSyncState | None:
    return await db.get(ProviderSyncState, (source.id, key))


def conditional_headers(state: ProviderSyncState | None) -> dict[str, str]:
    if state and state.etag:
        return {"If-None-Match": state.etag}
    if state and state.last_modified:
        return {"If-Modified-Since": state.last_modified}
    return {}


async def save_sync(
    db: AsyncSession,
    source: DataSource,
    key: str,
    raw: RawIngestion,
    parser: str,
    result: dict[str, Any],
) -> None:
    state = await sync_state(db, source, key)
    if state is None:
        state = ProviderSyncState(source_id=source.id, request_key=key)
        db.add(state)
    state.raw_ingestion_id, state.content_hash = raw.id, raw.sha256 or ""
    state.parser_version, state.result = parser, result
    state.etag = str(raw.request_metadata["etag"]) if raw.request_metadata.get("etag") else None
    state.last_modified = (
        str(raw.request_metadata["last_modified"])
        if raw.request_metadata.get("last_modified")
        else None
    )
    state.last_success_at = datetime.now(UTC)
    source.last_success = state.last_success_at
    await db.commit()


async def no_new_data(
    db: AsyncSession, source: DataSource, state: ProviderSyncState | None, raw: RawIngestion
) -> dict[str, Any]:
    if raw.http_status == 304 and state is None:
        raise AppError(502, "SOURCE_RESPONSE_INVALID", "304 requires a verified cached response")
    source.last_success = datetime.now(UTC)
    if state:
        state.last_success_at = source.last_success
    # Keep the last parsed response and canonical observation times intact.
    await db.commit()
    return {"status": "NO_NEW_DATA", "raw_ingestion_id": str(raw.id)}
