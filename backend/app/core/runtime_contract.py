"""The normal API and workers must use the patched, explicitly pinned TLS roots."""

from importlib.metadata import version
from pathlib import Path

RUNTIME_CONTRACT = "PR5_CORE_CERTIFI_20261019_PDF_6211_V2"


def verify_tls_runtime() -> None:
    pins = Path(__file__).resolve().parents[2] / "requirements.lock"
    if "certifi==2026.10.19" not in pins.read_text(encoding="utf-8").splitlines():
        raise RuntimeError("CORE_TLS_LOCK_MISMATCH")
    if version("certifi") != "2026.10.19":
        raise RuntimeError("CORE_TLS_RUNTIME_MISMATCH")
    support = pins.with_name("requirements-assistant.lock")
    if "pypdf==6.21.1" not in support.read_text(encoding="utf-8").splitlines():
        raise RuntimeError("DOCUMENT_PARSER_LOCK_MISMATCH")
    if version("pypdf") != "6.21.1":
        raise RuntimeError("DOCUMENT_PARSER_RUNTIME_MISMATCH")
