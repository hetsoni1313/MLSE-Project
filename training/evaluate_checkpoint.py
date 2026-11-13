"""Evaluate a fine-tuned model checkpoint against the Banking77 test set.

This script loads predictions from a checkpoint evaluation run (typically
done on Colab) and computes metrics locally.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.metrics import (
    compute_accuracy,
    compute_macro_f1,
    compute_invalid_rate,
    compute_latency_stats,
    compute_per_class_accuracy,
)
from llmops_governance.core.constants import BANKING77_LABEL_SET


def evaluate_predictions(predictions_path: Path) -> dict:
    """Evaluate predictions from a JSON file.

    Expected format: list of {"prediction": str, "ground_truth": str, "latency_ms": float}
    """
    with open(predictions_path) as f:
        data = json.load(f)

    preds = [d["prediction"] for d in data]
    truths = [d["ground_truth"] for d in data]
    latencies = [d.get("latency_ms", 0.0) for d in data]

    accuracy = compute_accuracy(preds, truths)
    macro_f1 = compute_macro_f1(preds, truths)
    invalid_rate = compute_invalid_rate(preds, BANKING77_LABEL_SET)
    latency_stats = compute_latency_stats(latencies)
    per_class = compute_per_class_accuracy(preds, truths)

    # Find worst-performing classes
    worst_classes = sorted(
        per_class.items(),
        key=lambda x: x[1]["accuracy"],
    )[:5]

    return {
        "total_samples": len(data),
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "invalid_rate": invalid_rate,
        "latency": latency_stats,
        "worst_classes": {k: v for k, v in worst_classes},
    }


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python evaluate_checkpoint.py <predictions.json>")
        print()
        print("Predictions file format (JSON array):")
        print('  [{"prediction": "change_pin", "ground_truth": "change_pin", "latency_ms": 42.5}, ...]')
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"ERROR: File not found: {path}")
        sys.exit(1)

    results = evaluate_predictions(path)

    print("=" * 60)
    print("Checkpoint Evaluation Results")
    print("=" * 60)
    print(f"  Samples:      {results['total_samples']}")
    print(f"  Accuracy:     {results['accuracy']:.4f}")
    print(f"  Macro F1:     {results['macro_f1']:.4f}")
    print(f"  Invalid Rate: {results['invalid_rate']:.4f}")
    print(f"  Mean Latency: {results['latency']['mean']:.1f} ms")
    print(f"  P95 Latency:  {results['latency']['p95']:.1f} ms")
    print()
    print("Worst-performing classes:")
    for cls, stats in results["worst_classes"].items():
        print(f"  {cls}: {stats['accuracy']:.2%} ({stats['correct']}/{stats['total']})")

    # Write results
    output_path = path.parent / f"{path.stem}_evaluation.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()

