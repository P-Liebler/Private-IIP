"""Isolated synthetic TOTP-key recovery contract, never an operator-key backup."""

import json

from cryptography.fernet import Fernet, InvalidToken


def main() -> None:
    from app.core.config import get_settings

    if get_settings().app_env != "test":
        raise RuntimeError("Synthetic recovery drill requires APP_ENV=test")
    key = Fernet.generate_key()
    protected = Fernet(key).encrypt(b"SYNTHETIC-TOTP-FACTOR")
    wrapping_key = Fernet.generate_key()
    encrypted_backup = Fernet(wrapping_key).encrypt(key)
    recovered_key = Fernet(wrapping_key).decrypt(encrypted_backup)
    assert Fernet(recovered_key).decrypt(protected) == b"SYNTHETIC-TOTP-FACTOR"
    try:
        Fernet(Fernet.generate_key()).decrypt(protected)
        raise AssertionError("Wrong key accepted")
    except InvalidToken:
        pass
    print(
        json.dumps(
            {
                "synthetic_totp_key_recovery": "PASSED",
                "wrong_key": "REJECTED",
                "operator_secret_recovery": "NOT_VERIFIED",
                "ca_client_trust": "NOT_VERIFIED",
            }
        )
    )


if __name__ == "__main__":
    main()
