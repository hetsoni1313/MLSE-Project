"""Baseline commercial API backend for Banking77 classification.

Supports OpenAI (GPT-4o-mini) as the default provider.
Falls back to a clearly-labeled MockBaselineBackend when no API key is configured.
"""

from __future__ import annotations

import os
import time
from typing import Any, ClassVar

import httpx

from gateway.backends import ModelBackend, PredictionResult
from llmops_governance.core.constants import (
    BANKING77_LABELS,
    FEW_SHOT_EXAMPLES,
)
from llmops_governance.logging.setup import get_logger
from llmops_governance.utils.validation import normalize_label, validate_label

logger = get_logger(__name__)

# ── Prompt template ───────────────────────────────────────────────────────
_SYSTEM_PROMPT = (
    "You are a banking customer intent classifier. Given a customer message, "
    "classify it into exactly one of the following 77 intent categories.\n\n"
    "Respond with ONLY the intent label, nothing else. No explanation, no "
    "punctuation, no prefix.\n\nIntent categories:\n{labels}"
)

_LABEL_LIST = "\n".join(f"- {label}" for label in BANKING77_LABELS)


def _build_messages(message: str) -> list[dict[str, str]]:
    """Build the chat messages with few-shot examples."""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _SYSTEM_PROMPT.format(labels=_LABEL_LIST)},
    ]
    for ex in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": ex["message"]})
        messages.append({"role": "assistant", "content": ex["intent"]})
    messages.append({"role": "user", "content": message})
    return messages


class BaselineAPIBackend(ModelBackend):
    """OpenAI-compatible commercial API backend."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout_ms: int = 30000,
    ) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._model = model
        self._base_url = base_url
        self._timeout_ms = timeout_ms
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return f"baseline-{self._model}"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(self._timeout_ms / 1000),
            )
        return self._client

    async def predict(self, message: str) -> PredictionResult:
        """Classify a message using the commercial API."""
        if not self._api_key:
            logger.warning("no_api_key_configured", backend="baseline")
            mock = MockBaselineBackend()
            return await mock.predict(message)

        start = time.perf_counter()
        try:
            client = await self._get_client()
            response = await client.post(
                "/chat/completions",
                json={
                    "model": self._model,
                    "messages": _build_messages(message),
                    "max_tokens": 30,
                    "temperature": 0.0,
                },
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            elapsed = (time.perf_counter() - start) * 1000

            raw = data["choices"][0]["message"]["content"].strip()
            normalized = normalize_label(raw)
            valid = validate_label(normalized)

            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

        except httpx.TimeoutException:
            elapsed = (time.perf_counter() - start) * 1000
            logger.exception("baseline_timeout", latency_ms=elapsed)
            return PredictionResult(
                error="Baseline API timeout",
                latency_ms=elapsed,
                model_name=self._model,
                valid_output=False,
            )
        except httpx.HTTPStatusError as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.exception("baseline_http_error", status=e.response.status_code)
            return PredictionResult(
                error=f"HTTP {e.response.status_code}",
                latency_ms=elapsed,
                model_name=self._model,
                valid_output=False,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.exception("baseline_error", error=str(e))
            return PredictionResult(
                error=str(e),
                latency_ms=elapsed,
                model_name=self._model,
                valid_output=False,
            )
        else:
            return PredictionResult(
                prediction=normalized,
                latency_ms=elapsed,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model_name=self._model,
                valid_output=valid,
                raw_response=raw,
            )

    async def health_check(self) -> bool:
        """Check if the API is reachable."""
        if not self._api_key:
            return False
        try:
            client = await self._get_client()
            response = await client.get("/models")
        except Exception:
            return False
        else:
            return response.status_code == 200  # noqa: PLR2004

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


class MockBaselineBackend(ModelBackend):
    """Deterministic mock backend for testing without an API key.

    This is CLEARLY LABELED as a mock — results are not from a real commercial API.
    Uses a small deterministic mapping for reproducible testing.
    """

    _MOCK_PREDICTIONS: ClassVar[dict[str, str]] = {
        "card": "get_physical_card",
        "pin": "change_pin",
        "transfer": "pending_transfer",
        "payment": "card_payment_not_recognised",
        "stolen": "lost_or_stolen_card",
        "balance": "balance_not_updated_after_bank_transfer",
        "exchange": "exchange_rate",
        "top up": "topping_up_by_card",
        "refund": "request_refund",
        "account": "terminate_account",
        "verify": "verify_my_identity",
        "fee": "card_payment_fee_charged",
        "atm": "atm_support",
        "contactless": "contactless_not_working",
        "cancel": "cancel_transfer",
    }

    @property
    def name(self) -> str:
        return "mock-baseline (NOT REAL API)"

    async def predict(self, message: str) -> PredictionResult:
        """Return a deterministic mock prediction."""
        start = time.perf_counter()
        msg_lower = message.lower()
        prediction = "activate_my_card"  # default
        for keyword, label in self._MOCK_PREDICTIONS.items():
            if keyword in msg_lower:
                prediction = label
                break

        elapsed = (time.perf_counter() - start) * 1000 + 50  # simulate ~50ms
        return PredictionResult(
            prediction=prediction,
            latency_ms=elapsed,
            input_tokens=len(message.split()) * 2,  # rough estimate
            output_tokens=5,
            model_name="mock-baseline",
            valid_output=True,
            raw_response=prediction,
            metadata={"is_mock": True, "warning": "This is a mock, not a real API result"},
        )

    async def health_check(self) -> bool:
        return True
