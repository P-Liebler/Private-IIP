"""Missing bytes and incompatible pinned runtimes must never load a model."""

import asyncio
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.services.ml_registry import ModelRegistryService
from app.services.pit_datasets import code_manifest


def synthetic_model(data, code):
    training_id = uuid4()
    artifact_hash = hashlib.sha256(data).hexdigest()
    return SimpleNamespace(
        training_run_id=training_id,
        artifact_key=f"model-artifacts/{training_id}/{artifact_hash}.json",
        artifact_hash=artifact_hash,
        configuration={"request": {}, "code": code},
    )


def test_missing_model_bytes_fail_without_fallback():
    model = synthetic_model(b"missing synthetic artifact", {})
    storage = SimpleNamespace(get=Mock(side_effect=FileNotFoundError("synthetic missing bytes")))
    with patch("app.services.ml_registry.get_storage", return_value=storage):
        with pytest.raises(FileNotFoundError):
            asyncio.run(ModelRegistryService(Mock()).artifact(model))
    storage.get.assert_called_once_with(model.artifact_key)


def test_incompatible_dependency_contract_is_rejected_without_rewriting_artifact():
    pinned = code_manifest() | {"dependencies": {"numpy": "synthetic-incompatible-runtime"}}
    artifact = {
        "contract": "internal-data-only-model-v1",
        "configuration": {},
        "training_code": pinned,
    }
    data = json.dumps(artifact).encode()
    model = synthetic_model(data, pinned)
    storage = SimpleNamespace(get=Mock(return_value=data))
    with patch("app.services.ml_registry.get_storage", return_value=storage):
        with pytest.raises(AppError) as caught:
            asyncio.run(ModelRegistryService(Mock()).artifact(model))
    assert caught.value.status_code == 409
    assert caught.value.code == "ARTIFACT_DEPENDENCY_MISMATCH"
    assert model.artifact_hash == hashlib.sha256(data).hexdigest()
    storage.get.assert_called_once_with(model.artifact_key)
