"""Unit tests for repository CRUD operations."""

from datetime import datetime, timezone
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from llmops_governance.metrics.models import Base
from llmops_governance.metrics.repository import (
    EvaluationRepository,
    ExperimentRepository,
    RequestLogRepository,
    RollbackRepository,
    RoutingConfigRepository,
)


@pytest_asyncio.fixture
async def async_session():
    """Create an in-memory SQLite async session for repository testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


class TestRepositories:
    @pytest.mark.asyncio
    async def test_request_log_crud(self, async_session):
        repo = RequestLogRepository(async_session)
        entry = await repo.save({
            "request_id": "req-1",
            "route": "local",
            "model_name": "qwen2.5-q4",
            "input_text": "Need a replacement card",
            "predicted_label": "get_physical_card",
            "ground_truth_label": "get_physical_card",
            "correct": True,
            "valid_output": True,
            "latency_ms": 42.0,
            "experiment_id": "exp-001",
        })
        assert entry.id is not None

        # Fetch recent
        recent = await repo.get_recent(10)
        assert len(recent) == 1
        assert recent[0].request_id == "req-1"

        # By experiment
        by_exp = await repo.get_by_experiment("exp-001")
        assert len(by_exp) == 1

        # With ground truth
        gt_logs = await repo.get_recent_with_ground_truth("local", 10)
        assert len(gt_logs) == 1

        # By route
        by_route = await repo.get_recent_by_route("local", 10)
        assert len(by_route) == 1

    @pytest.mark.asyncio
    async def test_experiment_crud(self, async_session):
        repo = ExperimentRepository(async_session)
        exp = await repo.save({
            "experiment_id": "exp-test-1",
            "name": "Canary Rollout 10%",
            "routing_mode": "weighted",
            "baseline_pct": 90,
            "local_pct": 10,
        })
        assert exp.id is not None

        fetched = await repo.get("exp-test-1")
        assert fetched is not None
        assert fetched.name == "Canary Rollout 10%"

        await repo.update_ended("exp-test-1", total_requests=100)
        completed = await repo.get("exp-test-1")
        assert completed.total_requests == 100
        assert completed.ended_at is not None

    @pytest.mark.asyncio
    async def test_rollback_crud(self, async_session):
        repo = RollbackRepository(async_session)
        rb = await repo.save({
            "event_id": "rb-001",
            "trigger_type": "accuracy",
            "metric_value": 0.72,
            "threshold_value": 0.85,
            "previous_baseline_pct": 50,
            "previous_local_pct": 50,
            "new_baseline_pct": 100,
            "new_local_pct": 0,
            "evaluation_window": 100,
            "details": "Accuracy dropped below 85%",
        })
        assert rb.id is not None

        recent = await repo.get_recent(5)
        assert len(recent) == 1
        assert recent[0].event_id == "rb-001"
        assert recent[0].metric_value == 0.72

    @pytest.mark.asyncio
    async def test_routing_config_crud(self, async_session):
        repo = RoutingConfigRepository(async_session)
        cfg = await repo.save({
            "mode": "canary",
            "baseline_pct": 75,
            "local_pct": 25,
            "changed_by": "test-admin",
            "reason": "Promoting canary to 25%",
        })
        assert cfg.id is not None

        history = await repo.get_history(10)
        assert len(history) == 1
        assert history[0].mode == "canary"
        assert history[0].local_pct == 25

    @pytest.mark.asyncio
    async def test_evaluation_summary_crud(self, async_session):
        repo = EvaluationRepository(async_session)
        summary = await repo.save({
            "model_name": "qwen2.5-q4",
            "accuracy": 0.87,
            "macro_f1": 0.86,
            "invalid_rate": 0.01,
            "mean_latency_ms": 48.0,
            "p50_latency_ms": 45.0,
            "p95_latency_ms": 85.0,
            "cost_per_query": 0.0001,
            "total_requests": 500,
        })
        assert summary.id is not None

        by_model = await repo.get_by_model("qwen2.5-q4")
        assert len(by_model) == 1
        assert by_model[0].accuracy == 0.87
