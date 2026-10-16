"""Official SEC JSON collector. No financial network access without rights and global rate gate."""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from typing import cast
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.valkey import make_valkey_client
from app.models import DataQuarantine, DataSource, Filing, Instrument, RawIngestion
from app.schemas.research import INSTANT_METRICS, FactInput
from app.services.fundamentals import FundamentalService
from app.services.provider_rate_limit import check_provider_rate
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService

# Server TIME plus sliding window avoids independent worker clocks and boundary bursts.
SEC_SCRIPT = """
local t = redis.call('TIME')
local now = tonumber(t[1])*1000000+tonumber(t[2])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now-1000000)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then return 0 end
redis.call('ZADD', KEYS[1], now, ARGV[2])
redis.call('EXPIRE', KEYS[1], 2)
return 1
"""


async def check_sec_rate(source: DataSource) -> None:
    from uuid import uuid4

    await check_provider_rate(source)
    client = make_valkey_client()
    try:
        admitted = await cast(
            Awaitable[int],
            client.eval(
                SEC_SCRIPT,
                1,
                "provider:sec:global",
                str(get_settings().sec_rate_limit),
                uuid4().hex,
            ),
        )
    except RedisError as error:
        raise AppError(503, "SOURCE_RATE_UNAVAILABLE", "SEC rate limiter unavailable") from error
    finally:
        await client.aclose()
    if not admitted:
        raise AppError(429, "SOURCE_RATE_LIMITED", "SEC global limit reached", retry_after=1)


TAGS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ),
    "gross_profit": ("GrossProfit",),
    "operating_income": ("OperatingIncomeLoss",),
    "net_income": ("NetIncomeLoss",),
    "eps_basic": ("EarningsPerShareBasic",),
    "eps_diluted": ("EarningsPerShareDiluted",),
    "cash": ("CashAndCashEquivalentsAtCarryingValue",),
    "total_assets": ("Assets",),
    "total_liabilities": ("Liabilities",),
    "total_equity": ("StockholdersEquity",),
    "total_debt": ("LongTermDebtCurrent", "LongTermDebtNoncurrent"),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",),
    "shares_outstanding": ("EntityCommonStockSharesOutstanding",),
    "current_assets": ("AssetsCurrent",),
    "current_liabilities": ("LiabilitiesCurrent",),
    "inventory": ("InventoryNet",),
    "income_tax": ("IncomeTaxExpenseBenefit",),
    "pretax_income": (
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    ),
}


def parse_submissions(data: bytes, cik: str) -> list[dict[str, object]]:
    document = json.loads(data)
    if str(document.get("cik", "")).zfill(10) != cik:
        raise ValueError("SEC CIK mismatch")
    recent = document["filings"]["recent"]
    count = len(recent["accessionNumber"])
    required = ("form", "filingDate", "reportDate", "acceptanceDateTime", "primaryDocument")
    if any(len(recent[key]) != count for key in required):
        raise ValueError("Corrupt SEC column arrays")
    rows: list[dict[str, object]] = []
    for index in range(count):
        form = recent["form"][index]
        if form not in {"10-K", "10-Q", "10-K/A", "10-Q/A"}:
            continue
        accession = recent["accessionNumber"][index]
        primary = recent["primaryDocument"][index]
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession) or not re.fullmatch(
            r"[A-Za-z0-9_.-]+", primary
        ):
            raise ValueError("Invalid filing path")
        accepted = datetime.fromisoformat(
            recent["acceptanceDateTime"][index].replace("Z", "+00:00")
        )
        if accepted.tzinfo is None:
            raise ValueError("Acceptance timestamp has no timezone")
        rows.append(
            {
                "accession_number": accession,
                "filing_type": form,
                "filing_date": date.fromisoformat(recent["filingDate"][index]),
                "accepted_at": accepted,
                "period_end": date.fromisoformat(recent["reportDate"][index]),
                "document_url": (
                    f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                    f"{accession.replace('-', '')}/{primary}"
                ),
            }
        )
    return rows


