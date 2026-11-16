"""Tests for weighted routing distribution."""

from collections import Counter

from gateway.routing.config import RoutingConfig
from gateway.routing.engine import Route, RoutingEngine


class TestWeightedRouting:
    def test_100_baseline(self):
        engine = RoutingEngine(
            RoutingConfig(mode="baseline", baseline_percentage=100, local_percentage=0)
        )
        routes = [engine.determine_route() for _ in range(100)]
        assert all(r == Route.BASELINE for r in routes)

    def test_100_local(self):
        engine = RoutingEngine(
            RoutingConfig(mode="weighted", baseline_percentage=0, local_percentage=100)
        )
        routes = [engine.determine_route() for _ in range(100)]
        assert all(r == Route.LOCAL for r in routes)

    def test_50_50_distribution(self):
        """50/50 split should produce roughly equal distribution."""
        engine = RoutingEngine(
            RoutingConfig(
                mode="weighted", baseline_percentage=50, local_percentage=50, sticky_enabled=False
            )
        )
        routes = [engine.determine_route() for _ in range(1000)]
        counts = Counter(routes)
        # Allow 15% tolerance
        assert 350 < counts[Route.BASELINE] < 650
        assert 350 < counts[Route.LOCAL] < 650

    def test_90_10_distribution(self):
        """90/10 split should produce ~90% baseline."""
        engine = RoutingEngine(
            RoutingConfig(
                mode="weighted", baseline_percentage=90, local_percentage=10, sticky_enabled=False
            )
        )
        routes = [engine.determine_route() for _ in range(1000)]
        counts = Counter(routes)
        assert counts[Route.BASELINE] > 800
        assert counts[Route.LOCAL] < 200
