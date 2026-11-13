"""Metric computation functions for evaluation.

Pure functions — no side effects, no database, no I/O.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict

from llmops_governance.core.constants import BANKING77_LABEL_SET


def compute_accuracy(predictions: list[str], ground_truth: list[str]) -> float:
    """Exact-match accuracy."""
    if not predictions or len(predictions) != len(ground_truth):
        return 0.0
    correct = sum(1 for p, g in zip(predictions, ground_truth) if p == g)
    return correct / len(predictions)


def compute_macro_f1(predictions: list[str], ground_truth: list[str]) -> float:
    """Macro-averaged F1 score across all classes."""
    if not predictions:
        return 0.0

    classes = set(ground_truth) | set(predictions)
    f1_scores: list[float] = []

    for cls in classes:
        tp = sum(1 for p, g in zip(predictions, ground_truth) if p == cls and g == cls)
        fp = sum(1 for p, g in zip(predictions, ground_truth) if p == cls and g != cls)
        fn = sum(1 for p, g in zip(predictions, ground_truth) if p != cls and g == cls)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        f1_scores.append(f1)

    return statistics.mean(f1_scores) if f1_scores else 0.0


def compute_invalid_rate(predictions: list[str], valid_labels: frozenset[str] | None = None) -> float:
    """Percentage of predictions not in the valid label set."""
    if not predictions:
        return 0.0
    labels = valid_labels or BANKING77_LABEL_SET
    invalid = sum(1 for p in predictions if p not in labels)
    return invalid / len(predictions)


def compute_latency_stats(latencies: list[float]) -> dict[str, float]:
    """Compute latency percentile statistics."""
    if not latencies:
        return {"mean": 0.0, "median": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "min": 0.0, "max": 0.0}

    sorted_lats = sorted(latencies)
    n = len(sorted_lats)
    return {
        "mean": statistics.mean(sorted_lats),
        "median": statistics.median(sorted_lats),
        "p50": sorted_lats[int(n * 0.50)],
        "p95": sorted_lats[min(int(n * 0.95), n - 1)],
        "p99": sorted_lats[min(int(n * 0.99), n - 1)],
        "min": sorted_lats[0],
        "max": sorted_lats[-1],
    }


def compute_per_class_accuracy(
    predictions: list[str], ground_truth: list[str]
) -> dict[str, dict[str, float | int]]:
    """Per-class accuracy and counts."""
    class_correct: dict[str, int] = defaultdict(int)
    class_total: dict[str, int] = defaultdict(int)

    for pred, gt in zip(predictions, ground_truth):
        class_total[gt] += 1
        if pred == gt:
            class_correct[gt] += 1

    result: dict[str, dict[str, float | int]] = {}
    for cls in sorted(class_total.keys()):
        total = class_total[cls]
        correct = class_correct[cls]
        result[cls] = {
            "total": total,
            "correct": correct,
            "accuracy": correct / total if total > 0 else 0.0,
        }
    return result


def compute_confusion_counts(
    predictions: list[str], ground_truth: list[str]
) -> dict[str, Counter]:
    """Build confusion matrix as dict of Counters: gt_label -> Counter(pred_label -> count)."""
    confusion: dict[str, Counter] = defaultdict(Counter)
    for pred, gt in zip(predictions, ground_truth):
        confusion[gt][pred] += 1
    return dict(confusion)


def compute_error_rate(errors: list[bool]) -> float:
    """Compute error rate from a list of error flags."""
    if not errors:
        return 0.0
    return sum(1 for e in errors if e) / len(errors)

