"""Tests for automatic rollback monitor."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from gateway.resilience.rollback import RollbackMonitor
from gateway.routing.config import RoutingConfig
from gateway.routing.engine import RoutingEngine


def _make_db_manager():
    """Create a mock database manager."""
    db = AsyncMock()
    return db


class TestRollbackMonitor:
    def test_initial_state(self):
        engine = RoutingEngine(
            RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50)
        )
        db = _make_db_manager()
        monitor = RollbackMonitor(engine, db)
        assert monitor is not None
        assert not engine.is_rolled_back

    def test_rollback_sets_baseline(self):
        engine = RoutingEngine(
            RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50)
        )
        engine.trigger_rollback()
        assert engine.is_rolled_back
        assert engine.config.local_percentage == 0
        assert engine.config.baseline_percentage == 100

    def test_rollback_prevents_duplicate(self):
        engine = RoutingEngine(
            RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50)
        )
        engine.trigger_rollback()
        assert engine.is_rolled_back
        # Already rolled back — should still be rolled back
        engine.trigger_rollback()
        assert engine.is_rolled_back

    def test_recovery_clears_rollback(self):
        engine = RoutingEngine(
            RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50)
        )
        engine.trigger_rollback()
        assert engine.is_rolled_back

        new_config = RoutingConfig(mode="weighted", baseline_percentage=90, local_percentage=10)
        engine.recover_from_rollback(new_config)
        assert not engine.is_rolled_back
        assert engine.config.local_percentage == 10

    def test_skip_when_zero_local(self):
        """Monitor should skip evaluation when local traffic is 0%."""
        engine = RoutingEngine(
            RoutingConfig(mode="baseline", baseline_percentage=100, local_percentage=0)
        )
        assert engine.config.local_percentage == 0

    def test_thresholds_configurable(self):
        engine = RoutingEngine(
            RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50)
        )
        db = _make_db_manager()
        monitor = RollbackMonitor(
            engine,
            db,
            min_accuracy=0.90,
            max_error_rate=0.03,
            max_p95_latency_ms=3000.0,
            min_labelled_samples=50,
        )
        assert monitor._min_accuracy == 0.90
        assert monitor._max_error_rate == 0.03
        assert monitor._max_p95_latency_ms == 3000.0
        assert monitor._min_labelled == 50

    @pytest.mark.asyncio
    async def test_evaluate_triggers_accuracy_rollback(self):
        """Accuracy below threshold triggers rollback when sample count met."""
        engine = RoutingEngine(
            RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50)
        )
        db = MagicMock()
        session = AsyncMock()

        # Mock request logs: 35 labelled samples, 20 correct -> accuracy 20/35 = ~57% (< 85%)
        mock_labelled = [MagicMock(correct=(i < 20)) for i in range(35)]
        mock_recent = [MagicMock(error=None, latency_ms=100.0) for _ in range(35)]

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = session
        mock_context.__aexit__.return_value = None
        db.get_session.return_value = mock_context

        with patch("gateway.resilience.rollback.RequestLogRepository") as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.get_recent_by_route.return_value = mock_recent
            repo_instance.get_recent_with_ground_truth.return_value = mock_labelled
            MockRepo.return_value = repo_instance

            monitor = RollbackMonitor(engine, db, min_accuracy=0.85, min_labelled_samples=30)
            await monitor._evaluate()

            assert engine.is_rolled_back
            assert engine.config.local_percentage == 0
            assert engine.config.baseline_percentage == 100

    @pytest.mark.asyncio
    async def test_evaluate_accuracy_skips_when_samples_insufficient(self):
        """Accuracy rollback does NOT trigger if labelled sample count < min_labelled."""
        engine = RoutingEngine(
            RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50)
        )
        db = MagicMock()
        session = AsyncMock()

        # Only 10 labelled samples (min is 30)
        mock_labelled = [MagicMock(correct=False) for _ in range(10)]
        mock_recent = [MagicMock(error=None, latency_ms=100.0) for _ in range(10)]

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = session
        mock_context.__aexit__.return_value = None
        db.get_session.return_value = mock_context

        with patch("gateway.resilience.rollback.RequestLogRepository") as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.get_recent_by_route.return_value = mock_recent
            repo_instance.get_recent_with_ground_truth.return_value = mock_labelled
            MockRepo.return_value = repo_instance

            monitor = RollbackMonitor(engine, db, min_accuracy=0.85, min_labelled_samples=30)
            await monitor._evaluate()

            assert not engine.is_rolled_back
            assert engine.config.local_percentage == 50

    @pytest.mark.asyncio
    async def test_evaluate_triggers_error_rate_rollback(self):
        """Error rate above threshold triggers rollback."""
        engine = RoutingEngine(
            RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50)
        )
        db = MagicMock()
        session = AsyncMock()

        # 20 requests, 10 errors -> 50% error rate (> 5%)
        mock_recent = [
            MagicMock(error="timeout" if i < 10 else None, latency_ms=100.0) for i in range(20)
        ]

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = session
        mock_context.__aexit__.return_value = None
        db.get_session.return_value = mock_context

        with patch("gateway.resilience.rollback.RequestLogRepository") as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.get_recent_by_route.return_value = mock_recent
            MockRepo.return_value = repo_instance

            monitor = RollbackMonitor(engine, db, max_error_rate=0.05)
            await monitor._evaluate()

            assert engine.is_rolled_back
            assert engine.config.local_percentage == 0

    @pytest.mark.asyncio
    async def test_evaluate_triggers_latency_rollback(self):
        """p95 latency above threshold triggers rollback."""
        engine = RoutingEngine(
            RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50)
        )
        db = MagicMock()
        session = AsyncMock()

        # 20 requests with p95 = 6000ms (> 5000ms threshold)
        latencies = [100.0] * 18 + [6000.0, 7000.0]
        mock_recent = [MagicMock(error=None, latency_ms=l) for l in latencies]

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = session
        mock_context.__aexit__.return_value = None
        db.get_session.return_value = mock_context

        with patch("gateway.resilience.rollback.RequestLogRepository") as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.get_recent_by_route.return_value = mock_recent
            MockRepo.return_value = repo_instance

            monitor = RollbackMonitor(engine, db, max_p95_latency_ms=5000.0)
            await monitor._evaluate()

            assert engine.is_rolled_back
            assert engine.config.local_percentage == 0
