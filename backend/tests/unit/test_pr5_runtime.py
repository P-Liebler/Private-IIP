"""Patched API runtime and unchanged legacy dependency gate."""

import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.core.runtime_contract import verify_tls_runtime
from app.services.ml_registry import ModelRegistryService


def test_unpatched_tls_package_cannot_start_normal_runtime():
    verify_tls_runtime()
    with patch("app.core.runtime_contract.version", return_value="2026.7.22"):
        with pytest.raises(RuntimeError, match="CORE_TLS_RUNTIME_MISMATCH"):
            verify_tls_runtime()


def test_unpatched_document_parser_cannot_start_normal_runtime():
    with patch(
        "app.core.runtime_contract.version",
        side_effect=lambda package: "2026.10.19" if package == "certifi" else "6.20.1",
    ):
        with pytest.raises(RuntimeError, match="DOCUMENT_PARSER_RUNTIME_MISMATCH"):
            verify_tls_runtime()


def test_archived_core_contract_is_preserved_and_rejected_by_patched_api():
    legacy = Path("legacy_contracts/pr4/requirements.lock").read_text(encoding="utf-8")
    patched = Path("requirements.lock").read_text(encoding="utf-8")
    assert (
        legacy.replace("certifi==2026.7.22", "certifi==2026.10.19").replace(
            "opentelemetry-api==1.45.0", "opentelemetry-api==1.45.1"
        )
        == patched
    )
    code = {"dependencies": legacy}
    data = json.dumps(
        {"contract": "internal-data-only-model-v1", "configuration": {}, "training_code": code}
    ).encode()
    digest = hashlib.sha256(data).hexdigest()
    training = uuid4()
    model = SimpleNamespace(
        training_run_id=training,
        artifact_hash=digest,
        artifact_key=f"model-artifacts/{training}/{digest}.json",
        configuration={"request": {}, "code": code},
    )
    storage = SimpleNamespace(get=Mock(return_value=data))
    with patch("app.services.ml_registry.get_storage", return_value=storage):
        service = ModelRegistryService(Mock())
        assert asyncio.run(service.archived_bytes(model))[0] == data
        with pytest.raises(AppError) as error:
            asyncio.run(service.artifact(model))
    assert error.value.code == "ARTIFACT_DEPENDENCY_MISMATCH"
    assert model.artifact_hash == hashlib.sha256(data).hexdigest()
