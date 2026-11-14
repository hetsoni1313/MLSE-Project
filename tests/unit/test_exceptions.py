"""Tests for custom exception hierarchy."""

import pytest

from llmops_governance.core.exceptions import (
    BackendError,
    BackendTimeoutError,
    ConfigurationError,
    InvalidPredictionError,
    LLMOpsError,
    ModelNotAvailableError,
    RollbackTriggered,
)


class TestExceptions:
    def test_base_exception(self):
        err = LLMOpsError("General failure")
        assert isinstance(err, Exception)
        assert str(err) == "General failure"

    def test_backend_error(self):
        err = BackendError("local-model", "Connection refused")
        assert isinstance(err, LLMOpsError)
        assert err.backend == "local-model"
        assert "[local-model] Connection refused" in str(err)

    def test_backend_timeout_error(self):
        err = BackendTimeoutError("openai", 5000.0)
        assert isinstance(err, BackendError)
        assert err.timeout_ms == 5000.0
        assert "5000ms" in str(err)

    def test_invalid_prediction_error(self):
        err = InvalidPredictionError("unknown_intent", closest="change_pin")
        assert "unknown_intent" in str(err)
        assert "change_pin" in str(err)

    def test_rollback_triggered_error(self):
        err = RollbackTriggered("accuracy", 0.75, 0.85)
        assert err.trigger == "accuracy"
        assert err.value == 0.75
        assert err.threshold == 0.85
        assert "0.7500" in str(err)

    def test_configuration_error(self):
        err = ConfigurationError("Percentages must sum to 100")
        assert isinstance(err, LLMOpsError)

    def test_model_not_available_error(self):
        err = ModelNotAvailableError("qwen2.5", "weights not found")
        assert "qwen2.5" in str(err)
        assert "weights not found" in str(err)
