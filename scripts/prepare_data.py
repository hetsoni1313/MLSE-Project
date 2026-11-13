#!/usr/bin/env python3
"""Prepare deterministic train/validation/golden splits from Banking77."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SEED = 42
VAL_SIZE = 500
GOLDEN_SIZE = 500


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def stratified_sample(
    data: list[dict], n: int, seed: int
) -> tuple[list[dict], list[dict]]:
    """Stratified sampling: extract n samples maintaining class distribution."""
    import random

    rng = random.Random(seed)

    by_class: dict[str, list[dict]] = {}
    for item in data:
        label = item["label"]
        by_class.setdefault(label, []).append(item)

    # Shuffle within each class
    for items in by_class.values():
        rng.shuffle(items)

    # Calculate samples per class
    n_classes = len(by_class)
    base_per_class = n // n_classes
    remainder = n % n_classes

    sampled: list[dict] = []
    remaining: list[dict] = []
    classes_sorted = sorted(by_class.keys())

    for i, cls in enumerate(classes_sorted):
        items = by_class[cls]
        take = base_per_class + (1 if i < remainder else 0)
        take = min(take, len(items))
        sampled.extend(items[:take])
        remaining.extend(items[take:])

    return sampled, remaining


def main() -> None:
    """Create reproducible data splits."""
    project_root = Path(__file__).resolve().parent.parent
    raw_dir = project_root / "data" / "raw"
    splits_dir = project_root / "data" / "splits"
    manifest_dir = project_root / "data" / "manifests"

    splits_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    # Load raw data
    train_path = raw_dir / "train.json"
    test_path = raw_dir / "test.json"

    if not train_path.exists() or not test_path.exists():
        print("❌ Raw data not found. Run: python scripts/download_data.py")
        sys.exit(1)

    with open(train_path) as f:
        train_data = json.load(f)
    with open(test_path) as f:
        test_data = json.load(f)

    print(f"📊 Raw train: {len(train_data)}, Raw test: {len(test_data)}")

    # Create validation split from training data
    val_data, train_remaining = stratified_sample(train_data, VAL_SIZE, SEED)
    print(f"   Validation: {len(val_data)} (stratified from train)")
    print(f"   Training:   {len(train_remaining)} (remaining train)")

    # Create golden test set from test data
    golden_data, _ = stratified_sample(test_data, GOLDEN_SIZE, SEED)
    print(f"   Golden test: {len(golden_data)} (stratified from test)")

    # Save splits
    splits = {
        "train.json": train_remaining,
        "validation.json": val_data,
        "golden_test.json": golden_data,
    }

    for filename, data in splits.items():
        path = splits_dir / filename
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    # Compute hashes
    hashes = {}
    for filename in splits:
        path = splits_dir / filename
        hashes[filename] = sha256_file(path)

    # Class distribution
    def class_dist(data: list[dict]) -> dict[str, int]:
        return dict(Counter(d["label"] for d in data))

    # Save manifest
    manifest = {
        "dataset": "PolyAI/banking77",
        "source": "https://huggingface.co/datasets/PolyAI/banking77",
        "license": "CC BY 4.0",
        "preparation_timestamp": datetime.now(timezone.utc).isoformat(),
        "random_seed": SEED,
        "preprocessing_version": "1.0.0",
        "splits": {
            "train": {
                "file": "train.json",
                "size": len(train_remaining),
                "sha256": hashes["train.json"],
            },
            "validation": {
                "file": "validation.json",
                "size": len(val_data),
                "sha256": hashes["validation.json"],
            },
            "golden_test": {
                "file": "golden_test.json",
                "size": len(golden_data),
                "sha256": hashes["golden_test.json"],
            },
        },
        "class_distribution": {
            "train": class_dist(train_remaining),
            "validation": class_dist(val_data),
            "golden_test": class_dist(golden_data),
        },
        "total_classes": len(set(d["label"] for d in train_data)),
    }

    manifest_path = manifest_dir / "dataset_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n✅ Splits saved to {splits_dir}")
    print(f"✅ Manifest saved to {manifest_path}")
    print(f"\nHashes:")
    for name, h in hashes.items():
        print(f"   {name}: {h[:16]}...")


if __name__ == "__main__":
    main()

