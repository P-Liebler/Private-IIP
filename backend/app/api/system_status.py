"""Authenticated operational status without backup paths or secrets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import require_user
from app.services.auth import AuthContext

router = APIRouter(prefix="/api/v1/system", tags=["system"])
RUNTIME = Path("/app/runtime")


def _status(name: str) -> dict[str, object]:
    try:
        value = json.loads((RUNTIME / name).read_text(encoding="utf-8"))
        return {
            "status": "SUCCESS" if value["success"] else "FAILED",
            "completed_at": value.get("completed_at"),
            "run_id": value.get("run_id", value.get("backup_run_id")),
        }
    except (OSError, ValueError, KeyError, TypeError):
        return {"status": "UNAVAILABLE", "completed_at": None, "run_id": None}


@router.get("/backup-status")
async def backup_status(_user: Annotated[AuthContext, Depends(require_user)]) -> dict[str, object]:
    return {"backup": _status("backup-status.json"), "restore_test": _status("restore-status.json")}
