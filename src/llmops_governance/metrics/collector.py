"""In-memory metrics collector for real-time gateway monitoring."""

from __future__ import annotations

import statistics
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class MetricsSummary:
    """Snapshot of current gateway metrics."""

    total_requests: int = 0
    baseline_requests: int = 0
    local_requests: int = 0
    shadow_requests: int = 0
    fallback_count: int = 0
    error_count: int = 0
    correct_predictions: int = 0
    labelled_predictions: int = 0
    accuracy: float = 0.0
    mean_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    requests_per_second: float = 0.0
    route_distribution: dict[str, int] = field(default_factory=dict)


class MetricsCollector:
    """Thread-safe in-memory metrics collector for the gateway.

    Collects per-request measurements and provides summary statistics.
    Designed for fast, lock-minimal operation on the hot path.
    """

    def __init__(self, window_size: int = 10000) -> None:
        self._window_size = window_size
        self._lock = threading.Lock()
        self._latencies: list[float] = []
        self._route_counts: dict[str, int] = defaultdict(int)
        self._total: int = 0
        self._errors: int = 0
        self._fallbacks: int = 0
        self._correct: int = 0
        self._labelled: int = 0
        self._start_time: float = time.monotonic()

    def record_request(
        self,
        route: str,
        latency_ms: float,
        error: bool = False,
        fallback: bool = False,
        correct: bool | None = None,
    ) -> None:
        """Record a single request's metrics."""
        with self._lock:
            self._total += 1
            self._route_counts[route] += 1
            if error:
                self._errors += 1
            if fallback:
                self._fallbacks += 1
            if correct is not None:
                self._labelled += 1
                if correct:
                    self._correct += 1

            self._latencies.append(latency_ms)
            if len(self._latencies) > self._window_size:
                self._latencies = self._latencies[-self._window_size :]

    def get_summary(self) -> MetricsSummary:
        """Return a snapshot of current metrics."""
        with self._lock:
            elapsed = max(time.monotonic() - self._start_time, 0.001)
            latencies = self._latencies.copy()
            accuracy = self._correct / self._labelled if self._labelled > 0 else 0.0
            sorted_lats = sorted(latencies) if latencies else [0.0]

            return MetricsSummary(
                total_requests=self._total,
                baseline_requests=self._route_counts.get("baseline", 0),
                local_requests=self._route_counts.get("local", 0),
                shadow_requests=self._route_counts.get("shadow", 0),
                fallback_count=self._fallbacks,
                error_count=self._errors,
                correct_predictions=self._correct,
                labelled_predictions=self._labelled,
                accuracy=accuracy,
                mean_latency_ms=(statistics.mean(sorted_lats) if sorted_lats else 0.0),
                p50_latency_ms=_percentile(sorted_lats, 0.50),
                p95_latency_ms=_percentile(sorted_lats, 0.95),
                p99_latency_ms=_percentile(sorted_lats, 0.99),
                requests_per_second=self._total / elapsed,
                route_distribution=dict(self._route_counts),
            )

    def reset(self) -> None:
        """Reset all counters."""
        with self._lock:
            self._latencies.clear()
            self._route_counts.clear()
            self._total = 0
            self._errors = 0
            self._fallbacks = 0
            self._correct = 0
            self._labelled = 0
            self._start_time = time.monotonic()


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Compute percentile from sorted values."""
    if not sorted_values:
        return 0.0
    idx = int(len(sorted_values) * pct)
    idx = min(idx, len(sorted_values) - 1)
    return sorted_values[idx]
