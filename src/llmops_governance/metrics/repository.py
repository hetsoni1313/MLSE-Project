"""Repository pattern for database access — async CRUD operations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from llmops_governance.metrics.models import (
    EvaluationSummary,
    ExperimentRun,
    RequestLog,
    RollbackEvent,
    RoutingConfigHistory,
)


class RequestLogRepository:
    """Async repository for request logs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, log_data: dict[str, Any]) -> RequestLog:
        """Persist a request log entry."""
        entry = RequestLog(**log_data)
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get_recent(self, limit: int = 100) -> list[RequestLog]:
        """Get most recent request logs."""
        result = await self._session.execute(
            select(RequestLog).order_by(desc(RequestLog.timestamp)).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_experiment(self, experiment_id: str) -> list[RequestLog]:
        """Get all logs for a specific experiment."""
        result = await self._session.execute(
            select(RequestLog)
            .where(RequestLog.experiment_id == experiment_id)
            .order_by(RequestLog.timestamp)
        )
        return list(result.scalars().all())

    async def get_recent_with_ground_truth(self, route: str, limit: int = 100) -> list[RequestLog]:
        """Get recent requests with ground truth labels for a specific route."""
        result = await self._session.execute(
            select(RequestLog)
            .where(
                RequestLog.route == route,
                RequestLog.ground_truth_label.isnot(None),
            )
            .order_by(desc(RequestLog.timestamp))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_by_route(self, route: str, limit: int = 100) -> list[RequestLog]:
        """Get recent requests for a specific route (for latency/error checks)."""
        result = await self._session.execute(
            select(RequestLog)
            .where(RequestLog.route == route)
            .order_by(desc(RequestLog.timestamp))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_route(self) -> dict[str, int]:
        """Count requests per route."""
        result = await self._session.execute(
            select(RequestLog.route, func.count(RequestLog.id)).group_by(RequestLog.route)
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_accuracy_stats(
        self, route: str | None = None, limit: int = 1000
    ) -> dict[str, Any]:
        """Calculate accuracy statistics for labelled requests."""
        query = select(RequestLog).where(RequestLog.ground_truth_label.isnot(None))
        if route:
            query = query.where(RequestLog.route == route)
        query = query.order_by(desc(RequestLog.timestamp)).limit(limit)

        result = await self._session.execute(query)
        logs = list(result.scalars().all())

        if not logs:
            return {"total": 0, "correct": 0, "accuracy": 0.0}

        correct = sum(1 for log in logs if log.correct)
        return {
            "total": len(logs),
            "correct": correct,
            "accuracy": correct / len(logs),
        }

    async def get_latency_stats(
        self, route: str | None = None, limit: int = 1000
    ) -> dict[str, float]:
        """Calculate latency percentiles."""
        query = select(RequestLog.latency_ms)
        if route:
            query = query.where(RequestLog.route == route)
        query = query.order_by(desc(RequestLog.timestamp)).limit(limit)

        result = await self._session.execute(query)
        latencies = sorted([row[0] for row in result.all()])

        if not latencies:
            return {"mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "count": 0}

        n = len(latencies)
        return {
            "mean": sum(latencies) / n,
            "p50": latencies[int(n * 0.50)],
            "p95": latencies[min(int(n * 0.95), n - 1)],
            "p99": latencies[min(int(n * 0.99), n - 1)],
            "count": n,
        }

    async def get_cost_stats(
        self, route: str | None = None, _limit: int = 1000
    ) -> dict[str, float]:
        """Calculate cost statistics."""
        query = select(
            func.sum(RequestLog.estimated_cost),
            func.avg(RequestLog.estimated_cost),
            func.count(RequestLog.id),
            func.avg(RequestLog.input_tokens),
            func.avg(RequestLog.output_tokens),
        )
        if route:
            query = query.where(RequestLog.route == route)

        result = await self._session.execute(query)
        row = result.one()
        total_cost = row[0] or 0.0
        avg_cost = row[1] or 0.0
        count = row[2] or 0
        avg_input = row[3] or 0.0
        avg_output = row[4] or 0.0

        return {
            "total_cost": float(total_cost),
            "avg_cost_per_query": float(avg_cost),
            "cost_per_1k": float(avg_cost) * 1000,
            "total_queries": int(count),
            "avg_input_tokens": float(avg_input),
            "avg_output_tokens": float(avg_output),
        }


class ExperimentRepository:
    """Async repository for experiment runs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, data: dict[str, Any]) -> ExperimentRun:
        """Save an experiment run."""
        entry = ExperimentRun(**data)
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get(self, experiment_id: str) -> ExperimentRun | None:
        """Get an experiment by ID."""
        result = await self._session.execute(
            select(ExperimentRun).where(ExperimentRun.experiment_id == experiment_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[ExperimentRun]:
        """List all experiments."""
        result = await self._session.execute(
            select(ExperimentRun).order_by(desc(ExperimentRun.started_at))
        )
        return list(result.scalars().all())

    async def update_ended(self, experiment_id: str, total_requests: int) -> None:
        """Mark an experiment as ended."""
        result = await self._session.execute(
            select(ExperimentRun).where(ExperimentRun.experiment_id == experiment_id)
        )
        exp = result.scalar_one_or_none()
        if exp:
            exp.ended_at = datetime.now(UTC)
            exp.total_requests = total_requests


class RollbackRepository:
    """Async repository for rollback events."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, data: dict[str, Any]) -> RollbackEvent:
        """Save a rollback event."""
        entry = RollbackEvent(**data)
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get_recent(self, limit: int = 20) -> list[RollbackEvent]:
        """Get recent rollback events."""
        result = await self._session.execute(
            select(RollbackEvent).order_by(desc(RollbackEvent.timestamp)).limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest(self) -> RollbackEvent | None:
        """Get the most recent rollback event."""
        result = await self._session.execute(
            select(RollbackEvent).order_by(desc(RollbackEvent.timestamp)).limit(1)
        )
        return result.scalar_one_or_none()


class EvaluationRepository:
    """Async repository for evaluation summaries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, data: dict[str, Any]) -> EvaluationSummary:
        """Save an evaluation summary."""
        entry = EvaluationSummary(**data)
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get_by_model(self, model_name: str) -> list[EvaluationSummary]:
        """Get evaluations for a specific model."""
        result = await self._session.execute(
            select(EvaluationSummary)
            .where(EvaluationSummary.model_name == model_name)
            .order_by(desc(EvaluationSummary.timestamp))
        )
        return list(result.scalars().all())

    async def get_latest(self) -> list[EvaluationSummary]:
        """Get the latest evaluation for each model."""
        result = await self._session.execute(
            select(EvaluationSummary).order_by(desc(EvaluationSummary.timestamp))
        )
        return list(result.scalars().all())


class RoutingConfigRepository:
    """Async repository for routing config history."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, data: dict[str, Any]) -> RoutingConfigHistory:
        """Save a routing config change."""
        entry = RoutingConfigHistory(**data)
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get_history(self, limit: int = 50) -> list[RoutingConfigHistory]:
        """Get routing config change history."""
        result = await self._session.execute(
            select(RoutingConfigHistory).order_by(desc(RoutingConfigHistory.timestamp)).limit(limit)
        )
        return list(result.scalars().all())
