"""GET /metrics — Returns current gateway metrics summary."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["Metrics"])


@router.get("/metrics")
async def get_metrics(request: Request) -> dict:
    """Return current gateway metrics from the in-memory collector."""
    collector = request.app.state.metrics_collector
    summary = collector.get_summary()
    return {
        "total_requests": summary.total_requests,
        "baseline_requests": summary.baseline_requests,
        "local_requests": summary.local_requests,
        "shadow_requests": summary.shadow_requests,
        "fallback_count": summary.fallback_count,
        "error_count": summary.error_count,
        "accuracy": round(summary.accuracy, 4),
        "labelled_predictions": summary.labelled_predictions,
        "mean_latency_ms": round(summary.mean_latency_ms, 2),
        "p50_latency_ms": round(summary.p50_latency_ms, 2),
        "p95_latency_ms": round(summary.p95_latency_ms, 2),
        "p99_latency_ms": round(summary.p99_latency_ms, 2),
        "requests_per_second": round(summary.requests_per_second, 2),
        "route_distribution": summary.route_distribution,
    }
