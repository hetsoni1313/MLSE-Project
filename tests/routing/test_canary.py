"""Tests for canary deployment stages."""

from gateway.routing.config import RoutingConfig
from gateway.routing.engine import RoutingEngine


class TestCanaryDeployment:
    def test_advance_canary_stages(self):
        config = RoutingConfig(
            mode="canary",
            baseline_percentage=95,
            local_percentage=5,
            canary_stages=[5, 25, 50, 100],
            current_canary_stage=0,
        )
        engine = RoutingEngine(config)

        # Advance to stage 1 (25%)
        new_pct = engine.advance_canary()
        assert new_pct == 25
        assert engine.config.local_percentage == 25

        # Advance to stage 2 (50%)
        new_pct = engine.advance_canary()
        assert new_pct == 50

        # Advance to stage 3 (100%)
        new_pct = engine.advance_canary()
        assert new_pct == 100

    def test_canary_at_final_stage(self):
        config = RoutingConfig(
            mode="canary",
            baseline_percentage=0,
            local_percentage=100,
            canary_stages=[5, 25, 50, 100],
            current_canary_stage=3,
        )
        engine = RoutingEngine(config)
        new_pct = engine.advance_canary()
        assert new_pct == 100  # Already at final stage
