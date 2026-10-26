from importlib.metadata import version
from unittest.mock import patch

import pytest

from app.core.runtime_contract import verify_tls_runtime


def test_unpatched_telemetry_cannot_start_normal_runtime():
    def installed(package: str) -> str:
        return "1.45.0" if package == "opentelemetry-api" else version(package)

    with patch("app.core.runtime_contract.version", side_effect=installed):
        with pytest.raises(RuntimeError, match="TELEMETRY_RUNTIME_MISMATCH"):
            verify_tls_runtime()
