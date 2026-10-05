from __future__ import annotations

import asyncio
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.db.session import get_engine, get_session_factory
from app.models import AuditEvent
from app.repositories.core import find_user_by_username


@pytest.mark.integration
def test_admin_cli_creates_once_and_resets_totp() -> None:
    username = f"cli_{uuid4().hex[:12]}"
    password = "test-only-cli-password-123"
    try:
        created = subprocess.run(
            [sys.executable, "-m", "app.auth.cli", "create-user", username],
            input=f"{password}\n{password}\n",
            text=True,
            capture_output=True,
            check=False,
        )
        assert created.returncode == 0
        assert f"Created user {username}" in created.stdout
        assert password not in created.stdout + created.stderr

        duplicate = subprocess.run(
            [sys.executable, "-m", "app.auth.cli", "create-user", username],
            input=f"{password}\n{password}\n",
            text=True,
            capture_output=True,
            check=False,
        )
        assert duplicate.returncode == 1
        assert "User already exists" in duplicate.stderr

        reset = subprocess.run(
            [sys.executable, "-m", "app.auth.cli", "reset-totp", username],
            input="RESET\n",
            text=True,
            capture_output=True,
            check=False,
        )
        assert reset.returncode == 0
        assert "all sessions revoked" in reset.stdout
    finally:

        async def cleanup() -> None:
            try:
                async with get_session_factory()() as db:
                    user = await find_user_by_username(db, username)
                    if user is not None:
                        await db.execute(
                            delete(AuditEvent).where(AuditEvent.actor_user_id == user.id)
                        )
                        await db.delete(user)
                        await db.commit()
            finally:
                await get_engine().dispose()

        asyncio.run(cleanup())
