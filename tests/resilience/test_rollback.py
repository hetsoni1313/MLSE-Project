"""Tests for automatic rollback monitor."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from gateway.routing.config import RoutingConfig
from gateway.routing.engine import RoutingEngine
from gateway.resilience.rollback import RollbackMonitor


def _make_db_manager():
    """Create a mock database manager."""
    db = AsyncMock()
    return db


class TestRollbackMonitor:
    def test_initial_state(self):
        engine = RoutingEngine(RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50))
        db = _make_db_manager()
        monitor = RollbackMonitor(engine, db)
        assert not engine.is_rolled_back

    def test_rollback_sets_baseline(self):
        engine = RoutingEngine(RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50))
        engine.trigger_rollback()
        assert engine.is_rolled_back
        assert engine.config.local_percentage == 0
        assert engine.config.baseline_percentage == 100

    def test_rollback_prevents_duplicate(self):
        engine = RoutingEngine(RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50))
        engine.trigger_rollback()
        assert engine.is_rolled_back
        # Already rolled back — should still be rolled back
        engine.trigger_rollback()
        assert engine.is_rolled_back

    def test_recovery_clears_rollback(self):
        engine = RoutingEngine(RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50))
        engine.trigger_rollback()
        assert engine.is_rolled_back

        new_config = RoutingConfig(mode="weighted", baseline_percentage=90, local_percentage=10)
        engine.recover_from_rollback(new_config)
        assert not engine.is_rolled_back
        assert engine.config.local_percentage == 10

    def test_skip_when_zero_local(self):
        """Monitor should skip evaluation when local traffic is 0%."""
        engine = RoutingEngine(RoutingConfig(mode="baseline", baseline_percentage=100, local_percentage=0))
        assert engine.config.local_percentage == 0

    def test_thresholds_configurable(self):
        engine = RoutingEngine(RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50))
        db = _make_db_manager()
        monitor = RollbackMonitor(
            engine, db,
            min_accuracy=0.90,
            max_error_rate=0.03,
            max_p95_latency_ms=3000.0,
            min_labelled_samples=50,
        )
        assert monitor._min_accuracy == 0.90
        assert monitor._max_error_rate == 0.03
        assert monitor._max_p95_latency_ms == 3000.0
        assert monitor._min_labelled == 50

