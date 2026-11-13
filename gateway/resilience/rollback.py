"""Automatic rollback monitor — evaluates local model performance and triggers rollback.

Runs as a background async task, periodically checking recent request metrics
against configured thresholds. Triggers routing rollback to 100% baseline
when performance degrades.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from gateway.routing.engine import RoutingEngine
from llmops_governance.logging.setup import get_logger
from llmops_governance.metrics.database import DatabaseManager
from llmops_governance.metrics.repository import (
    RequestLogRepository,
    RollbackRepository,
)

logger = get_logger(__name__)


class RollbackMonitor:
    """Background monitor that evaluates local model performance.

    Checks three conditions for rollback:
    1. Accuracy below threshold (requires sufficient ground-truth labels)
    2. Error rate above threshold
    3. p95 latency above threshold

    Safety features:
    - Won't trigger accuracy rollback with < min_labelled_samples labels
    - Prevents duplicate rollback events
    - Thread-safe config access via routing engine
    - Recovery only through explicit admin action
    """

    def __init__(
        self,
        routing_engine: RoutingEngine,
        db_manager: DatabaseManager,
        *,
        evaluation_window: int = 100,
        min_labelled_samples: int = 30,
        min_accuracy: float = 0.85,
        max_error_rate: float = 0.05,
        max_p95_latency_ms: float = 5000.0,
        check_interval_seconds: int = 30,
    ) -> None:
        self._routing = routing_engine
        self._db = db_manager
        self._window = evaluation_window
        self._min_labelled = min_labelled_samples
        self._min_accuracy = min_accuracy
        self._max_error_rate = max_error_rate
        self._max_p95_latency_ms = max_p95_latency_ms
        self._check_interval = check_interval_seconds
        self._task: asyncio.Task | None = None  # type: ignore[type-arg]
        self._running = False
        self._lock = asyncio.Lock()
        self._last_rollback_event_id: str | None = None

    async def start(self) -> None:
        """Start the background monitoring loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("rollback_monitor_started", interval_s=self._check_interval)

    async def stop(self) -> None:
        """Stop the monitoring loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("rollback_monitor_stopped")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await asyncio.sleep(self._check_interval)
                await self._evaluate()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("rollback_monitor_error", error=str(e))

    async def _evaluate(self) -> None:
        """Evaluate recent local model performance."""
        config = self._routing.config

        # Skip if already at 0% local or already rolled back
        if config.local_percentage == 0 or self._routing.is_rolled_back:
            return

        async with self._lock:
            async with self._db.get_session() as session:
                repo = RequestLogRepository(session)

                # Check error rate
                recent = await repo.get_recent_by_route("local", self._window)
                if len(recent) >= 10:  # Need at least 10 requests
                    error_count = sum(1 for r in recent if r.error is not None)
                    error_rate = error_count / len(recent)
                    if error_rate > self._max_error_rate:
                        await self._trigger_rollback(
                            session,
                            trigger="error_rate",
                            value=error_rate,
                            threshold=self._max_error_rate,
                        )
                        return

                # Check p95 latency
                if len(recent) >= 10:
                    latencies = sorted([r.latency_ms for r in recent])
                    p95_idx = min(int(len(latencies) * 0.95), len(latencies) - 1)
                    p95 = latencies[p95_idx]
                    if p95 > self._max_p95_latency_ms:
                        await self._trigger_rollback(
                            session,
                            trigger="p95_latency",
                            value=p95,
                            threshold=self._max_p95_latency_ms,
                        )
                        return

                # Check accuracy (only with sufficient ground truth)
                labelled = await repo.get_recent_with_ground_truth(
                    "local", self._window
                )
                if len(labelled) >= self._min_labelled:
                    correct = sum(1 for r in labelled if r.correct)
                    accuracy = correct / len(labelled)
                    if accuracy < self._min_accuracy:
                        await self._trigger_rollback(
                            session,
                            trigger="accuracy",
                            value=accuracy,
                            threshold=self._min_accuracy,
                        )

    async def _trigger_rollback(
        self,
        session: object,
        trigger: str,
        value: float,
        threshold: float,
    ) -> None:
        """Execute routing rollback and record the event."""
        config = self._routing.config

        # Prevent duplicate rollback
        if self._routing.is_rolled_back:
            return

        event_id = str(uuid.uuid4())
        self._routing.trigger_rollback()

        # Record rollback event
        from sqlalchemy.ext.asyncio import AsyncSession

        if isinstance(session, AsyncSession):
            rollback_repo = RollbackRepository(session)
            await rollback_repo.save({
                "event_id": event_id,
                "timestamp": datetime.now(timezone.utc),
                "trigger_type": trigger,
                "metric_value": value,
                "threshold_value": threshold,
                "previous_baseline_pct": config.baseline_percentage,
                "previous_local_pct": config.local_percentage,
                "new_baseline_pct": 100,
                "new_local_pct": 0,
                "evaluation_window": self._window,
                "details": (
                    f"Automatic rollback: {trigger}={value:.4f} "
                    f"exceeded threshold={threshold:.4f}"
                ),
            })
            await session.commit()

        self._last_rollback_event_id = event_id
        logger.critical(
            "automatic_rollback_triggered",
            event_id=event_id,
            trigger=trigger,
            value=value,
            threshold=threshold,
            previous_local_pct=config.local_percentage,
        )

    async def check_now(self) -> dict:
        """Manually trigger a check (for testing and admin endpoints)."""
        await self._evaluate()
        config = self._routing.config
        return {
            "rolled_back": self._routing.is_rolled_back,
            "current_local_pct": config.local_percentage,
            "last_rollback_event": self._last_rollback_event_id,
        }

