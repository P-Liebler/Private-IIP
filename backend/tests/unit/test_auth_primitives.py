from __future__ import annotations

from datetime import UTC, datetime

import pyotp
import pytest
from pydantic import ValidationError

from app.auth.passwords import PasswordService
from app.auth.totp import TotpService
from app.core.config import get_settings
from app.schemas.settings import SettingsUpdate


def test_password_hash_verify_and_rehash() -> None:
    service = PasswordService()
    encoded = service.hash("test-only-password-123")
    assert encoded.startswith("$argon2id$")
    assert service.verify("test-only-password-123", encoded)
    assert not service.verify("wrong-password", encoded)
    assert not service.needs_rehash(encoded)
    assert service.needs_rehash("invalid")


def test_totp_fixed_time_and_encryption() -> None:
    # Fixed time avoids a clock-boundary test.
    service = TotpService()
    secret = "JBSWY3DPEHPK3PXP"
    instant = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    code = pyotp.TOTP(secret).at(instant)
    assert service.matching_step(secret, code, now=instant) == int(instant.timestamp() // 30)
    assert service.matching_step(secret, "0000000", now=instant) is None
    assert service.matching_step(secret, "abcdef", now=instant) is None
    if get_settings().totp_encryption_key is None:
        pytest.skip("TOTP_ENCRYPTION_KEY is required for encryption check")
    encrypted = service.encrypt(secret)
    assert secret not in encrypted
    assert service.decrypt(encrypted) == secret


def test_settings_validation() -> None:
    assert SettingsUpdate(timezone="Europe/Zurich", base_currency="CHF").timezone == "Europe/Zurich"
    for payload in ({"timezone": "No/Such_Zone"}, {"base_currency": "chf"}, {"timezone": None}):
        try:
            SettingsUpdate.model_validate(payload)
        except ValidationError:
            continue
        raise AssertionError(f"Expected validation error for {payload}")
