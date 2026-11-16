"""Tests for routing config validation."""

import pytest
from gateway.routing.config import RoutingConfig
from pydantic import ValidationError


class TestRoutingConfig:
    def test_valid_baseline(self):
        config = RoutingConfig(mode="baseline", baseline_percentage=100, local_percentage=0)
        assert config.mode == "baseline"

    def test_valid_weighted(self):
        config = RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50)
        assert config.baseline_percentage + config.local_percentage == 100

    def test_invalid_sum(self):
        with pytest.raises(ValidationError):
            RoutingConfig(mode="weighted", baseline_percentage=60, local_percentage=60)

    def test_negative_percentage(self):
        with pytest.raises(ValidationError):
            RoutingConfig(mode="weighted", baseline_percentage=-10, local_percentage=110)

    def test_invalid_mode(self):
        with pytest.raises(ValidationError):
            RoutingConfig(mode="invalid_mode", baseline_percentage=100, local_percentage=0)

    def test_to_baseline_only(self):
        config = RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50)
        baseline = config.to_baseline_only()
        assert baseline.mode == "baseline"
        assert baseline.baseline_percentage == 100
        assert baseline.local_percentage == 0
