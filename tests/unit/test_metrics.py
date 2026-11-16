"""Tests for evaluation metrics computation."""

import pytest
from evaluation.metrics import (
    compute_accuracy,
    compute_error_rate,
    compute_invalid_rate,
    compute_latency_stats,
    compute_macro_f1,
    compute_per_class_accuracy,
)

from llmops_governance.core.constants import BANKING77_LABEL_SET


class TestAccuracy:
    def test_perfect_accuracy(self):
        preds = ["a", "b", "c"]
        truth = ["a", "b", "c"]
        assert compute_accuracy(preds, truth) == 1.0

    def test_zero_accuracy(self):
        preds = ["x", "y", "z"]
        truth = ["a", "b", "c"]
        assert compute_accuracy(preds, truth) == 0.0

    def test_partial_accuracy(self):
        preds = ["a", "b", "x"]
        truth = ["a", "b", "c"]
        assert abs(compute_accuracy(preds, truth) - 2 / 3) < 0.001

    def test_empty_input(self):
        assert compute_accuracy([], []) == 0.0


class TestMacroF1:
    def test_perfect_f1(self):
        preds = ["a", "b", "c"]
        truth = ["a", "b", "c"]
        assert compute_macro_f1(preds, truth) == 1.0

    def test_zero_f1(self):
        preds = ["x", "y", "z"]
        truth = ["a", "b", "c"]
        assert compute_macro_f1(preds, truth) == 0.0

    def test_partial_f1(self):
        preds = ["a", "a", "b"]
        truth = ["a", "b", "b"]
        f1 = compute_macro_f1(preds, truth)
        assert 0.0 < f1 < 1.0


class TestInvalidRate:
    def test_all_valid(self):
        preds = ["activate_my_card", "change_pin"]
        assert compute_invalid_rate(preds, BANKING77_LABEL_SET) == 0.0

    def test_all_invalid(self):
        preds = ["nonexistent", "fake_label"]
        assert compute_invalid_rate(preds, BANKING77_LABEL_SET) == 1.0

    def test_mixed(self):
        preds = ["activate_my_card", "fake_label"]
        assert compute_invalid_rate(preds, BANKING77_LABEL_SET) == 0.5


class TestLatencyStats:
    def test_basic_stats(self):
        lats = [100.0, 200.0, 300.0, 400.0, 500.0]
        stats = compute_latency_stats(lats)
        assert stats["mean"] == 300.0
        assert stats["min"] == 100.0
        assert stats["max"] == 500.0

    def test_empty_latencies(self):
        stats = compute_latency_stats([])
        assert stats["mean"] == 0.0

    def test_single_latency(self):
        stats = compute_latency_stats([42.0])
        assert stats["mean"] == 42.0
        assert stats["p50"] == 42.0


class TestPerClassAccuracy:
    def test_per_class(self):
        preds = ["a", "a", "b", "b"]
        truth = ["a", "b", "b", "b"]
        result = compute_per_class_accuracy(preds, truth)
        assert result["a"]["accuracy"] == 1.0  # 1/1 correct for class a
        assert result["b"]["accuracy"] == pytest.approx(2 / 3, abs=0.01)  # 2/3 correct


class TestErrorRate:
    def test_no_errors(self):
        assert compute_error_rate([False, False, False]) == 0.0

    def test_all_errors(self):
        assert compute_error_rate([True, True, True]) == 1.0

    def test_mixed(self):
        assert compute_error_rate([True, False, False, True]) == 0.5
