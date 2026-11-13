"""Fallback handler — routes to baseline when local backend fails."""

from __future__ import annotations

import time

from gateway.backends import ModelBackend, PredictionResult
from llmops_governance.logging.setup import get_logger

logger = get_logger(__name__)


class FallbackHandler:
    """Wraps local backend calls with automatic fallback to baseline.

    When the local backend fails (timeout, error, unavailable),
    the request is transparently retried against the baseline backend.
    All fallback events are logged.
    """

    def __init__(
        self,
        local_backend: ModelBackend,
        baseline_backend: ModelBackend,
    ) -> None:
        self._local = local_backend
        self._baseline = baseline_backend
        self._fallback_count = 0

    @property
    def fallback_count(self) -> int:
        return self._fallback_count

    async def predict_with_fallback(
        self,
        message: str,
    ) -> tuple[PredictionResult, bool, str | None]:
        """Attempt local prediction with fallback to baseline.

        Returns:
            Tuple of (result, fallback_used, fallback_reason)
        """
        start = time.perf_counter()

        # Try local backend first
        local_result = await self._local.predict(message)

        if local_result.error is None and local_result.valid_output:
            return local_result, False, None

        # Local failed — fall back to baseline
        fallback_reason = local_result.error or "invalid_output"
        logger.warning(
            "fallback_triggered",
            reason=fallback_reason,
            local_latency_ms=local_result.latency_ms,
        )

        baseline_result = await self._baseline.predict(message)
        self._fallback_count += 1

        total_ms = (time.perf_counter() - start) * 1000
        baseline_result.latency_ms = total_ms
        baseline_result.metadata["fallback_from"] = self._local.name
        baseline_result.metadata["fallback_reason"] = fallback_reason

        return baseline_result, True, fallback_reason

    async def predict_shadow(
        self,
        message: str,
    ) -> tuple[PredictionResult, PredictionResult | None]:
        """Run baseline for client response, local silently for comparison.

        Returns:
            Tuple of (baseline_result, local_result_or_none)
        """
        # Always return baseline to client
        baseline_result = await self._baseline.predict(message)

        # Run local silently — never affects client response
        local_result: PredictionResult | None = None
        try:
            local_result = await self._local.predict(message)
        except Exception as e:
            logger.warning("shadow_local_failed", error=str(e))
            local_result = PredictionResult(
                error=str(e),
                model_name=self._local.name,
                valid_output=False,
            )

        return baseline_result, local_result

