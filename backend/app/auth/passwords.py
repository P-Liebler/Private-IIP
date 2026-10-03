from __future__ import annotations

from argon2 import PasswordHasher as Argon2PasswordHasher
from argon2 import Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class PasswordService:
    def __init__(self) -> None:
        self._hasher = Argon2PasswordHasher(
            time_cost=3, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16, type=Type.ID
        )

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, encoded: str) -> bool:
        try:
            return bool(self._hasher.verify(encoded, password))
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, encoded: str) -> bool:
        try:
            return bool(self._hasher.check_needs_rehash(encoded))
        except InvalidHashError:
            return True


passwords = PasswordService()
