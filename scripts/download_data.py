#!/usr/bin/env python3
"""Download the Banking77 dataset from Hugging Face."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    """Download PolyAI/banking77 and save metadata."""
    project_root = Path(__file__).resolve().parent.parent
    raw_dir = project_root / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    print("📥 Downloading PolyAI/banking77 dataset...")
    try:
        from datasets import load_dataset
    except ImportError:
        print("❌ 'datasets' package not installed. Run: pip install datasets")
        sys.exit(1)

    dataset = load_dataset("PolyAI/banking77")
    print(f"✅ Dataset loaded successfully")

    # Save dataset info
    train_data = dataset["train"]
    test_data = dataset["test"]

    print(f"   Train split: {len(train_data)} examples")
    print(f"   Test split:  {len(test_data)} examples")

    # Get label names
    label_names = train_data.features["label"].names
    print(f"   Classes: {len(label_names)}")

    # Save as JSON for reproducibility
    train_path = raw_dir / "train.json"
    test_path = raw_dir / "test.json"

    train_records = [
        {"text": row["text"], "label": label_names[row["label"]], "label_id": row["label"]}
        for row in train_data
    ]
    test_records = [
        {"text": row["text"], "label": label_names[row["label"]], "label_id": row["label"]}
        for row in test_data
    ]

    with open(train_path, "w") as f:
        json.dump(train_records, f, indent=2)
    with open(test_path, "w") as f:
        json.dump(test_records, f, indent=2)

    # Save metadata
    meta = {
        "dataset": "PolyAI/banking77",
        "download_timestamp": datetime.now(timezone.utc).isoformat(),
        "train_size": len(train_records),
        "test_size": len(test_records),
        "num_classes": len(label_names),
        "label_names": label_names,
        "source": "https://huggingface.co/datasets/PolyAI/banking77",
        "license": "CC BY 4.0",
    }
    with open(raw_dir / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"✅ Saved to {raw_dir}")
    print(f"   train.json: {train_path}")
    print(f"   test.json:  {test_path}")


if __name__ == "__main__":
    main()

