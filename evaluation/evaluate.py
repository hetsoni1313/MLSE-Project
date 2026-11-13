"""Main evaluator — orchestrates evaluation across models and datasets."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from evaluation.metrics import (
    compute_accuracy,
    compute_confusion_counts,
    compute_invalid_rate,
    compute_latency_stats,
    compute_macro_f1,
    compute_per_class_accuracy,
)
from llmops_governance.core.constants import BANKING77_LABEL_SET
from llmops_governance.schemas.metrics import EvaluationResult


def _get_git_commit() -> str:
    """Get current git commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


class Evaluator:
    """Evaluates model predictions against ground truth.

    Can evaluate from:
    - Saved prediction files (JSON)
    - Direct prediction lists
    """

    def __init__(self, model_name: str = "unknown") -> None:
        self.model_name = model_name

    def evaluate_predictions(
        self,
        predictions: list[str],
        ground_truth: list[str],
        latencies: list[float] | None = None,
        costs: list[float] | None = None,
        dataset_hash: str = "",
        errors: list[bool] | None = None,
    ) -> EvaluationResult:
        """Evaluate predictions against ground truth."""
        accuracy = compute_accuracy(predictions, ground_truth)
        macro_f1 = compute_macro_f1(predictions, ground_truth)
        invalid_rate = compute_invalid_rate(predictions, BANKING77_LABEL_SET)

        lat_stats = compute_latency_stats(latencies or [])
        per_class = compute_per_class_accuracy(predictions, ground_truth)

        total = len(predictions)
        avg_cost = sum(costs) / len(costs) if costs else 0.0
        error_rate = sum(errors) / len(errors) if errors else 0.0

        throughput = 0.0
        if latencies and sum(latencies) > 0:
            total_seconds = sum(latencies) / 1000
            throughput = total / total_seconds

        return EvaluationResult(
            model_name=self.model_name,
            dataset_hash=dataset_hash,
            accuracy=accuracy,
            macro_f1=macro_f1,
            invalid_rate=invalid_rate,
            mean_latency_ms=lat_stats["mean"],
            p50_latency_ms=lat_stats["p50"],
            p95_latency_ms=lat_stats["p95"],
            p99_latency_ms=lat_stats["p99"],
            cost_per_query=avg_cost,
            cost_per_1k_queries=avg_cost * 1000,
            total_requests=total,
            error_rate=error_rate,
            throughput_qps=throughput,
            timestamp=datetime.now(timezone.utc),
            git_commit=_get_git_commit(),
            per_class_accuracy={k: v["accuracy"] for k, v in per_class.items()},
        )

    def evaluate_from_file(self, predictions_path: str) -> EvaluationResult:
        """Evaluate from a saved predictions JSON file."""
        with open(predictions_path) as f:
            data = json.load(f)

        predictions = [d["prediction"] for d in data["predictions"]]
        ground_truth = [d["ground_truth"] for d in data["predictions"]]
        latencies = [d.get("latency_ms", 0.0) for d in data["predictions"]]
        costs = [d.get("cost", 0.0) for d in data["predictions"]]
        errors = [d.get("error", False) for d in data["predictions"]]

        return self.evaluate_predictions(
            predictions=predictions,
            ground_truth=ground_truth,
            latencies=latencies,
            costs=costs,
            dataset_hash=data.get("dataset_hash", ""),
            errors=errors,
        )

    def save_report(
        self,
        result: EvaluationResult,
        output_path: str,
    ) -> None:
        """Save evaluation report as JSON."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result.model_dump(mode="json"), f, indent=2, default=str)

    def compare_models(
        self,
        baseline_result: EvaluationResult,
        local_result: EvaluationResult,
    ) -> dict:
        """Compare two evaluation results side by side."""
        return {
            "baseline": {
                "model": baseline_result.model_name,
                "accuracy": baseline_result.accuracy,
                "macro_f1": baseline_result.macro_f1,
                "p95_latency_ms": baseline_result.p95_latency_ms,
                "cost_per_1k": baseline_result.cost_per_1k_queries,
                "invalid_rate": baseline_result.invalid_rate,
            },
            "local": {
                "model": local_result.model_name,
                "accuracy": local_result.accuracy,
                "macro_f1": local_result.macro_f1,
                "p95_latency_ms": local_result.p95_latency_ms,
                "cost_per_1k": local_result.cost_per_1k_queries,
                "invalid_rate": local_result.invalid_rate,
            },
            "delta": {
                "accuracy": local_result.accuracy - baseline_result.accuracy,
                "macro_f1": local_result.macro_f1 - baseline_result.macro_f1,
                "latency_reduction_pct": (
                    (baseline_result.p95_latency_ms - local_result.p95_latency_ms)
                    / baseline_result.p95_latency_ms * 100
                    if baseline_result.p95_latency_ms > 0 else 0
                ),
                "cost_savings_pct": (
                    (baseline_result.cost_per_1k_queries - local_result.cost_per_1k_queries)
                    / baseline_result.cost_per_1k_queries * 100
                    if baseline_result.cost_per_1k_queries > 0 else 0
                ),
            },
        }

