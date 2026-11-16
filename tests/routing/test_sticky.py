"""Tests for sticky routing — deterministic user assignment."""

from gateway.routing.config import RoutingConfig
from gateway.routing.engine import Route, RoutingEngine


class TestStickyRouting:
    def test_same_user_same_route(self):
        """Same user_id always gets the same route."""
        engine = RoutingEngine(
            RoutingConfig(
                mode="weighted", baseline_percentage=50, local_percentage=50, sticky_enabled=True
            )
        )
        route1 = engine.determine_route(user_id="user-42")
        for _ in range(50):
            assert engine.determine_route(user_id="user-42") == route1

    def test_different_users_distributed(self):
        """Different users should be distributed across routes."""
        engine = RoutingEngine(
            RoutingConfig(
                mode="weighted", baseline_percentage=50, local_percentage=50, sticky_enabled=True
            )
        )
        routes = {engine.determine_route(user_id=f"user-{i}") for i in range(100)}
        assert Route.BASELINE in routes
        assert Route.LOCAL in routes

    def test_request_id_fallback(self):
        """When user_id is None, request_id is used for hashing."""
        engine = RoutingEngine(
            RoutingConfig(
                mode="weighted", baseline_percentage=50, local_percentage=50, sticky_enabled=True
            )
        )
        route1 = engine.determine_route(request_id="req-abc")
        for _ in range(20):
            assert engine.determine_route(request_id="req-abc") == route1

    def test_stable_across_calls(self):
        """Assignment remains stable when config doesn't change."""
        engine = RoutingEngine(
            RoutingConfig(
                mode="weighted", baseline_percentage=70, local_percentage=30, sticky_enabled=True
            )
        )
        assignments = {}
        for i in range(50):
            uid = f"user-{i}"
            assignments[uid] = engine.determine_route(user_id=uid)

        # Verify stability
        for uid, expected_route in assignments.items():
            assert engine.determine_route(user_id=uid) == expected_route
