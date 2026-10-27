from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

import pytest

from app.assistant.documents import PIPELINE
from app.core.runtime_contract import verify_tls_runtime


def test_pr6_parser_rejected_and_archived_contract_preserved():
    verify_tls_runtime()
    with patch(
        "app.core.runtime_contract.version",
        side_effect=lambda package: "6.21.1" if package == "pypdf" else version(package),
    ):
        with pytest.raises(RuntimeError, match="DOCUMENT_PARSER_RUNTIME_MISMATCH"):
            verify_tls_runtime()
    archived = Path("legacy_contracts/pr6/requirements-assistant.lock").read_text(encoding="utf-8")
    assert archived.replace("pypdf==6.21.1", "pypdf==6.21.2") == Path(
        "requirements-assistant.lock"
    ).read_text(encoding="utf-8")
    assert Path("legacy_contracts/pr6/requirements.lock").read_text(encoding="utf-8") == Path(
        "requirements.lock"
    ).read_text(encoding="utf-8")
    assert PIPELINE == "pypdf-6.21.2:plain-text-no-ocr:chunk600-overlap80-v3"
