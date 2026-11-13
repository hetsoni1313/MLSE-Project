"""Abstract model backend interface and prediction result."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PredictionResult:
    """Structured result from a model backend prediction."""

    prediction: str = ""
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    model_name: str = ""
    valid_output: bool = True
    error: str | None = None
    raw_response: str = ""
    tokens_per_second: float | None = None
    metadata: dict = field(default_factory=dict)


class ModelBackend(ABC):
    """Abstract interface for inference backends.

    All model backends (commercial API, local model, fault injection)
    must implement this interface to work with the gateway.
    """

    @abstractmethod
    async def predict(self, message: str) -> PredictionResult:
        """Run inference on a single customer message.

        Args:
            message: Customer banking message to classify.

        Returns:
            PredictionResult with prediction, latency, token usage, etc.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the backend is healthy and ready to serve.

        Returns:
            True if the backend can accept requests.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable backend name."""

