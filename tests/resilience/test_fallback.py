"""Tests for fallback handler."""

from unittest.mock import AsyncMock

import pytest
from gateway.backends import ModelBackend, PredictionResult
from gateway.resilience.fallback import FallbackHandler


def _make_backend(
    name: str, prediction: str = "change_pin", error: str | None = None, valid: bool = True
) -> AsyncMock:
    backend = AsyncMock(spec=ModelBackend)
    backend.name = name
    backend.predict.return_value = PredictionResult(
        prediction=prediction,
        latency_ms=100.0,
        model_name=name,
        valid_output=valid,
        error=error,
        input_tokens=10,
        output_tokens=5,
    )
    backend.health_check.return_value = True
    return backend


class TestFallbackHandler:
    @pytest.mark.asyncio
    async def test_local_success_no_fallback(self):
        local = _make_backend("local", "change_pin")
        baseline = _make_backend("baseline", "change_pin")
        handler = FallbackHandler(local, baseline)

        result, fallback, reason = await handler.predict_with_fallback("test")
        assert not fallback
        assert reason is None
        assert result.prediction == "change_pin"

    @pytest.mark.asyncio
    async def test_local_error_triggers_fallback(self):
        local = _make_backend("local", error="timeout", valid=False)
        baseline = _make_backend("baseline", "change_pin")
        handler = FallbackHandler(local, baseline)

        result, fallback, reason = await handler.predict_with_fallback("test")
        assert fallback
        assert reason == "timeout"
        assert result.model_name == "baseline"

    @pytest.mark.asyncio
    async def test_local_invalid_triggers_fallback(self):
        local = _make_backend("local", "GARBAGE", valid=False)
        baseline = _make_backend("baseline", "change_pin")
        handler = FallbackHandler(local, baseline)

        result, fallback, reason = await handler.predict_with_fallback("test")
        assert fallback

    @pytest.mark.asyncio
    async def test_fallback_count_increments(self):
        local = _make_backend("local", error="fail", valid=False)
        baseline = _make_backend("baseline", "change_pin")
        handler = FallbackHandler(local, baseline)

        await handler.predict_with_fallback("test1")
        await handler.predict_with_fallback("test2")
        assert handler.fallback_count == 2

    @pytest.mark.asyncio
    async def test_shadow_returns_baseline(self):
        local = _make_backend("local", "local_pred")
        baseline = _make_backend("baseline", "baseline_pred")
        handler = FallbackHandler(local, baseline)

        baseline_result, local_result = await handler.predict_shadow("test")
        assert baseline_result.prediction == "baseline_pred"
        assert local_result is not None
        assert local_result.prediction == "local_pred"

    @pytest.mark.asyncio
    async def test_shadow_local_failure_doesnt_affect_baseline(self):
        local = _make_backend("local", error="crash", valid=False)
        baseline = _make_backend("baseline", "baseline_pred")
        handler = FallbackHandler(local, baseline)

        baseline_result, local_result = await handler.predict_shadow("test")
        assert baseline_result.prediction == "baseline_pred"
        assert local_result is not None
