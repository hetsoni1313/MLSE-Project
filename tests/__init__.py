"""Shared pytest fixtures for the LLMOps test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from gateway.routing.config import RoutingConfig
from gateway.routing.engine import RoutingEngine

from llmops_governance.core.constants import BANKING77_LABEL_SET, BANKING77_LABELS

# Ensure project root is on path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))


@pytest.fixture
def banking77_labels() -> list[str]:
    """Return the full Banking77 label list."""
    return BANKING77_LABELS.copy()


@pytest.fixture
def banking77_label_set() -> frozenset[str]:
    """Return the Banking77 label set."""
    return BANKING77_LABEL_SET


@pytest.fixture
def sample_messages() -> list[dict[str, str]]:
    """Sample messages with ground truth labels."""
    return [
        {"text": "How do I get a new card?", "label": "get_physical_card"},
        {"text": "My card was stolen yesterday", "label": "lost_or_stolen_card"},
        {"text": "Why is my transfer still pending?", "label": "pending_transfer"},
        {"text": "I need to change my PIN", "label": "change_pin"},
        {"text": "Cancel my bank transfer please", "label": "cancel_transfer"},
        {"text": "What's the exchange rate today?", "label": "exchange_rate"},
        {"text": "I want a refund for the charge", "label": "request_refund"},
        {"text": "How do I top up my account?", "label": "topping_up_by_card"},
        {"text": "My contactless isn't working", "label": "contactless_not_working"},
        {"text": "I need to verify my identity", "label": "verify_my_identity"},
    ]


@pytest.fixture
def routing_config_baseline() -> RoutingConfig:
    """Baseline-only routing config."""
    return RoutingConfig(mode="baseline", baseline_percentage=100, local_percentage=0)


@pytest.fixture
def routing_config_weighted() -> RoutingConfig:
    """50/50 weighted routing config."""
    return RoutingConfig(mode="weighted", baseline_percentage=50, local_percentage=50)


@pytest.fixture
def routing_config_shadow() -> RoutingConfig:
    """Shadow mode routing config."""
    return RoutingConfig(
        mode="shadow", baseline_percentage=100, local_percentage=0, shadow_enabled=True
    )


@pytest.fixture
def routing_engine(routing_config_baseline: RoutingConfig) -> RoutingEngine:
    """Create a routing engine with baseline config."""
    return RoutingEngine(routing_config_baseline)


@pytest.fixture
def sample_predictions() -> list[dict]:
    """Sample prediction results for testing."""
    return [
        {
            "prediction": "get_physical_card",
            "ground_truth": "get_physical_card",
            "latency_ms": 120.0,
            "cost": 0.0001,
        },
        {
            "prediction": "lost_or_stolen_card",
            "ground_truth": "lost_or_stolen_card",
            "latency_ms": 115.0,
            "cost": 0.0001,
        },
        {
            "prediction": "pending_transfer",
            "ground_truth": "pending_transfer",
            "latency_ms": 130.0,
            "cost": 0.0001,
        },
        {
            "prediction": "change_pin",
            "ground_truth": "change_pin",
            "latency_ms": 110.0,
            "cost": 0.0001,
        },
        {
            "prediction": "cancel_transfer",
            "ground_truth": "cancel_transfer",
            "latency_ms": 125.0,
            "cost": 0.0001,
        },
        {
            "prediction": "exchange_rate",
            "ground_truth": "exchange_rate",
            "latency_ms": 140.0,
            "cost": 0.0001,
        },
        {
            "prediction": "request_refund",
            "ground_truth": "request_refund",
            "latency_ms": 105.0,
            "cost": 0.0001,
        },
        {
            "prediction": "activate_my_card",
            "ground_truth": "topping_up_by_card",
            "latency_ms": 135.0,
            "cost": 0.0001,
        },
        {
            "prediction": "contactless_not_working",
            "ground_truth": "contactless_not_working",
            "latency_ms": 118.0,
            "cost": 0.0001,
        },
        {
            "prediction": "verify_my_identity",
            "ground_truth": "verify_my_identity",
            "latency_ms": 122.0,
            "cost": 0.0001,
        },
    ]
