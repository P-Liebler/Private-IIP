"""Company-specific manual PDF review; extraction never creates financial facts."""

from typing import Any, Literal
from uuid import UUID

from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.documents import parse_pdf, require_data_operator
from app.core.errors import AppError
from app.models import RawIngestion, User
from app.schemas.pit import StrictModel
from app.schemas.research import FactInput
from app.services.fundamentals import FundamentalService
from app.services.raw_ingestion import RawIngestionService
from app.services.sources import SourceGate, SourceService


class ReviewedReportFact(StrictModel):
    fact: FactInput
    page: int = Field(ge=1, le=50)
    quotation: str = Field(min_length=5, max_length=1000)
    accounting_basis: Literal["IFRS", "SWISS_GAAP_FER", "US_GAAP"]
    definition: str = Field(min_length=10, max_length=500)


class ReportReviewInput(StrictModel):
    reviewed: Literal[True]
    document_reference: str = Field(min_length=10, max_length=200)
    candidates: list[ReviewedReportFact] = Field(min_length=1, max_length=50)


class IRReportReviewService:
    def __init__(self, db: AsyncSession, user: User) -> None:
        self.db, self.user = db, user
        self.raw = RawIngestionService(db)

    async def upload(self, source_slug: str, instrument_id: UUID, data: bytes) -> RawIngestion:
        require_data_operator(self.user)
        source = await SourceService(self.db).get(source_slug)
        SourceGate.require_enabled(source, "fundamentals")
        SourceGate.require_enabled(source, "filings")
        if len(data) > 5_000_000 or not data.startswith(b"%PDF-"):
            raise AppError(422, "REPORT_PDF_INVALID", "Bounded PDF report required")
        return await self.raw.store(
            data=data,
            source_id=source.id,
            source_slug=source.slug,
            resource_type="ir_report_review",
            instrument_id=instrument_id,
            content_type="application/pdf",
            request_metadata={"user_id": str(self.user.id), "filename": "report.pdf"},
        )

    async def preview(self, raw_id: UUID) -> dict[str, Any]:
        require_data_operator(self.user)
        raw = await self.raw.get(raw_id)
        if raw.resource_type != "ir_report_review" or raw.request_metadata.get("user_id") != str(
            self.user.id
        ):
            raise AppError(404, "REPORT_NOT_FOUND", "Private original report required")
        from app.models import DataSource

        source = await self.db.get(DataSource, raw.source_id)
        assert source
        SourceGate.require_enabled(source, "fundamentals")
        SourceGate.require_enabled(source, "filings")
        pages = await parse_pdf(await self.raw.get_verified(raw_id))
        return {
            "raw_ingestion_id": str(raw_id),
            "sha256": raw.sha256,
            "pages": pages,
            "status": "REVIEW_REQUIRED",
            "canonical_facts_created": 0,
        }

    async def commit(self, raw_id: UUID, review: ReportReviewInput) -> dict[str, int]:
        preview = await self.preview(raw_id)
        pages = {p["page"]: p["text"] for p in preview["pages"]}
        raw = await self.raw.get(raw_id)
        inputs = []
        for candidate in review.candidates:
            if (
                candidate.fact.instrument_id != raw.instrument_id
                or candidate.quotation not in pages.get(candidate.page, "")
            ):
                raise AppError(
                    422,
                    "REPORT_EVIDENCE_INVALID",
                    "Exact page quotation and original instrument required",
                )
            item = FactInput.model_validate(
                {
                    **candidate.fact.model_dump(),
                    "availability_evidence": f"Reviewed by {self.user.username}; "
                    f"{candidate.accounting_basis}; {review.document_reference}; "
                    f"page {candidate.page}; {candidate.definition}; {candidate.quotation}; "
                    f"original={raw_id}; sha256={raw.sha256}",
                }
            )
            inputs.append(item)
        from app.models import DataSource

        source = await self.db.get(DataSource, raw.source_id)
        assert source
        confirmation = await self.raw.store(
            data=review.model_dump_json().encode(),
            source_id=raw.source_id,
            source_slug=source.slug,
            resource_type="ir_report_confirmation",
            instrument_id=raw.instrument_id,
            content_type="application/json",
            request_metadata={
                "user_id": str(self.user.id),
                "identifier_value": str(raw_id),
                "filename": "human-review.json",
                "parser_version": "ir-pdf-human-review-v1",
            },
        )
        result = await FundamentalService(self.db, self.raw).persist(
            inputs, confirmation, parser="ir-pdf-human-review-v1"
        )
        await self.db.commit()
        return result
