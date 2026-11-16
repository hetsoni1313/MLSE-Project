"""POST /classify — Core intent classification endpoint."""

from __future__ import annotations

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Request

from gateway.backends import PredictionResult
from gateway.routing.engine import Route
from llmops_governance.logging.setup import get_logger
from llmops_governance.schemas.requests import ClassifyRequest, ClassifyResponse

logger = get_logger(__name__)
router = APIRouter(tags=["Classification"])


@router.post("/classify", response_model=ClassifyResponse)
async def classify(req: ClassifyRequest, request: Request) -> ClassifyResponse:
    """Classify a customer banking message into one of 77 intent categories.

    The routing engine determines which backend handles the request.
    Fallback and shadow behaviors are handled automatically.
    """
    app_state = request.app.state
    routing_engine = app_state.routing_engine
    fallback_handler = app_state.fallback_handler
    metrics_collector = app_state.metrics_collector
    request_logger = app_state.request_logger

    start = time.perf_counter()
    route = routing_engine.determine_route(
        user_id=req.user_id,
        request_id=req.request_id,
    )

    result: PredictionResult
    fallback_used = False
    fallback_reason: str | None = None
    shadow_prediction: str | None = None

    try:
        if route == Route.SHADOW:
            # Shadow mode: return baseline, run local silently
            baseline_result, local_result = await fallback_handler.predict_shadow(req.message)
            result = baseline_result
            if local_result:
                shadow_prediction = local_result.prediction
            actual_route = "baseline"

        elif route == Route.LOCAL:
            # Try local with fallback
            result, fallback_used, fallback_reason = await fallback_handler.predict_with_fallback(
                req.message
            )
            actual_route = "baseline" if fallback_used else "local"

        else:
            # Baseline only
            result = await app_state.baseline_backend.predict(req.message)
            actual_route = "baseline"

    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        logger.exception("classify_error", error=str(e))
        return ClassifyResponse(
            request_id=req.request_id or "",
            prediction="",
            route="error",
            latency_ms=elapsed,
            model_name="unknown",
            valid_output=False,
            error=str(e),
        )

    elapsed = (time.perf_counter() - start) * 1000

    # Determine correctness if ground truth provided
    correct: bool | None = None
    if req.ground_truth:
        correct = result.prediction == req.ground_truth

    # Calculate cost estimate
    estimated_cost = _estimate_cost(
        result.input_tokens,
        result.output_tokens,
        actual_route,
        app_state,
    )

    # Log the request (non-blocking)
    log_data = {
        "timestamp": datetime.now(UTC),
        "request_id": req.request_id or "",
        "user_id": req.user_id,
        "route": actual_route,
        "model_name": result.model_name,
        "input_text": req.message,
        "predicted_label": result.prediction,
        "ground_truth_label": req.ground_truth,
        "correct": correct,
        "valid_output": result.valid_output,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "latency_ms": elapsed,
        "tokens_per_second": result.tokens_per_second,
        "estimated_cost": estimated_cost,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "error": result.error,
        "experiment_mode": routing_engine.config.mode,
    }

    # Log shadow prediction too
    if shadow_prediction is not None:
        log_data["experiment_mode"] = "shadow"

    request_logger.log_request(log_data)

    # Update in-memory metrics
    metrics_collector.record_request(
        route=actual_route,
        latency_ms=elapsed,
        error=result.error is not None,
        fallback=fallback_used,
        correct=correct,
    )

    return ClassifyResponse(
        request_id=req.request_id or "",
        prediction=result.prediction,
        route=actual_route,
        latency_ms=round(elapsed, 2),
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        model_name=result.model_name,
        valid_output=result.valid_output,
        error=result.error,
        shadow_prediction=shadow_prediction,
    )


def _estimate_cost(
    input_tokens: int,
    output_tokens: int,
    route: str,
    app_state: object,
) -> float:
    """Estimate cost based on route and token usage."""
    if route == "baseline":
        # Use pricing config
        try:
            pricing = app_state.settings.pricing
            input_cost = input_tokens * (pricing.input_price_per_mtok / 1_000_000)
            output_cost = output_tokens * (pricing.output_price_per_mtok / 1_000_000)
            return input_cost + output_cost
        except Exception:
            return 0.0
    else:
        # Local model — cost is based on machine cost per query
        # Default: ~$0.0001 per query for local hardware
        return 0.0001
