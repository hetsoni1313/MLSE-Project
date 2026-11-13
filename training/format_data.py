"""Format Banking77 data into chat-completion training format.

Converts the HuggingFace Banking77 dataset into the instruction-tuning
format expected by Qwen2.5 fine-tuning: chat-ml style messages.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llmops_governance.core.constants import BANKING77_LABELS

SYSTEM_PROMPT = (
    "You are a banking customer service intent classifier. "
    "Given a customer message, respond with exactly one intent label from the Banking77 taxonomy. "
    "Output only the label, nothing else."
)


def format_sample(text: str, label_idx: int) -> dict:
    """Format a single sample into chat-completion format."""
    label = BANKING77_LABELS[label_idx] if label_idx < len(BANKING77_LABELS) else f"unknown_{label_idx}"
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
            {"role": "assistant", "content": label},
        ]
    }


def format_dataset(input_path: Path, output_path: Path) -> int:
    """Convert a JSONL file of {text, label} to chat format."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0

    with open(input_path) as fin, open(output_path, "w") as fout:
        for line in fin:
            if not line.strip():
                continue
            sample = json.loads(line)
            formatted = format_sample(sample["text"], sample["label"])
            fout.write(json.dumps(formatted) + "\n")
            count += 1

    return count


def main():
    """Format train and validation datasets."""
    data_dir = Path(__file__).parent.parent / "data"
    processed_dir = data_dir / "processed"
    formatted_dir = data_dir / "formatted"

    if not processed_dir.exists():
        print("ERROR: Processed data directory not found.")
        print("  Run: python scripts/download_data.py && python scripts/prepare_data.py")
        sys.exit(1)

    for split in ("train", "val", "test"):
        input_path = processed_dir / f"{split}.jsonl"
        if not input_path.exists():
            print(f"  Skipping {split} — file not found")
            continue

        output_path = formatted_dir / f"{split}_chat.jsonl"
        count = format_dataset(input_path, output_path)
        print(f"  ✓ Formatted {count} {split} samples → {output_path}")

    print("\nFormatted data ready for fine-tuning upload to Colab.")


if __name__ == "__main__":
    main()
