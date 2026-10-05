from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_user
from app.core.errors import AppError
from app.db.session import get_session
from app.schemas.imports import CsvPreviewResponse
from app.services.auth import AuthContext
from app.services.csv_preview import CsvPreviewService

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])


@router.post("/csv/preview", response_model=CsvPreviewResponse)
async def preview_csv(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    _context: Annotated[AuthContext, Depends(require_user)],
) -> CsvPreviewResponse:
    if request.headers.get("Content-Type", "").split(";", 1)[0].lower() != "text/csv":
        raise AppError(415, "CSV_CONTENT_TYPE_REQUIRED", "Upload a text/csv file")
    filename = request.headers.get("X-Filename", "upload.csv")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 5_000_000:
            raise AppError(413, "CSV_SIZE_INVALID", "CSV exceeds 5 MB")
    try:
        return await CsvPreviewService(db).preview(bytes(data), filename=filename)
    except ValueError as error:
        raise AppError(422, "CSV_METADATA_INVALID", str(error)) from error