def parse_companyfacts(
    data: bytes, cik: str, instrument_id: UUID, filings: dict[str, Filing]
) -> tuple[list[FactInput], list[str]]:
    document = json.loads(data, parse_float=str)
    if str(document.get("cik", "")).zfill(10) != cik:
        raise ValueError("SEC CIK mismatch")
    taxonomies = document["facts"]
    inputs: list[FactInput] = []
    warnings: list[str] = []
    for metric, tags in TAGS.items():
        # Debt components are not a total-debt definition. Leave unavailable.
        if metric == "total_debt":
            continue
        candidates: dict[tuple[object, ...], list[FactInput]] = {}
        taxonomy = taxonomies.get("dei" if metric == "shares_outstanding" else "us-gaap", {})
        for tag in tags:
            for unit, observations in taxonomy.get(tag, {}).get("units", {}).items():
                for observation in observations:
                    filing = filings.get(observation.get("accn"))
                    if filing is None or observation.get("form") != filing.filing_type:
                        continue
                    try:
                        end = date.fromisoformat(observation["end"])
                        start = (
                            date.fromisoformat(observation["start"])
                            if "start" in observation
                            else None
                        )
                        days = (end - start).days + 1 if start else 0
                        kind = (
                            "INSTANT"
                            if metric in INSTANT_METRICS
                            else "ANNUAL"
                            if 330 <= days <= 400
                            else "QUARTER"
                            if 60 <= days <= 110
                            else "YTD"
                        )
                        currency = None if unit == "shares" else unit.split("/")[0]
                        expected = (
                            "shares"
                            if metric == "shares_outstanding"
                            else f"{currency}/shares"
                            if metric.startswith("eps_")
                            else currency
                        )
                        if unit != expected:
                            raise ValueError("Invalid XBRL unit")
                        item = FactInput(
                            instrument_id=instrument_id,
                            metric=metric,
                            value=observation["val"],
                            unit="SHARES"
                            if unit == "shares"
                            else "PER_SHARE"
                            if "/shares" in unit
                            else "MONEY",
                            currency=currency,
                            period_start=start,
                            period_end=end,
                            period_type=kind,
                            fiscal_year=observation.get("fy"),
                            fiscal_quarter=None,
                            filing_reference=filing.accession_number,
                            known_at=filing.accepted_at,
                            availability_evidence=(
                                f"SEC acceptance metadata {filing.id}; "
                                "locally observed companyfacts"
                            ),
                            consolidated=True,
                        )
                        key = (start, end, kind, filing.accession_number)
                        candidates.setdefault(key, []).append(item)
                    except (ValueError, KeyError):
                        warnings.append(f"REJECTED_XBRL:{metric}:{tag}")
        for values in candidates.values():
            if len({(item.value, item.unit, item.currency) for item in values}) == 1:
                inputs.append(values[0])
            else:
                warnings.append(f"AMBIGUOUS_XBRL:{metric}")
    # Order original releases before amendments; never depend on SEC array order.
    inputs.sort(key=lambda item: item.known_at or datetime.min.replace(tzinfo=UTC))
    return inputs, warnings


