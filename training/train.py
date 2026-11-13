"""Local training entry-point — delegates actual fine-tuning to Colab.

This script validates the training configuration and dataset locally,
then prints instructions for running the actual fine-tuning on Google Colab
with a free T4 GPU.

For actual training, use: training/notebooks/colab_finetuning.ipynb
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


def validate_training_config() -> dict:
    """Validate the training configuration file."""
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        print(f"ERROR: Training config not found at {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    required_keys = ["model", "training", "dataset"]
    for key in required_keys:
        if key not in config:
            print(f"ERROR: Missing required config section: {key}")
            sys.exit(1)

    print("✓ Training configuration validated")
    return config


def validate_dataset() -> int:
    """Check that the prepared dataset exists."""
    data_dir = Path(__file__).parent.parent / "data" / "processed"
    train_path = data_dir / "train.jsonl"
    val_path = data_dir / "val.jsonl"

    if not train_path.exists():
        print(f"WARNING: Training data not found at {train_path}")
        print("  Run: python scripts/download_data.py && python scripts/prepare_data.py")
        return 0

    count = sum(1 for _ in open(train_path))
    print(f"✓ Training dataset found: {count} samples")

    if val_path.exists():
        val_count = sum(1 for _ in open(val_path))
        print(f"✓ Validation dataset found: {val_count} samples")

    return count


def main():
    """Validate config and dataset, then print Colab instructions."""
    print("=" * 60)
    print("LLMOps Governance — Training Validation")
    print("=" * 60)
    print()

    config = validate_training_config()
    count = validate_dataset()
    print()

    model_name = config.get("model", {}).get("name", "Qwen/Qwen2.5-1.5B-Instruct")
    print(f"Base model: {model_name}")
    print(f"Method: QLoRA (4-bit quantized LoRA fine-tuning)")
    print()

    print("=" * 60)
    print("IMPORTANT: Fine-tuning must be done on Google Colab (free T4 GPU)")
    print("=" * 60)
    print()
    print("Steps:")
    print("  1. Open training/notebooks/colab_finetuning.ipynb in Google Colab")
    print("  2. Select Runtime → Change runtime type → T4 GPU")
    print("  3. Upload data/processed/train.jsonl and val.jsonl to Colab")
    print("  4. Run all cells")
    print("  5. Download the merged model and GGUF file")
    print(f"  6. Place the GGUF file in: ~/.cache/llmops-governance/models/")
    print()
    print("Do NOT attempt fine-tuning on this MacBook — it will be too slow")
    print("and may exhaust memory.")


if __name__ == "__main__":
    main()

