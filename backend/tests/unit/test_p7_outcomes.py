import asyncio
from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.models import Instrument, Prediction
from app.services.predictions import PredictionService


def test_maturity_and_wrong_forecast_preservation(monkeypatch):
    async def run():
        user_id, instrument_id, prediction_id = uuid4(), uuid4(), uuid4()
        original = {
            "confidence_status": "VALIDATED",
            "probability_outperform": 0.9,
            "signal_day": "2024-01-02",
            "target_configuration": {
                "universe_id": str(uuid4()),
                "benchmark_id": str(uuid4()),
                "start": "2024-01-02",
                "end": "2024-03-01",
                "base_currency": "USD",
                "availability_mode": "STRICT_PIT",
                "target_horizon": 30,
            },
            "data_context": "SYNTHETIC_UNIT_TEST_ONLY",
        }
        prediction = SimpleNamespace(
            id=prediction_id,
            instrument_id=instrument_id,
            user_id=user_id,
            generated_at=datetime(2024, 1, 2, 22, tzinfo=UTC),
            result=deepcopy(original),
        )

        async def get(model, identifier):
            return (
                prediction
                if model is Prediction
                else SimpleNamespace(exchange="NYSE")
                if model is Instrument
                else None
            )

        db = SimpleNamespace(
            get=AsyncMock(side_effect=get),
            scalar=AsyncMock(return_value=None),
            add=MagicMock(),
            commit=AsyncMock(),
        )
        target = AsyncMock(return_value={"status": "TARGET_UNAVAILABLE"})
        monkeypatch.setattr("app.services.predictions.DatasetBuilder.target", target)
        service = PredictionService(db)
        assert await service.outcome(prediction_id, user_id) is None
        target.return_value = {"status": "AVAILABLE", "label_available_at": "2099-01-01T00:00:00Z"}
        assert await service.outcome(prediction_id, user_id) is None
        target.return_value = {
            "status": "AVAILABLE",
            "label_available_at": "2024-03-01T00:00:00Z",
            "instrument_return": "-0.1",
            "benchmark_return": "0.1",
            "excess_return": "-0.2",
            "classification": 0,
        }
        result = await service.outcome(prediction_id, user_id)
        assert result.result["correct"] is False
        assert result.result["actual_excess_return"] == "-0.2"
        assert prediction.result == original
        assert target.call_args.args[3] == prediction.generated_at

    asyncio.run(run())
