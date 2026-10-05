from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Instrument, InstrumentIdentifier
from app.services.audit import audit_service


def normalize_identifier(kind: str, value: str) -> str:
    normalized = value.strip().upper()
    if kind == "ISIN":
        normalized = normalized.replace(" ", "")
        if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", normalized):
            raise ValueError("Invalid ISIN format")
    elif kind == "FIGI":
        if not re.fullmatch(r"[A-Z0-9]{12}", normalized):
            raise ValueError("Invalid FIGI format")
    elif kind == "TICKER":
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9.\-]{0,39}", normalized):
            raise ValueError("Invalid ticker format")
    else:
        raise ValueError("Unsupported identifier type")
    return normalized


def market_key(kind: str, *, mic: str | None, exchange: str | None) -> str:
    return (mic or exchange or "").strip().upper() if kind == "TICKER" else ""


@dataclass(frozen=True)
class SearchHit:
    instrument: Instrument
    match_type: str
    resolution_status: str
    matched_value: str
    current: bool


class InstrumentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, instrument_id: UUID) -> tuple[Instrument, list[InstrumentIdentifier]]:
        instrument = await self.db.get(Instrument, instrument_id)
        if instrument is None:
            raise AppError(404, "INSTRUMENT_NOT_FOUND", "Instrument not found")
        identifiers = list(
            (
                await self.db.scalars(
                    select(InstrumentIdentifier)
                    .where(InstrumentIdentifier.instrument_id == instrument_id)
                    .order_by(InstrumentIdentifier.observed_at, InstrumentIdentifier.created_at)
                )
            ).all()
        )
        return instrument, identifiers

    async def create(
        self,
        *,
        name: str,
        asset_type: str,
        currency: str,
        ticker: str | None = None,
        isin: str | None = None,
        figi: str | None = None,
        exchange: str | None = None,
        mic: str | None = None,
        country: str | None = None,
        listed_at: date | None = None,
        actor_user_id: UUID,
    ) -> Instrument:
        if not name.strip() or asset_type not in {"STOCK", "ETF"}:
            raise ValueError("Invalid instrument name or asset type")
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError("Invalid instrument currency")
        normalized = {
            "TICKER": normalize_identifier("TICKER", ticker) if ticker else None,
            "ISIN": normalize_identifier("ISIN", isin) if isin else None,
            "FIGI": normalize_identifier("FIGI", figi) if figi else None,
        }
        instrument = Instrument(
            id=uuid4(),
            name=name.strip(),
            asset_type=asset_type,
            currency=currency,
            exchange=exchange.strip().upper() if exchange else None,
            mic=mic.strip().upper() if mic else None,
            country=country.strip().upper() if country else None,
            listed_at=listed_at,
            active=True,
        )
        self.db.add(instrument)
        try:
            await self.db.flush()
            for kind, value in normalized.items():
                if value:
                    await self._set_identifier(
                        instrument,
                        kind,
                        value,
                        valid_from=listed_at or datetime.now(UTC).date(),
                        source_id=None,
                        raw_ingestion_id=None,
                        actor_user_id=actor_user_id,
                    )
            audit_service.record(
                self.db,
                event="instrument.created",
                resource="instrument",
                resource_id=str(instrument.id),
                actor_user_id=actor_user_id,
                metadata={"asset_type": asset_type, "origin": "manual"},
            )
            await self.db.commit()
        except IntegrityError as error:
            await self.db.rollback()
            raise AppError(
                409, "IDENTIFIER_CONFLICT", "Identifier conflicts with another instrument"
            ) from error
        except Exception:
            await self.db.rollback()
            raise
        return instrument

    async def update(
        self,
        instrument_id: UUID,
        changes: dict[str, str | bool | date | None],
        *,
        actor_user_id: UUID,
    ) -> Instrument:
        instrument = (
            await self.db.scalars(
                select(Instrument).where(Instrument.id == instrument_id).with_for_update()
            )
        ).one_or_none()
        if instrument is None:
            raise AppError(404, "INSTRUMENT_NOT_FOUND", "Instrument not found")
        if not changes:
            raise AppError(422, "INVALID_INSTRUMENT", "No changes supplied")
        if "name" in changes and (
            not isinstance(changes["name"], str) or not changes["name"].strip()
        ):
            raise AppError(422, "INVALID_INSTRUMENT", "Instrument name is required")
        next_active = changes.get("active", instrument.active)
        next_delisted = changes.get("delisted_at", instrument.delisted_at)
        if next_delisted is not None and next_active:
            raise AppError(422, "INVALID_INSTRUMENT", "Delisted instrument cannot be active")
        if (
            isinstance(next_delisted, date)
            and instrument.listed_at
            and next_delisted < instrument.listed_at
        ):
            raise AppError(422, "INVALID_INSTRUMENT", "Delisting precedes listing")
        for field, value in changes.items():
            if field not in {"name", "active", "delisted_at", "sector", "industry"}:
                raise AppError(422, "INVALID_INSTRUMENT", "Unsupported instrument field")
            setattr(instrument, field, value.strip() if isinstance(value, str) else value)
        audit_service.record(
            self.db,
            event="instrument.updated",
            resource="instrument",
            resource_id=str(instrument.id),
            actor_user_id=actor_user_id,
            metadata={"fields": ",".join(sorted(changes))},
        )
        await self.db.commit()
        return instrument

    async def set_identifier(
        self,
        instrument_id: UUID,
        kind: str,
        value: str,
        *,
        valid_from: date,
        source_id: UUID | None,
        raw_ingestion_id: UUID | None,
        actor_user_id: UUID,
    ) -> InstrumentIdentifier:
        instrument = (
            await self.db.scalars(
                select(Instrument).where(Instrument.id == instrument_id).with_for_update()
            )
        ).one_or_none()
        if instrument is None:
            raise AppError(404, "INSTRUMENT_NOT_FOUND", "Instrument not found")
        normalized = normalize_identifier(kind, value)
        try:
            result = await self._set_identifier(
                instrument,
                kind,
                normalized,
                valid_from=valid_from,
                source_id=source_id,
                raw_ingestion_id=raw_ingestion_id,
                actor_user_id=actor_user_id,
            )
            await self.db.commit()
        except IntegrityError as error:
            await self.db.rollback()
            raise AppError(
                409, "IDENTIFIER_CONFLICT", "Identifier conflicts with another instrument"
            ) from error
        except Exception:
            await self.db.rollback()
            raise
        return result

    async def _set_identifier(
        self,
        instrument: Instrument,
        kind: str,
        value: str,
        *,
        valid_from: date,
        source_id: UUID | None,
        raw_ingestion_id: UUID | None,
        actor_user_id: UUID,
    ) -> InstrumentIdentifier:
        key = market_key(kind, mic=instrument.mic, exchange=instrument.exchange)
        current = (
            await self.db.scalars(
                select(InstrumentIdentifier)
                .where(
                    InstrumentIdentifier.instrument_id == instrument.id,
                    InstrumentIdentifier.type == kind,
                    InstrumentIdentifier.valid_to.is_(None),
                )
                .with_for_update()
            )
        ).one_or_none()
        if current is not None:
            if current.value == value and current.market_key == key:
                return current
            if valid_from <= current.valid_from:
                raise AppError(
                    409,
                    "IDENTIFIER_DATE_CONFLICT",
                    "New identifier must start after current identifier",
                )
            current.valid_to = valid_from
            audit_service.record(
                self.db,
                event="instrument.identifier_closed",
                resource="instrument_identifier",
                resource_id=str(current.id),
                actor_user_id=actor_user_id,
                metadata={"type": kind, "value": current.value},
            )
        conflicts = (
            await self.db.scalars(
                select(InstrumentIdentifier).where(
                    InstrumentIdentifier.type == kind,
                    InstrumentIdentifier.value == value,
                    InstrumentIdentifier.market_key == key,
                    or_(
                        InstrumentIdentifier.valid_to.is_(None),
                        InstrumentIdentifier.valid_to > valid_from,
                    ),
                )
            )
        ).all()
        if conflicts:
            raise AppError(
                409, "IDENTIFIER_CONFLICT", "Identifier validity overlaps another record"
            )
        identifier = InstrumentIdentifier(
            id=uuid4(),
            instrument_id=instrument.id,
            type=kind,
            value=value,
            market_key=key,
            valid_from=valid_from,
            source_id=source_id,
            raw_ingestion_id=raw_ingestion_id,
            observed_at=datetime.now(UTC),
        )
        self.db.add(identifier)
        setattr(instrument, kind.lower(), value)
        audit_service.record(
            self.db,
            event="instrument.identifier_added",
            resource="instrument_identifier",
            resource_id=str(identifier.id),
            actor_user_id=actor_user_id,
            metadata={"type": kind, "value": value},
        )
        await self.db.flush()
        return identifier

    async def search(self, query: str, *, limit: int = 20) -> list[SearchHit]:
        term = query.strip()
        if not term:
            return []
        upper = term.upper()
        identifiers = (
            await self.db.execute(
                select(InstrumentIdentifier, Instrument)
                .join(Instrument, Instrument.id == InstrumentIdentifier.instrument_id)
                .where(InstrumentIdentifier.value == upper)
                .limit(limit + 1)
            )
        ).all()
        if identifiers:
            distinct: dict[UUID, tuple[InstrumentIdentifier, Instrument]] = {}
            for identifier, instrument in identifiers:
                distinct[instrument.id] = (identifier, instrument)
            status = "UNIQUE" if len(distinct) == 1 and len(identifiers) <= limit else "AMBIGUOUS"
            return [
                SearchHit(
                    instrument=instrument,
                    match_type="EXACT_TICKER"
                    if identifier.type == "TICKER"
                    else "EXACT_IDENTIFIER",
                    resolution_status=status,
                    matched_value=identifier.value,
                    current=identifier.valid_to is None,
                )
                for identifier, instrument in list(distinct.values())[:limit]
            ]
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        matches = list(
            (
                await self.db.scalars(
                    select(Instrument)
                    .where(Instrument.name.ilike(f"%{escaped}%", escape="\\"))
                    .order_by(Instrument.name)
                    .limit(limit)
                )
            ).all()
        )
        return [
            SearchHit(
                instrument=item,
                match_type="EXACT_NAME"
                if item.name.casefold() == term.casefold()
                else "FUZZY_NAME",
                resolution_status="UNIQUE"
                if len(matches) == 1 and item.name.casefold() == term.casefold()
                else "CANDIDATE",
                matched_value=item.name,
                current=True,
            )
            for item in matches
        ]
