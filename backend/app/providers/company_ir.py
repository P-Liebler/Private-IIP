"""Explicit report contracts. No universal HTML/PDF financial inference."""

from __future__ import annotations

import asyncio
import csv
import ipaddress
import socket
from datetime import UTC, datetime
from io import StringIO
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.providers.http import fetch_response
from app.schemas.research import FactInput
from app.services.fundamentals import FundamentalService
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService


class ReportContract(BaseModel):
    instrument_id: UUID
    source_slug: str = "COMPANY_IR"
    url: str
    approved_host: str
    parser_version: str = "company-ir-explicit-csv-v1"
    mapping: dict[str, str] = Field(default_factory=dict)
    accounting_basis: Literal["IFRS", "SWISS_GAAP_FER", "US_GAAP", "UNVERIFIED"] = "UNVERIFIED"
    document_reference: str = Field(default="", max_length=300)
    reviewed: bool = False


async def validate_public_endpoint(url: str, approved_host: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != approved_host
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 443}
        or parsed.query
        or parsed.fragment
    ):
        raise AppError(422, "REPORT_URL_INVALID", "Exact approved public HTTPS report required")
    addresses = await asyncio.to_thread(
        socket.getaddrinfo, approved_host, 443, type=socket.SOCK_STREAM
    )
    if not addresses or any(not ipaddress.ip_address(entry[4][0]).is_global for entry in addresses):
        raise AppError(422, "REPORT_URL_INVALID", "Nonpublic endpoint is not allowed")
    return parsed.path


def parse_report_csv(data: bytes, contract: ReportContract) -> list[FactInput]:
    reader = csv.DictReader(StringIO(data.decode("utf-8-sig")))
    rows: list[FactInput] = []
    for line, original in enumerate(reader, 2):
        if line > 10001:
            raise ValueError("Too many report rows")
        values = {
            contract.mapping.get(k, k): v for k, v in original.items() if k and v not in (None, "")
        }
        if values.get("instrument_id") not in {None, str(contract.instrument_id)}:
            raise ValueError("Report identity mismatch")
        values["instrument_id"] = str(contract.instrument_id)
        if contract.accounting_basis != "UNVERIFIED":
            values["availability_evidence"] = (
                f"{contract.accounting_basis}; {contract.document_reference}; "
                + str(values.get("availability_evidence", ""))
            )
        rows.append(FactInput.model_validate(values))
    if not rows:
        raise ValueError("Empty financial report")
    return rows


class CompanyIRCollector:
    def __init__(
        self,
        db: AsyncSession,
        raw: RawIngestionService | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.db, self.raw, self.client = db, raw or RawIngestionService(db), client

    async def collect(self, contract: ReportContract) -> dict[str, int]:
        source = await SourceService(self.db).get(contract.source_slug)
        SourceGate.require_enabled(source, "fundamentals")
        if (
            not contract.reviewed
            or contract.accounting_basis == "UNVERIFIED"
            or not contract.document_reference
        ):
            raise AppError(
                409,
                "REPORT_CONTRACT_REVIEW_REQUIRED",
                "Accounting basis and company-specific report contract require review",
            )
        # Scope records the exact host. Caller-supplied approved_host cannot confer rights.
        if f"host={contract.approved_host}" not in (source.scope or "").split():
            raise AppError(403, "SOURCE_SCOPE_MISMATCH", "Report host not approved")
        await validate_public_endpoint(contract.url, contract.approved_host)
        raw = await fetch_response(
            self.db,
            self.raw,
            source,
            use="fundamentals",
            url=contract.url,
            allowed_host=contract.approved_host,
            resource="company_ir",
            client=self.client,
            instrument_id=contract.instrument_id,
            content_types=("text/csv", "application/csv"),
            metadata={"parser_version": contract.parser_version},
        )
        try:
            facts = parse_report_csv(await self.raw.get_verified(raw.id), contract)
            result = await FundamentalService(self.db, self.raw).persist(
                facts, raw, parser=contract.parser_version
            )
            source.last_success = datetime.now(UTC)
            await self.db.commit()
            return result
        except (ValueError, UnicodeDecodeError):
            await self.db.rollback()
            raise AppError(
                422, "REPORT_INVALID", "Report failed explicit mapping/validation"
            ) from None
