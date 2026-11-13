"""FastAPI Gateway — The heart of the LLMOps Governance Platform.

Initializes all backends, routing engine, resilience components,
and provides the API for intent classification with intelligent routing.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gateway.api.admin import router as admin_router
from gateway.api.classify import router as classify_router
from gateway.api.health import router as health_router
from gateway.api.metrics_api import router as metrics_router
from gateway.backends.baseline import BaselineAPIBackend, MockBaselineBackend
from gateway.backends.fault_injection import FaultInjectionBackend
from gateway.backends.local import LocalModelBackend
from gateway.resilience.circuit_breaker import CircuitBreaker
from gateway.resilience.fallback import FallbackHandler
from gateway.resilience.rollback import RollbackMonitor
from gateway.routing.config import RoutingConfig
from gateway.routing.engine import RoutingEngine
from gateway.services import RequestLogger
from llmops_governance.config.settings import Settings, get_settings
from llmops_governance.logging.setup import configure_logging, get_logger
from llmops_governance.metrics.collector import MetricsCollector
from llmops_governance.metrics.database import DatabaseManager

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — initialize and cleanup resources."""
    settings = get_settings()
    configure_logging(
        log_level=settings.log_level,
        json_output=settings.environment != "development",
    )

    logger.info("gateway_starting", environment=settings.environment)

    # ── Database ──────────────────────────────────────────────────────
    db_manager = DatabaseManager(settings.database.url)
    await db_manager.initialize()
    app.state.db_manager = db_manager

    # ── Settings ──────────────────────────────────────────────────────
    app.state.settings = settings

    # ── Backends ──────────────────────────────────────────────────────
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key:
        baseline = BaselineAPIBackend(api_key=api_key, model=settings.pricing.model)
    else:
        logger.warning("no_api_key_using_mock_baseline")
        baseline = MockBaselineBackend()
    app.state.baseline_backend = baseline

    local = LocalModelBackend(
        server_url=settings.model.llama_server_url,
        timeout_ms=settings.model.local_model_timeout_ms,
    )
    app.state.local_backend = local

    # Fault injection wrapper (for local backend)
    fault_injection_enabled = os.getenv("FAULT_INJECTION_ENABLED", "false").lower() == "true"
    fault_backend = FaultInjectionBackend(local)
    if fault_injection_enabled:
        app.state.fault_backend = fault_backend
        effective_local = fault_backend
    else:
        app.state.fault_backend = None
        effective_local = local

    # ── Routing ───────────────────────────────────────────────────────
    routing_config = RoutingConfig(
        mode=settings.routing.mode,
        baseline_percentage=settings.routing.baseline_percentage,
        local_percentage=settings.routing.local_percentage,
        sticky_enabled=settings.routing.sticky_enabled,
        shadow_enabled=settings.routing.shadow_enabled,
    )
    routing_engine = RoutingEngine(routing_config)
    app.state.routing_engine = routing_engine

    # ── Resilience ────────────────────────────────────────────────────
    fallback_handler = FallbackHandler(effective_local, baseline)
    app.state.fallback_handler = fallback_handler

    circuit_breaker = CircuitBreaker()
    app.state.circuit_breaker = circuit_breaker

    # ── Metrics ───────────────────────────────────────────────────────
    metrics_collector = MetricsCollector()
    app.state.metrics_collector = metrics_collector

    # ── Request Logger ────────────────────────────────────────────────
    request_logger = RequestLogger(db_manager)
    await request_logger.start()
    app.state.request_logger = request_logger

    # ── Rollback Monitor ──────────────────────────────────────────────
    rollback_monitor = RollbackMonitor(
        routing_engine=routing_engine,
        db_manager=db_manager,
        evaluation_window=settings.rollback.evaluation_window,
        min_labelled_samples=settings.rollback.min_labelled_samples,
        min_accuracy=settings.rollback.min_accuracy,
        max_error_rate=settings.rollback.max_error_rate,
        max_p95_latency_ms=settings.rollback.max_p95_latency_ms,
        check_interval_seconds=settings.rollback.check_interval_seconds,
    )
    if settings.rollback.enabled:
        await rollback_monitor.start()
    app.state.rollback_monitor = rollback_monitor

    logger.info("gateway_ready", routing_mode=routing_config.mode)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────
    logger.info("gateway_shutting_down")
    await rollback_monitor.stop()
    await request_logger.stop()
    if hasattr(baseline, "close"):
        await baseline.close()
    if hasattr(local, "close"):
        await local.close()
    await db_manager.close()
    logger.info("gateway_shutdown_complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="LLMOps Cost & Latency Governance Platform",
        description=(
            "Intelligent gateway for routing Banking77 intent classification "
            "between commercial API and fine-tuned local model, with automatic "
            "fallback, rollback, and cost monitoring."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(classify_router)
    app.include_router(health_router)
    app.include_router(admin_router)
    app.include_router(metrics_router)

    return app


# Application instance
app = create_app()

