"""Prediction runner — async batch prediction against an endpoint."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from llmops_governance.logging.setup import get_logger

logger = get_logger(__name__)


class PredictionRunner:
    """Run predictions against a gateway endpoint for evaluation."""

    def __init__(
        self,
        gateway_url: str = "http://localhost:8000",
        concurrency: int = 4,
        timeout_ms: int = 30000,
    ) -> None:
        self._gateway_url = gateway_url
        self._concurrency = concurrency
        self._timeout = timeout_ms / 1000

    async def run_predictions(
        self,
        dataset: list[dict],
        experiment_id: str = "",
    ) -> list[dict]:
        """Run predictions for a dataset against the gateway.

        Args:
            dataset: List of {"text": ..., "label": ...} entries
            experiment_id: Experiment identifier for logging

        Returns:
            List of prediction result dicts
        """
        semaphore = asyncio.Semaphore(self._concurrency)
        async with httpx.AsyncClient(timeout=httpx.Timeout(self._timeout)) as client:
            tasks = [
                self._predict_one(client, semaphore, entry, experiment_id) for entry in dataset
            ]
            return await asyncio.gather(*tasks)

    async def _predict_one(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        entry: dict,
        experiment_id: str,
    ) -> dict:
        """Make a single prediction request."""
        async with semaphore:
            start = time.perf_counter()
            try:
                response = await client.post(
                    f"{self._gateway_url}/classify",
                    json={
                        "message": entry["text"],
                        "ground_truth": entry.get("label"),
                        "request_id": f"{experiment_id}-{entry.get('idx', 0)}",
                    },
                )
                elapsed = (time.perf_counter() - start) * 1000
                data = response.json()
                return {
                    "text": entry["text"],
                    "ground_truth": entry.get("label", ""),
                    "prediction": data.get("prediction", ""),
                    "route": data.get("route", ""),
                    "latency_ms": elapsed,
                    "model_name": data.get("model_name", ""),
                    "valid_output": data.get("valid_output", False),
                    "fallback_used": data.get("fallback_used", False),
                    "error": data.get("error"),
                    "cost": 0.0,
                }
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                return {
                    "text": entry["text"],
                    "ground_truth": entry.get("label", ""),
                    "prediction": "",
                    "route": "error",
                    "latency_ms": elapsed,
                    "error": str(e),
                    "valid_output": False,
                    "cost": 0.0,
                }

    def save_predictions(
        self,
        predictions: list[dict],
        output_path: str,
        dataset_hash: str = "",
        metadata: dict | None = None,
    ) -> None:
        """Save predictions to a JSON file."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        output = {
            "dataset_hash": dataset_hash,
            "timestamp": datetime.now(UTC).isoformat(),
            "total_predictions": len(predictions),
            "metadata": metadata or {},
            "predictions": predictions,
        }
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)
        logger.info("predictions_saved", path=output_path, count=len(predictions))
