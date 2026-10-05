from __future__ import annotations

import json
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
    ) -> None:
        self.db = db
        self.client = client
        self.raw_service = raw_service or RawIngestionService(db)

    async def map_identifier(
        self,
        *,
        kind: str,
        value: str,
        exchange: str | None = None,
    ) -> MappingResult:
        if kind not in _ID_TYPES:
            raise AppError(422, "INVALID_IDENTIFIER", "Unsupported identifier type")
        try:
            normalized = normalize_identifier(kind, value)
        except ValueError as error:
            raise AppError(422, "INVALID_IDENTIFIER", str(error)) from error
        source = await SourceService(self.db).get("OPENFIGI")
        SourceGate.require_enabled(source, "mapping")  # Must precede client use and HTTP.
        await check_provider_rate(source)
        body: dict[str, str] = {"idType": _ID_TYPES[kind], "idValue": normalized}
        if exchange:
            body["exchCode"] = exchange.strip().upper()
        settings = get_settings()
        headers = {"Content-Type": "application/json"}
        if settings.openfigi_api_key:
            headers["X-OPENFIGI-APIKEY"] = settings.openfigi_api_key.get_secret_value()
        requested_at = datetime.now(UTC)
        metadata: dict[str, str | int] = {
            "endpoint": "/v3/mapping",
            "method": "POST",
            "identifier_type": kind,
            "identifier_value": normalized,
        }
        own_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=10.0)
        try:
            try:
                response = await client.post(
                    f"{settings.openfigi_base_url.rstrip('/')}/v3/mapping",
                    json=[body],
                    headers=headers,
                )
            except httpx.TimeoutException as error:
                await self.raw_service.record_failure(
                    source_id=source.id,
                    resource_type="openfigi_mapping",
                    requested_at=requested_at,
                    error_code="SOURCE_TIMEOUT",
                    request_metadata=metadata,
                )
                await self._failure(source)
                raise AppError(503, "SOURCE_TIMEOUT", "OpenFIGI request timed out") from error
            except httpx.RequestError as error:
                await self.raw_service.record_failure(
                    source_id=source.id,
                    resource_type="openfigi_mapping",
                    requested_at=requested_at,
                    error_code="SOURCE_UNAVAILABLE",
                    request_metadata=metadata,
                )
                await self._failure(source)
                raise AppError(503, "SOURCE_UNAVAILABLE", "OpenFIGI unavailable") from error
            raw = await self.raw_service.store(
                data=response.content,
                source_id=source.id,
                source_slug=source.slug,
                resource_type="openfigi_mapping",
                requested_at=requested_at,
                http_status=response.status_code,
                content_type=response.headers.get("Content-Type", "application/json"),
                request_metadata=metadata,
            )
            if response.status_code == 429:
                await self._failure(source)
                raise AppError(429, "SOURCE_RATE_LIMITED", "OpenFIGI rate limited the request")
            if response.status_code >= 500:
                await self._failure(source)
                raise AppError(503, "SOURCE_UNAVAILABLE", "OpenFIGI unavailable")
            if response.status_code != 200:
                await self._failure(source)
                raise AppError(
                    502, "SOURCE_RESPONSE_INVALID", "OpenFIGI rejected the mapping request"
                )
            try:
                result = parse_mapping_response(response.content, raw.id)
            except AppError:
                await self._failure(source)
                raise
            source.last_success = datetime.now(UTC)
            await self.db.commit()
            return result
        finally:
            if own_client:
                await client.aclose()

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