class SecCollector:
    def __init__(
        self,
        db: AsyncSession,
        raw: RawIngestionService | None = None,
        client: httpx.AsyncClient | None = None,
        limiter: Callable[[DataSource], Awaitable[None]] = check_sec_rate,
    ) -> None:
        self.db, self.raw, self.client, self.limiter = (
            db,
            raw or RawIngestionService(db),
            client,
            limiter,
        )

    async def fetch(self, path: str, instrument_id: UUID, *, archive: bool = False) -> RawIngestion:
        source = await SourceService(self.db).get("SEC_EDGAR")
        use = "filings" if archive else "fundamentals"
        SourceGate.require_enabled(source, use)
        settings = get_settings()
        if (
            not settings.sec_enabled
            or not settings.sec_user_agent.strip()
            or "@" not in settings.sec_contact_email
        ):
            raise AppError(
                409, "SEC_UNCONFIGURED", "SEC activation and contact configuration required"
            )
        if archive:
            if not re.fullmatch(r"/Archives/edgar/data/\d+/\d{18}/[A-Za-z0-9_.-]+", path):
                raise AppError(422, "SEC_ENDPOINT_INVALID", "Invalid SEC filing path")
        elif settings.sec_base_url != "https://data.sec.gov" or not re.fullmatch(
            r"/(submissions/CIK\d{10}\.json|api/xbrl/companyfacts/CIK\d{10}\.json)", path
        ):
            raise AppError(
                422, "SEC_ENDPOINT_INVALID", "Only verified official SEC endpoints allowed"
            )
        from app.providers.http import fetch_response

        return await fetch_response(
            self.db,
            self.raw,
            source,
            use=use,
            url=("https://www.sec.gov" if archive else settings.sec_base_url) + path,
            allowed_host="www.sec.gov" if archive else "data.sec.gov",
            resource="sec_response",
            client=self.client,
            instrument_id=instrument_id,
            limiter=self.limiter,
            headers={
                "User-Agent": f"{settings.sec_user_agent} {settings.sec_contact_email}",
                "Accept": "text/html" if archive else "application/json",
            },
            metadata={"parser_version": "sec-companyfacts-v1"},
            content_types=("text/html", "application/xhtml+xml", "application/pdf", "text/plain")
            if archive
            else ("application/json",),
        )

    async def download_filing(self, filing_id: UUID) -> Filing:
        filing = await self.db.get(Filing, filing_id)
        source = await SourceService(self.db).get("SEC_EDGAR")
        SourceGate.require_enabled(source, "filings")
        if filing is None or filing.source_id != source.id or not filing.document_url:
            raise AppError(404, "FILING_NOT_FOUND", "Verified SEC filing required")
        parsed = urlsplit(filing.document_url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "www.sec.gov"
            or parsed.query
            or parsed.fragment
        ):
            raise AppError(422, "SEC_ENDPOINT_INVALID", "Verified SEC archive URL required")
        raw = await self.fetch(parsed.path, filing.instrument_id, archive=True)
        document = Filing(
            instrument_id=filing.instrument_id,
            accession_number=filing.accession_number,
            filing_type=filing.filing_type,
            filing_date=filing.filing_date,
            accepted_at=filing.accepted_at,
            period_end=filing.period_end,
            document_url=filing.document_url,
            document_hash=raw.sha256,
            response_hash=raw.sha256,
            source_id=source.id,
            raw_ingestion_id=raw.id,
            known_at=filing.known_at,
            observed_at=raw.received_at,
            retrieved_at=raw.received_at,
            availability_evidence=f"SEC primary bytes; acceptance metadata filing {filing.id}",
        )
        self.db.add(document)
        await self.db.commit()
        return document

    async def collect(self, instrument_id: UUID, cik: str) -> dict[str, object]:
        try:
            return await self._collect(instrument_id, cik)
        except AppError as error:
            if error.code not in {"SOURCE_NOT_APPROVED", "SEC_UNCONFIGURED", "CIK_INVALID"}:
                await self.db.rollback()
                source = await SourceService(self.db).get("SEC_EDGAR")
                await self.db.refresh(source)
                source.last_failure = datetime.now(UTC)
                source.failure_count += 1
                await self.db.commit()
            raise

    async def _collect(self, instrument_id: UUID, cik: str) -> dict[str, object]:
        if not re.fullmatch(r"\d{1,10}", cik):
            raise AppError(422, "CIK_INVALID", "CIK must be numeric")
        cik = cik.zfill(10)
        instrument = await self.db.get(Instrument, instrument_id)
        if instrument is None or instrument.country != "US" or not instrument.ticker:
            raise AppError(
                409, "SEC_IDENTITY_REVIEW", "Reviewed US instrument required before collection"
            )
        submissions_raw = await self.fetch(f"/submissions/CIK{cik}.json", instrument_id)
        instrument = await self.db.get(Instrument, instrument_id)
        try:
            metadata = json.loads(await self.raw.get_verified(submissions_raw.id))
            if not isinstance(metadata, dict):
                raise ValueError("Invalid submissions object")
        except (ValueError, TypeError) as error:
            raise AppError(422, "SEC_PARSE_FAILED", "Invalid SEC submissions") from error
        if (
            instrument is None
            or instrument.country != "US"
            or not instrument.ticker
            or instrument.ticker not in metadata.get("tickers", [])
        ):
            raise AppError(
                409, "SEC_IDENTITY_REVIEW", "CIK and instrument identity need explicit review"
            )
        try:
            rows = parse_submissions(await self.raw.get_verified(submissions_raw.id), cik)
        except (ValueError, KeyError, TypeError) as error:
            raise AppError(422, "SEC_PARSE_FAILED", "Invalid SEC submissions") from error
        filings: dict[str, Filing] = {}
        for row in rows:
            accession = cast(str, row["accession_number"])
            filing = (
                await self.db.scalars(
                    select(Filing)
                    .where(
                        Filing.instrument_id == instrument_id,
                        Filing.source_id == submissions_raw.source_id,
                        Filing.accession_number == accession,
                    )
                    .order_by(Filing.observed_at.desc())
                    .limit(1)
                )
            ).one_or_none()
            if filing is None:
                accepted = cast(datetime, row["accepted_at"])
                if accepted > submissions_raw.received_at:
                    raise AppError(422, "SEC_FUTURE_FILING", "Future acceptance timestamp")
                filing = Filing(
                    **row,
                    instrument_id=instrument_id,
                    source_id=submissions_raw.source_id,
                    raw_ingestion_id=submissions_raw.id,
                    response_hash=submissions_raw.sha256,
                    document_hash=None,
                    known_at=accepted,
                    observed_at=submissions_raw.received_at,
                    retrieved_at=submissions_raw.received_at,
                    availability_evidence=(
                        "SEC submissions acceptance timestamp; "
                        "hash refers to metadata response, not primary document"
                    ),
                )
                self.db.add(filing)
                await self.db.flush()
            filings[accession] = filing
        await self.db.commit()
        facts_raw = await self.fetch(f"/api/xbrl/companyfacts/CIK{cik}.json", instrument_id)
        try:
            inputs, warnings = parse_companyfacts(
                await self.raw.get_verified(facts_raw.id), cik, instrument_id, filings
            )
            result = await FundamentalService(self.db, self.raw).persist(
                inputs, facts_raw, parser="sec-companyfacts-v1", filings=filings
            )
            for index, warning in enumerate(sorted(set(warnings)), 1):
                self.db.add(
                    DataQuarantine(
                        raw_ingestion_id=facts_raw.id,
                        source_id=facts_raw.source_id,
                        instrument_id=instrument_id,
                        row_number=index,
                        data_type="fundamental",
                        record_key=f"sec-warning:{index}",
                        reason=warning,
                        severity="ERROR",
                        row_data={},
                    )
                )
            source = await SourceService(self.db).get("SEC_EDGAR")
            source.last_success = datetime.now(UTC)
            await self.db.commit()
            return {
                "raw_ingestion_id": facts_raw.id,
                "filings": len(filings),
                "warnings": warnings,
                **result,
            }
        except (ValueError, KeyError, TypeError) as error:
            await self.db.rollback()
            raise AppError(422, "SEC_PARSE_FAILED", "Invalid SEC company facts") from error
