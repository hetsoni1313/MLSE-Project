"""Local model backend connecting to llama.cpp server's OpenAI-compatible API."""

from __future__ import annotations

import os
import time

import httpx

from gateway.backends import ModelBackend, PredictionResult
from llmops_governance.core.constants import BANKING77_LABELS, FEW_SHOT_EXAMPLES
from llmops_governance.logging.setup import get_logger
from llmops_governance.utils.validation import normalize_label, validate_label

logger = get_logger(__name__)

_LABEL_LIST = "\n".join(f"- {label}" for label in BANKING77_LABELS)

_SYSTEM_PROMPT = f"""You are a banking customer intent classifier. Classify the customer message into exactly one of the following 77 intent categories.
Respond with ONLY the intent label, nothing else.

Intent categories:
{_LABEL_LIST}"""


def _build_messages(message: str) -> list[dict[str, str]]:
    """Build chat messages with few-shot examples for the local model."""
    messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
    for ex in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": ex["message"]})
        messages.append({"role": "assistant", "content": ex["intent"]})
    messages.append({"role": "user", "content": message})
    return messages


class LocalModelBackend(ModelBackend):
    """Backend connecting to a llama.cpp server with OpenAI-compatible API."""

    def __init__(
        self,
        server_url: str | None = None,
        timeout_ms: int = 10000,
        model_name: str = "local-gguf",
    ) -> None:
        self._server_url = server_url or os.getenv(
            "LLAMA_SERVER_URL", "http://localhost:8081"
        )
        self._timeout_ms = timeout_ms
        self._model_name = model_name
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return f"local-{self._model_name}"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._server_url,
                timeout=httpx.Timeout(self._timeout_ms / 1000),
            )
        return self._client

    async def predict(self, message: str) -> PredictionResult:
        """Classify a message using the local model."""
        start = time.perf_counter()
        try:
            client = await self._get_client()
            response = await client.post(
                "/v1/chat/completions",
                json={
                    "model": self._model_name,
                    "messages": _build_messages(message),
                    "max_tokens": 30,
                    "temperature": 0.0,
                    "stop": ["\n"],
                },
            )
            response.raise_for_status()
            data = response.json()
            elapsed = (time.perf_counter() - start) * 1000

            raw = data["choices"][0]["message"]["content"].strip()
            normalized = normalize_label(raw)
            valid = validate_label(normalized)

            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

            # Calculate tokens per second
            tps = None
            if output_tokens > 0 and elapsed > 0:
                tps = output_tokens / (elapsed / 1000)

            return PredictionResult(
                prediction=normalized,
                latency_ms=elapsed,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model_name=self._model_name,
                valid_output=valid,
                raw_response=raw,
                tokens_per_second=tps,
            )

        except httpx.TimeoutException:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("local_model_timeout", latency_ms=elapsed)
            return PredictionResult(
                error="Local model timeout",
                latency_ms=elapsed,
                model_name=self._model_name,
                valid_output=False,
            )
        except httpx.ConnectError:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("local_model_unavailable", server=self._server_url)
            return PredictionResult(
                error="Local model server unavailable",
                latency_ms=elapsed,
                model_name=self._model_name,
                valid_output=False,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("local_model_error", error=str(e))
            return PredictionResult(
                error=str(e),
                latency_ms=elapsed,
                model_name=self._model_name,
                valid_output=False,
            )

    async def health_check(self) -> bool:
        """Check if the llama.cpp server is healthy."""
        try:
            client = await self._get_client()
            response = await client.get("/health")
            return response.status_code == 200  # noqa: PLR2004
        except Exception:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

