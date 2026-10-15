import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.models import Prediction
from app.services.ml_registry import ModelRegistryService
from app.services.predictions import PredictionService
from app.services.recommendations import RecommendationService


def test_shadow_model_never_authorizes_even_a_validated_prediction_claim(monkeypatch):
    uid, iid, mid, did = uuid4(), uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    prediction = Prediction(
        user_id=uid,
        instrument_id=iid,
        model_id=mid,
        dataset_id=did,
        horizon=30,
        generated_at=now,
        information_cutoff_at=now,
        result={"confidence_status": "VALIDATED", "model_versions": [str(mid)]},
    )

    async def generate(*_args):
        return prediction

    async def status(*_args):
        return "SHADOW"

    class FixtureSession:
        async def get(self, *_args):
            return SimpleNamespace(id=mid, user_id=uid, horizon=30)

    monkeypatch.setattr(PredictionService, "generate", generate)
    monkeypatch.setattr(ModelRegistryService, "status", status)
    _, valid = asyncio.run(RecommendationService(FixtureSession(), uid).forecast(iid, 30, now))
    assert not valid
