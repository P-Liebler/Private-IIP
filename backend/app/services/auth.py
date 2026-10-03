from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from redis.exceptions import RedisError
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import passwords
from app.auth.totp import totp_service
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.valkey import make_valkey_client
from app.models import SessionRecord, User
from app.repositories.core import find_session_by_hash, find_user_by_id, find_user_by_username
from app.services.audit import audit_service
from app.services.rate_limit import rate_limiter

logger = logging.getLogger(__name__)
USERNAME_PATTERN = re.compile(r"^[a-z0-9_.-]{3,64}$")
CHALLENGE_TTL_SECONDS = 300
TOTP_SETUP_TTL_SECONDS = 600
_DUMMY_HASH = passwords.hash(secrets.token_urlsafe(32))


def normalize_username(username: str) -> str:
    normalized = username.strip().lower()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Username must be 3–64 ASCII letters, digits, dots, underscores or hyphens"
        )
    return normalized


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def client_ip_address(client_host: str | None) -> str:
    # Do not trust client-controlled X-Forwarded-For without a configured proxy trust boundary.
    return client_host or "unknown"


async def commit_security_change(db: AsyncSession) -> None:
    try:
        await db.commit()
    except SQLAlchemyError as error:
        await db.rollback()
        logger.exception("security state and audit commit failed")
        raise AppError(
            503, "AUTH_UNAVAILABLE", "Authentication is temporarily unavailable"
        ) from error


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: SessionRecord


@dataclass(frozen=True)
class AuthenticatedLogin:
    user: User
    token: str


