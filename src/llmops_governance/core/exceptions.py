"""Custom exception hierarchy for the LLMOps platform."""

from __future__ import annotations


class LLMOpsError(Exception):
    """Base exception for all LLMOps platform errors."""


class BackendError(LLMOpsError):
    """An inference backend encountered an error."""

    def __init__(self, backend: str, message: str, cause: Exception | None = None) -> None:
        self.backend = backend
        self.cause = cause
        super().__init__(f"[{backend}] {message}")


class BackendTimeoutError(BackendError):
    """An inference backend timed out."""

    def __init__(self, backend: str, timeout_ms: float) -> None:
        self.timeout_ms = timeout_ms
        super().__init__(backend, f"Request timed out after {timeout_ms:.0f}ms")


class InvalidPredictionError(LLMOpsError):
    """Model returned a prediction not in the valid label set."""

    def __init__(self, prediction: str, closest: str | None = None) -> None:
        self.prediction = prediction
        self.closest = closest
        msg = f"Invalid prediction: {prediction!r}"
        if closest:
            msg += f" (closest valid label: {closest!r})"
        super().__init__(msg)


class RollbackTriggered(LLMOpsError):
    """Automatic rollback was triggered due to threshold violation."""

    def __init__(self, trigger: str, value: float, threshold: float) -> None:
        self.trigger = trigger
        self.value = value
        self.threshold = threshold
        super().__init__(
            f"Rollback triggered: {trigger} = {value:.4f} "
            f"(threshold: {threshold:.4f})"
        )


class ConfigurationError(LLMOpsError):
    """Invalid configuration detected."""


class ModelNotAvailableError(LLMOpsError):
    """The requested model is not available or cannot be loaded."""

    def __init__(self, model: str, reason: str = "") -> None:
        self.model = model
        super().__init__(f"Model {model!r} not available: {reason}")

