from __future__ import annotations

import asyncio
import time
from uuid import uuid4

import pyotp
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.session import get_engine, get_session_factory
from app.main import create_app
from app.models import AuditEvent, SessionRecord, User
from app.services.auth import AuthService, token_hash
from app.services.rate_limit import rate_limiter


@pytest.mark.integration
def test_private_auth_settings_totp_and_audit() -> None:
    if get_settings().totp_encryption_key is None:
        pytest.skip("TOTP_ENCRYPTION_KEY is required for the integration flow")

    async def run() -> None:
        username = f"auth_{uuid4().hex[:12]}"
        password = "test-only-long-password-2"
        async with get_session_factory()() as db:
            user = await AuthService(db).create_user(username, password)
            user_id = user.id
        try:
            async with AsyncClient(
                transport=ASGITransport(app=create_app()),
                base_url="http://testserver",
                headers={"Origin": get_settings().frontend_origin},
            ) as client:
                assert (await client.get("/api/v1/auth/session")).json() == {
                    "authenticated": False,
                    "user": None,
                }
                denied = await client.get("/api/v1/settings")
                assert denied.status_code == 401
                unknown = f"absent_{uuid4().hex[:12]}"
                try:
                    for _ in range(get_settings().auth_login_max_attempts):
                        attempt = await client.post(
                            "/api/v1/auth/login", json={"username": unknown, "password": "wrong"}
                        )
                        assert attempt.status_code == 401
                    limited = await client.post(
                        "/api/v1/auth/login", json={"username": unknown, "password": "wrong"}
                    )
                    assert limited.status_code == 429
                    assert "Retry-After" in limited.headers
                finally:
                    await rate_limiter.clear_login("127.0.0.1", unknown)
                bad = await client.post(
                    "/api/v1/auth/login", json={"username": username, "password": "incorrect"}
                )
                assert bad.status_code == 401
                login = await client.post(
                    "/api/v1/auth/login", json={"username": username, "password": password}
                )
                assert login.status_code == 200
                assert login.json()["status"] == "authenticated"
                assert "httponly" in login.headers["set-cookie"].lower()
                assert "samesite=lax" in login.headers["set-cookie"].lower()
                token = client.cookies.get(get_settings().session_cookie_name)
                assert token is not None
                async with get_session_factory()() as db:
                    record = await db.scalar(
                        select(SessionRecord).where(SessionRecord.token_hash == token_hash(token))
                    )
                    assert record is not None and record.token_hash != token
                    account = await db.get(User, user_id)
                    assert account is not None
                    account.is_active = False
                    await db.commit()
                assert (await client.get("/api/v1/settings")).status_code == 401
                async with get_session_factory()() as db:
                    account = await db.get(User, user_id)
                    assert account is not None
                    account.is_active = True
                    await db.commit()
                assert (await client.get("/api/v1/settings")).json() == {
                    "timezone": "Europe/Zurich",
                    "base_currency": "CHF",
                }
                assert (
                    await client.patch("/api/v1/settings", json={"timezone": "No/Such_Zone"})
                ).status_code == 422
                assert (
                    await client.patch("/api/v1/settings", json={"base_currency": "chf"})
                ).status_code == 422
                csrf = await client.patch(
                    "/api/v1/settings",
                    json={"timezone": "UTC"},
                    headers={"Origin": "https://attacker.example"},
                )
                assert csrf.status_code == 403
                changed = await client.patch(
                    "/api/v1/settings", json={"timezone": "UTC", "base_currency": "EUR"}
                )
                assert changed.status_code == 200
                assert changed.json() == {"timezone": "UTC", "base_currency": "EUR"}
                setup = await client.post("/api/v1/auth/totp/setup")
                assert setup.status_code == 200
                secret = setup.json()["secret"]
                assert setup.json()["provisioning_uri"].startswith("otpauth://totp/")
                async with get_session_factory()() as db:
                    account = await db.get(User, user_id)
                    assert account is not None and not account.totp_enabled
                    assert account.totp_pending_secret_encrypted is not None
                    assert secret not in account.totp_pending_secret_encrypted
                assert (
                    await client.post("/api/v1/auth/totp/confirm", json={"code": "000000"})
                ).status_code == 401
                current_step = int(time.time() // 30)
                confirm = await client.post(
                    "/api/v1/auth/totp/confirm",
                    json={"code": pyotp.TOTP(secret).at(current_step * 30)},
                )
                assert confirm.status_code == 200
                assert confirm.json()["totp_enabled"] is True
                logout = await client.post("/api/v1/auth/logout")
                assert logout.status_code == 204
                assert (await client.get("/api/v1/settings")).status_code == 401
                challenge = await client.post(
                    "/api/v1/auth/login", json={"username": username, "password": password}
                )
                assert challenge.status_code == 202
                assert challenge.json()["status"] == "totp_required"
                assert (await client.get("/api/v1/auth/session")).json()["authenticated"] is False
                verified = await client.post(
                    "/api/v1/auth/totp/verify",
                    json={
                        "challenge": challenge.json()["challenge"],
                        "code": pyotp.TOTP(secret).at((current_step + 1) * 30),
                    },
                )
                assert verified.status_code == 200
                assert (await client.get("/api/v1/auth/session")).json()["authenticated"] is True
                replay = await client.post(
                    "/api/v1/auth/totp/verify",
                    json={
                        "challenge": challenge.json()["challenge"],
                        "code": pyotp.TOTP(secret).at((current_step + 1) * 30),
                    },
                )
                assert replay.status_code == 401
                async with get_session_factory()() as db:
                    events = (
                        await db.scalars(
                            select(AuditEvent).where(AuditEvent.actor_user_id == user_id)
                        )
                    ).all()
                    names = {event.event for event in events}
                    assert {
                        "auth.login_success",
                        "auth.login_failure",
                        "auth.logout",
                        "auth.totp_setup_started",
                        "auth.totp_enabled",
                        "settings.changed",
                    } <= names
                    assert all(secret not in str(event.metadata_json) for event in events)
                    assert all(password not in str(event.metadata_json) for event in events)
                    assert all(token not in str(event.metadata_json) for event in events)
                    assert await AuthService(db).reset_totp(username)
                assert (await client.get("/api/v1/auth/session")).json()["authenticated"] is False
        finally:
            try:
                async with get_session_factory()() as db:
                    await db.execute(delete(AuditEvent).where(AuditEvent.actor_user_id == user_id))
                    await db.execute(delete(User).where(User.id == user_id))
                    await db.commit()
            finally:
                await get_engine().dispose()

    asyncio.run(run())
