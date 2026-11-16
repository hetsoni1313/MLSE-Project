"""Model comparison utility."""

from __future__ import annotations

from llmops_governance.schemas.metrics import EvaluationResult


class ModelComparison:
    """Compare evaluation results and check promotion criteria."""

    def __init__(
        self,
        min_accuracy: float = 0.80,
        max_p95_latency_ms: float = 5000.0,
        max_invalid_rate: float = 0.10,
    ) -> None:
        self.min_accuracy = min_accuracy
        self.max_p95_latency_ms = max_p95_latency_ms
        self.max_invalid_rate = max_invalid_rate

    def check_promotion(self, result: EvaluationResult) -> dict:
        """Check if a model meets promotion criteria."""
        checks = {
            "accuracy": {
                "passed": result.accuracy >= self.min_accuracy,
                "value": result.accuracy,
                "threshold": self.min_accuracy,
            },
            "p95_latency": {
                "passed": result.p95_latency_ms <= self.max_p95_latency_ms,
                "value": result.p95_latency_ms,
                "threshold": self.max_p95_latency_ms,
            },
            "invalid_rate": {
                "passed": result.invalid_rate <= self.max_invalid_rate,
                "value": result.invalid_rate,
                "threshold": self.max_invalid_rate,
            },
        }
        all_passed = all(c["passed"] for c in checks.values())
        return {
            "model": result.model_name,
            "promoted": all_passed,
            "checks": checks,
        }

    def compare(
        self,
        baseline: EvaluationResult,
        candidate: EvaluationResult,
    ) -> dict:
        """Side-by-side comparison of two models."""
        return {
            "baseline": {
                "model": baseline.model_name,
                "accuracy": baseline.accuracy,
                "macro_f1": baseline.macro_f1,
                "p95_latency_ms": baseline.p95_latency_ms,
                "cost_per_1k": baseline.cost_per_1k_queries,
            },
            "candidate": {
                "model": candidate.model_name,
                "accuracy": candidate.accuracy,
                "macro_f1": candidate.macro_f1,
                "p95_latency_ms": candidate.p95_latency_ms,
                "cost_per_1k": candidate.cost_per_1k_queries,
            },
            "delta": {
                "accuracy": candidate.accuracy - baseline.accuracy,
                "cost_savings_pct": (
                    (baseline.cost_per_1k_queries - candidate.cost_per_1k_queries)
                    / baseline.cost_per_1k_queries
                    * 100
                )
                if baseline.cost_per_1k_queries > 0
                else 0,
            },
            "promotion": self.check_promotion(candidate),
        }
