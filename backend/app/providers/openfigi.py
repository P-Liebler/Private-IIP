from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import DataSource
from app.providers.contracts import MappingCandidate, MappingResult
from app.services.audit import audit_service
from app.services.instruments import InstrumentService, normalize_identifier
from app.services.provider_rate_limit import check_provider_rate
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService

_ID_TYPES = {"TICKER": "TICKER", "ISIN": "ID_ISIN", "FIGI": "ID_BB_GLOBAL"}


def parse_mapping_response(body: bytes, raw_ingestion_id: UUID | None = None) -> MappingResult:
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, ValueError) as error:
        raise AppError(502, "SOURCE_RESPONSE_INVALID", "Invalid OpenFIGI response") from error
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
        raise AppError(502, "SOURCE_RESPONSE_INVALID", "Invalid OpenFIGI response")
    entry = payload[0]
    if "error" in entry:
        raise AppError(502, "SOURCE_RESPONSE_INVALID", "OpenFIGI mapping returned an error")
    data = entry.get("data")
    if data is None and isinstance(entry.get("warning"), str):
        return MappingResult("NO_MATCH", (), raw_ingestion_id)
    if not isinstance(data, list):
        raise AppError(502, "SOURCE_RESPONSE_INVALID", "Invalid OpenFIGI response")
    candidates: list[MappingCandidate] = []
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("figi"), str):
            raise AppError(502, "SOURCE_RESPONSE_INVALID", "Invalid OpenFIGI candidate")
        try:
            figi = normalize_identifier("FIGI", item["figi"])
        except ValueError as error:
            raise AppError(502, "SOURCE_RESPONSE_INVALID", "Invalid OpenFIGI candidate") from error
        for field in ("ticker", "name", "exchCode", "securityType", "marketSector"):
            if item.get(field) is not None and not isinstance(item[field], str):
                raise AppError(502, "SOURCE_RESPONSE_INVALID", "Invalid OpenFIGI candidate")
        candidates.append(
            MappingCandidate(
                figi=figi,
                ticker=item.get("ticker"),
                name=item.get("name"),
                exch_code=item.get("exchCode"),
                security_type=item.get("securityType"),
                market_sector=item.get("marketSector"),
            )
        )
    status = (
        "NO_MATCH"
        if not candidates
        else "UNIQUE_CANDIDATE"
        if len(candidates) == 1
        else "AMBIGUOUS"
    )
    return MappingResult(status, tuple(candidates), raw_ingestion_id)


class OpenFigiProvider:
    def __init__(
        self,
        db: AsyncSession,
        *,
        client: httpx.AsyncClient | None = None,
        raw_service: RawIngestionService | None = None,
        limiter: Callable[[DataSource], Awaitable[None]] = check_provider_rate,
    ) -> None:
        self.db = db
        self.client = client
        self.raw_service = raw_service or RawIngestionService(db)
        self.limiter = limiter

    async def map_identifier(
        self,
        *,
        kind: str,
        value: str,
        exchange: str | None = None,
        mic: str | None = None,
        currency: str | None = None,
        include_unlisted: bool = False,
    ) -> MappingResult:
        if kind not in _ID_TYPES:
            raise AppError(422, "INVALID_IDENTIFIER", "Unsupported identifier type")
        try:
            normalized = normalize_identifier(kind, value)
        except ValueError as error:
            raise AppError(422, "INVALID_IDENTIFIER", str(error)) from error
        source = await SourceService(self.db).get("OPENFIGI")
        SourceGate.require_enabled(source, "mapping")  # Must precede client use and HTTP.
        body: dict[str, str | bool] = {"idType": _ID_TYPES[kind], "idValue": normalized}
        if exchange:
            body["exchCode"] = exchange.strip().upper()
        if mic and exchange:
            raise AppError(422, "MAPPING_FILTER_INVALID", "MIC and exchange are mutually exclusive")
        if mic:
            body["micCode"] = mic.strip().upper()
        if currency:
            body["currency"] = currency.strip().upper()
        if include_unlisted:
            body["includeUnlistedEquities"] = True
        settings = get_settings()
        if settings.openfigi_base_url != "https://api.openfigi.com":
            raise AppError(422, "SOURCE_ORIGIN_INVALID", "Official OpenFIGI origin required")
        headers = {"Content-Type": "application/json"}
        if settings.openfigi_api_key:
            headers["X-OPENFIGI-APIKEY"] = settings.openfigi_api_key.get_secret_value()
        metadata: dict[str, str | int] = {
            "endpoint": "/v3/mapping",
            "method": "POST",
            "identifier_type": kind,
            "identifier_value": normalized,
        }
        from app.providers.http import fetch_response

        raw = await fetch_response(
            self.db,
            self.raw_service,
            source,
            use="mapping",
            url="https://api.openfigi.com/v3/mapping",
            allowed_host="api.openfigi.com",
            resource="openfigi_mapping",
            client=self.client,
            method="POST",
            json_body=[body],
            limiter=self.limiter,
            headers=headers,
            metadata=metadata,
        )
        try:
            result = parse_mapping_response(await self.raw_service.get_verified(raw.id), raw.id)
        except AppError:
            await self._failure(source)
            raise
        source.last_success = datetime.now(UTC)
        await self.db.commit()
        return result

    async def _failure(self, source: DataSource) -> None:
        source.last_failure = datetime.now(UTC)
        source.failure_count += 1
        await self.db.commit()


class MappingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def accept(
        self,
        *,
        instrument_id: UUID,
        raw_ingestion_id: UUID,
        figi: str,
        actor_user_id: UUID,
    ) -> None:
        source = await SourceService(self.db).get("OPENFIGI")
        SourceGate.require_enabled(source, "mapping")
        raw_service = RawIngestionService(self.db)
        raw = await raw_service.get(raw_ingestion_id)
        if (
            raw.source_id != source.id
            or raw.resource_type != "openfigi_mapping"
            or raw.http_status != 200
        ):
            raise AppError(409, "MAPPING_PROVENANCE_INVALID", "Mapping source is invalid")
        result = parse_mapping_response(await raw_service.get_verified(raw_ingestion_id), raw.id)
        try:
            normalized = normalize_identifier("FIGI", figi)
        except ValueError as error:
            raise AppError(422, "INVALID_IDENTIFIER", str(error)) from error
        if normalized not in {candidate.figi for candidate in result.candidates}:
            raise AppError(
                409, "MAPPING_CANDIDATE_INVALID", "Candidate is not in the stored response"
            )
        audit_service.record(
            self.db,
            event="mapping.accepted",
            resource="instrument",
            resource_id=str(instrument_id),
            actor_user_id=actor_user_id,
            metadata={"figi": normalized, "raw_ingestion_id": str(raw.id)},
        )
        await InstrumentService(self.db).set_identifier(
            instrument_id,
            "FIGI",
            normalized,
            valid_from=datetime.now(UTC).date(),
            source_id=source.id,
            raw_ingestion_id=raw.id,
            actor_user_id=actor_user_id,
        )
