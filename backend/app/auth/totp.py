from __future__ import annotations

from datetime import UTC, datetime

import pyotp
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.errors import AppError

ISSUER = "Investment Intelligence"
TOTP_PERIOD_SECONDS = 30


class TotpService:
    def _fernet(self) -> Fernet:
        key = get_settings().totp_encryption_key
        if key is None:
            raise AppError(503, "TOTP_UNAVAILABLE", "Two-factor authentication is not configured")
        return Fernet(key.get_secret_value().encode())

    def generate_secret(self) -> str:
        self._fernet()  # Do not start setup when encryption is unavailable.
        return pyotp.random_base32()

    def encrypt(self, secret: str) -> str:
        return self._fernet().encrypt(secret.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        try:
            return self._fernet().decrypt(encrypted.encode()).decode()
        except InvalidToken as error:
            raise AppError(
                503, "TOTP_UNAVAILABLE", "Two-factor secret cannot be decrypted"
            ) from error

    def provisioning_uri(self, secret: str, username: str) -> str:
        return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=ISSUER)

    def matching_step(self, secret: str, code: str, *, now: datetime | None = None) -> int | None:
        if len(code) != 6 or not code.isascii() or not code.isdigit():
            return None
        current = int((now or datetime.now(UTC)).timestamp() // TOTP_PERIOD_SECONDS)
        totp = pyotp.TOTP(secret)
        for step in (current - 1, current, current + 1):
            if totp.verify(
                code,
                for_time=datetime.fromtimestamp(step * TOTP_PERIOD_SECONDS, UTC),
                valid_window=0,
            ):
                return step
        return None


totp_service = TotpService()
