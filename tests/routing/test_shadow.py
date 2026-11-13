"""Tests for shadow mode routing."""

import pytest
from gateway.routing.config import RoutingConfig
from gateway.routing.engine import Route, RoutingEngine


class TestShadowMode:
    def test_shadow_mode_returns_shadow_route(self):
        engine = RoutingEngine(RoutingConfig(mode="shadow", baseline_percentage=100, local_percentage=0, shadow_enabled=True))
        route = engine.determine_route(user_id="user-1")
        assert route == Route.SHADOW

    def test_shadow_enabled_flag(self):
        engine = RoutingEngine(RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50, shadow_enabled=True))
        route = engine.determine_route()
        assert route == Route.SHADOW

    def test_shadow_disabled(self):
        engine = RoutingEngine(RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50, shadow_enabled=False))
        route = engine.determine_route()
        assert route in (Route.BASELINE, Route.LOCAL)