@dataclass(frozen=True)
class TotpChallenge:
    challenge: str


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_user(self, username: str, password: str) -> User:
        normalized = normalize_username(username)
        if len(password) < 12 or len(password) > 1024:
            raise ValueError("Password must contain between 12 and 1024 characters")
        if await find_user_by_username(self.db, normalized) is not None:
            raise ValueError("User already exists")
        user = User(
            id=uuid4(),
            username=normalized,
            password_hash=await asyncio.to_thread(passwords.hash, password),
        )
        self.db.add(user)
        await self.db.flush()
        audit_service.record(
            self.db,
            event="user.created",
            resource="user",
            actor_user_id=user.id,
            resource_id=str(user.id),
            metadata={"source": "admin_cli"},
        )
        try:
            await self.db.commit()
        except IntegrityError as error:
            await self.db.rollback()
            raise ValueError("User already exists") from error
        return user

    async def _record_login_failure(
        self, username: str, *, user: User | None, ip_address: str, factor: str
    ) -> None:
        audit_service.record(
            self.db,
            event="auth.login_failure",
            resource="user",
            actor_user_id=user.id if user is not None else None,
            resource_id=str(user.id) if user is not None else None,
            metadata={"username": username, "factor": factor},
            ip_address=ip_address,
        )
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            logger.exception("login failure audit could not be saved")

    async def _create_session(
        self, user: User, *, ip_address: str, user_agent: str | None, factor: str
    ) -> AuthenticatedLogin:
        now = datetime.now(UTC)
        token = secrets.token_urlsafe(48)
        record = SessionRecord(
            id=uuid4(),
            user_id=user.id,
            token_hash=token_hash(token),
            created_at=now,
            expires_at=now + timedelta(hours=get_settings().session_ttl_hours),
            last_seen_at=now,
            ip_address=ip_address[:45],
            user_agent=user_agent[:512] if user_agent else None,
        )
        self.db.add(record)
        user.last_login_at = now
        audit_service.record(
            self.db,
            event="auth.login_success",
            resource="session",
            actor_user_id=user.id,
            resource_id=str(record.id),
            metadata={"factor": factor},
            ip_address=ip_address,
        )
        await commit_security_change(self.db)
        return AuthenticatedLogin(user=user, token=token)

    async def login(
        self, username: str, password: str, *, ip_address: str, user_agent: str | None
    ) -> AuthenticatedLogin | TotpChallenge:
        try:
            normalized = normalize_username(username)
        except ValueError:
            normalized = username.strip().lower()[:64]
        await rate_limiter.check_login(ip_address, normalized)
        user = await find_user_by_username(self.db, normalized)
        encoded = user.password_hash if user is not None else _DUMMY_HASH
        valid = await asyncio.to_thread(passwords.verify, password, encoded)
        if user is None or not user.is_active or not valid:
            await self._record_login_failure(
                normalized, user=user, ip_address=ip_address, factor="password"
            )
            raise AppError(401, "INVALID_CREDENTIALS", "Invalid credentials")
        if passwords.needs_rehash(user.password_hash):
            user.password_hash = await asyncio.to_thread(passwords.hash, password)
            audit_service.record(
                self.db,
                event="auth.password_rehashed",
                resource="user",
                actor_user_id=user.id,
                resource_id=str(user.id),
            )
            await commit_security_change(self.db)
        if user.totp_enabled:
            if not user.totp_secret_encrypted:
                raise AppError(503, "TOTP_UNAVAILABLE", "Two-factor authentication is unavailable")
            totp_service.decrypt(user.totp_secret_encrypted)
            challenge = secrets.token_urlsafe(32)
            client = make_valkey_client()
            try:
                await client.set(
                    f"auth:challenge:{token_hash(challenge)}",
                    f"{user.id}|{ip_address}",
                    ex=CHALLENGE_TTL_SECONDS,
                )
            except RedisError as error:
                raise AppError(
                    503, "AUTH_UNAVAILABLE", "Authentication is temporarily unavailable"
                ) from error
            finally:
                await client.aclose()
            return TotpChallenge(challenge=challenge)
        result = await self._create_session(
            user, ip_address=ip_address, user_agent=user_agent, factor="password"
        )
        await rate_limiter.clear_login(ip_address, normalized)
        return result

    async def verify_totp_challenge(
        self, challenge: str, code: str, *, ip_address: str, user_agent: str | None
    ) -> AuthenticatedLogin:
        await rate_limiter.check_totp(ip_address)
        key = f"auth:challenge:{token_hash(challenge)}"
        client = make_valkey_client()
        try:
            challenge_data = await client.get(key)
            if not isinstance(challenge_data, bytes):
                raise AppError(401, "INVALID_TOTP", "Invalid or expired code")
            try:
                user_id_text, bound_ip = challenge_data.decode().split("|", 1)
                user_id = UUID(user_id_text)
            except (UnicodeDecodeError, ValueError) as error:
                raise AppError(401, "INVALID_TOTP", "Invalid or expired code") from error
            if bound_ip != ip_address:
                raise AppError(401, "INVALID_TOTP", "Invalid or expired code")
            user = await find_user_by_id(self.db, user_id, for_update=True)
            if (
                user is None
                or not user.is_active
                or not user.totp_enabled
                or not user.totp_secret_encrypted
            ):
                raise AppError(401, "INVALID_TOTP", "Invalid or expired code")
            secret = totp_service.decrypt(user.totp_secret_encrypted)
            step = totp_service.matching_step(secret, code)
            if step is None or (
                user.totp_last_used_step is not None and step <= user.totp_last_used_step
            ):
                await self._record_login_failure(
                    user.username, user=user, ip_address=ip_address, factor="totp"
                )
                raise AppError(401, "INVALID_TOTP", "Invalid or expired code")
            consumed = await client.getdel(key)
            if consumed != challenge_data:
                raise AppError(401, "INVALID_TOTP", "Invalid or expired code")
            user.totp_last_used_step = step
            result = await self._create_session(
                user, ip_address=ip_address, user_agent=user_agent, factor="password+totp"
            )
        except RedisError as error:
            raise AppError(
                503, "AUTH_UNAVAILABLE", "Authentication is temporarily unavailable"
            ) from error
        finally:
            await client.aclose()
        await rate_limiter.clear_totp(ip_address)
        await rate_limiter.clear_login(ip_address, user.username)
        return result

    async def authenticate(self, token: str | None) -> tuple[AuthContext | None, str]:
        if token is None:
            return None, "UNAUTHENTICATED"
        if len(token) > 256:
            return None, "SESSION_EXPIRED"
        record = await find_session_by_hash(self.db, token_hash(token))
        now = datetime.now(UTC)
        if record is None or record.revoked_at is not None or record.expires_at <= now:
            return None, "SESSION_EXPIRED"
        user = await find_user_by_id(self.db, record.user_id)
        if user is None or not user.is_active:
            return None, "UNAUTHENTICATED"
        if record.last_seen_at <= now - timedelta(minutes=5):
            record.last_seen_at = now
            await commit_security_change(self.db)
        return AuthContext(user=user, session=record), ""

    async def logout(self, context: AuthContext, *, ip_address: str) -> None:
        context.session.revoked_at = datetime.now(UTC)
        audit_service.record(
            self.db,
            event="auth.logout",
            resource="session",
            actor_user_id=context.user.id,
            resource_id=str(context.session.id),
            ip_address=ip_address,
        )
        await commit_security_change(self.db)

    async def start_totp(self, context: AuthContext, *, ip_address: str) -> tuple[str, str]:
        user = await find_user_by_id(self.db, context.user.id, for_update=True)
        if user is None or not user.is_active:
            raise AppError(401, "UNAUTHENTICATED", "Authentication required")
        if user.totp_enabled:
            raise AppError(
                409, "TOTP_ALREADY_ENABLED", "Two-factor authentication is already enabled"
            )
        secret = totp_service.generate_secret()
        user.totp_pending_secret_encrypted = totp_service.encrypt(secret)
        user.totp_pending_created_at = datetime.now(UTC)
        audit_service.record(
            self.db,
            event="auth.totp_setup_started",
            resource="user",
            actor_user_id=user.id,
            resource_id=str(user.id),
            ip_address=ip_address,
        )
        await commit_security_change(self.db)
        return secret, totp_service.provisioning_uri(secret, user.username)

    async def confirm_totp(self, context: AuthContext, code: str, *, ip_address: str) -> User:
        user = await find_user_by_id(self.db, context.user.id, for_update=True)
        if user is None or not user.is_active:
            raise AppError(401, "UNAUTHENTICATED", "Authentication required")
        if user.totp_enabled:
            raise AppError(
                409, "TOTP_ALREADY_ENABLED", "Two-factor authentication is already enabled"
            )
        if not user.totp_pending_secret_encrypted or not user.totp_pending_created_at:
            raise AppError(400, "TOTP_SETUP_REQUIRED", "Start two-factor setup first")
        if user.totp_pending_created_at < datetime.now(UTC) - timedelta(
            seconds=TOTP_SETUP_TTL_SECONDS
        ):
            user.totp_pending_secret_encrypted = None
            user.totp_pending_created_at = None
            await commit_security_change(self.db)
            raise AppError(400, "TOTP_SETUP_REQUIRED", "Two-factor setup expired; start again")
        secret = totp_service.decrypt(user.totp_pending_secret_encrypted)
        step = totp_service.matching_step(secret, code)
        if step is None:
            raise AppError(401, "INVALID_TOTP", "Invalid code")
        user.totp_secret_encrypted = user.totp_pending_secret_encrypted
        user.totp_pending_secret_encrypted = None
        user.totp_pending_created_at = None
        user.totp_enabled = True
        user.totp_last_used_step = step
        await self.db.execute(
            update(SessionRecord)
            .where(
                SessionRecord.user_id == user.id,
                SessionRecord.id != context.session.id,
                SessionRecord.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        audit_service.record(
            self.db,
            event="auth.totp_enabled",
            resource="user",
            actor_user_id=user.id,
            resource_id=str(user.id),
            ip_address=ip_address,
        )
        await commit_security_change(self.db)
        return user

    async def reset_totp(self, username: str) -> bool:
        user = await find_user_by_username(self.db, normalize_username(username), for_update=True)
        if user is None:
            return False
        user.totp_enabled = False
        user.totp_secret_encrypted = None
        user.totp_pending_secret_encrypted = None
        user.totp_pending_created_at = None
        user.totp_last_used_step = None
        await self.db.execute(
            update(SessionRecord)
            .where(SessionRecord.user_id == user.id, SessionRecord.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        audit_service.record(
            self.db,
            event="auth.totp_reset",
            resource="user",
            actor_user_id=user.id,
            resource_id=str(user.id),
            metadata={"source": "admin_cli"},
        )
        await commit_security_change(self.db)
        return True
