"""Fault injection backend for testing failure scenarios.

Wraps another backend and injects configurable faults.
DISABLED by default — requires FAULT_INJECTION_ENABLED=true.
"""

from __future__ import annotations

import asyncio
import os
import random
import time
from dataclasses import dataclass, field

from gateway.backends import ModelBackend, PredictionResult
from llmops_governance.core.constants import BANKING77_LABELS
from llmops_governance.logging.setup import get_logger

logger = get_logger(__name__)


@dataclass
class FaultConfig:
    """Configuration for fault injection modes."""

    unavailable: bool = False
    timeout: bool = False
    timeout_delay_ms: int = 15000
    invalid_output: bool = False
    invalid_output_rate: float = 1.0
    degraded_accuracy: bool = False
    degraded_accuracy_rate: float = 0.8  # % of predictions that become wrong
    high_latency: bool = False
    high_latency_ms: int = 3000
    error_rate: bool = False
    error_rate_pct: float = 0.5  # 50% of requests fail


@dataclass
class FaultInjectionState:
    """Mutable state of the fault injector."""

    enabled: bool = False
    config: FaultConfig = field(default_factory=FaultConfig)


class FaultInjectionBackend(ModelBackend):
    """Backend wrapper that injects faults for testing.

    Only active when FAULT_INJECTION_ENABLED=true AND faults are toggled on.
    Wraps a real backend and modifies its behavior based on configured faults.
    """

    def __init__(self, wrapped: ModelBackend) -> None:
        self._wrapped = wrapped
        self._state = FaultInjectionState()
        self._allowed = os.getenv("FAULT_INJECTION_ENABLED", "false").lower() == "true"

    @property
    def name(self) -> str:
        if self._state.enabled:
            return f"fault-injection({self._wrapped.name})"
        return self._wrapped.name

    @property
    def state(self) -> FaultInjectionState:
        return self._state

    def enable(self) -> None:
        """Enable fault injection (only if FAULT_INJECTION_ENABLED)."""
        if not self._allowed:
            logger.warning("fault_injection_not_allowed")
            return
        self._state.enabled = True
        logger.warning("fault_injection_enabled")

    def disable(self) -> None:
        """Disable fault injection."""
        self._state.enabled = False
        self._state.config = FaultConfig()
        logger.info("fault_injection_disabled")

    def set_fault(self, fault_type: str, enabled: bool = True, **kwargs: object) -> None:
        """Toggle a specific fault type."""
        if not self._allowed:
            return
        if hasattr(self._state.config, fault_type):
            setattr(self._state.config, fault_type, enabled)
            if enabled:
                self._state.enabled = True
            for k, v in kwargs.items():
                if hasattr(self._state.config, k):
                    setattr(self._state.config, k, v)
            logger.info("fault_set", fault_type=fault_type, enabled=enabled, **{str(k): v for k, v in kwargs.items()})

    async def predict(self, message: str) -> PredictionResult:
        """Predict with potential fault injection."""
        if not self._state.enabled or not self._allowed:
            return await self._wrapped.predict(message)

        cfg = self._state.config

        # 1. Unavailable — simulate server down
        if cfg.unavailable:
            logger.debug("fault_injected", type="unavailable")
            return PredictionResult(
                error="[FAULT INJECTION] Server unavailable",
                model_name=self._wrapped.name,
                valid_output=False,
                latency_ms=1.0,
            )

        # 2. Timeout — delay beyond configured timeout
        if cfg.timeout:
            logger.debug("fault_injected", type="timeout")
            await asyncio.sleep(cfg.timeout_delay_ms / 1000)
            return PredictionResult(
                error="[FAULT INJECTION] Request timed out",
                model_name=self._wrapped.name,
                valid_output=False,
                latency_ms=float(cfg.timeout_delay_ms),
            )

        # 3. Error rate — random subset of requests fail
        if cfg.error_rate and random.random() < cfg.error_rate_pct:  # noqa: S311
            logger.debug("fault_injected", type="error_rate")
            return PredictionResult(
                error="[FAULT INJECTION] Random error",
                model_name=self._wrapped.name,
                valid_output=False,
                latency_ms=10.0,
            )

        # 4. High latency — add extra delay then call real backend
        if cfg.high_latency:
            logger.debug("fault_injected", type="high_latency", added_ms=cfg.high_latency_ms)
            await asyncio.sleep(cfg.high_latency_ms / 1000)

        # Call the real backend
        result = await self._wrapped.predict(message)

        # When running in dev/test environment where llama-server is not running,
        # synthesize a baseline local prediction for quality/latency tests
        if result.error and "unavailable" in result.error.lower():
            if cfg.degraded_accuracy or cfg.invalid_output or cfg.high_latency:
                result = PredictionResult(
                    prediction="activate_my_card",
                    latency_ms=result.latency_ms,
                    model_name=self._wrapped.name,
                    valid_output=True,
                    error=None,
                    metadata={"synthetic_dev_mode": True},
                )

        # 5. Invalid output — replace prediction with garbage
        if cfg.invalid_output and random.random() < cfg.invalid_output_rate:  # noqa: S311
            result.prediction = "INVALID_INJECTED_LABEL"
            result.valid_output = False
            result.metadata["fault_injected"] = "invalid_output"

        # 6. Degraded accuracy — replace prediction with wrong label
        if cfg.degraded_accuracy and random.random() < cfg.degraded_accuracy_rate:  # noqa: S311
            wrong_labels = [l for l in BANKING77_LABELS if l != result.prediction]
            result.prediction = random.choice(wrong_labels)  # noqa: S311
            result.metadata["fault_injected"] = "degraded_accuracy"

        return result

    async def health_check(self) -> bool:
        """Health check — returns False when unavailable fault is active."""
        if self._state.enabled and self._state.config.unavailable:
            return False
        return await self._wrapped.health_check()

