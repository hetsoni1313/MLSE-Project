"""Dataset formatting for Banking77 instruction fine-tuning."""

from __future__ import annotations


SYSTEM_PROMPT = (
    "You are a banking customer intent classifier. "
    "Given a customer message, respond with exactly one intent label from the Banking77 dataset. "
    "Output only the intent label, nothing else."
)


def format_instruction(text: str, label: str) -> dict[str, str]:
    """Format a Banking77 example as a chat instruction pair."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
            {"role": "assistant", "content": label},
        ]
    }


def format_dataset(examples: list[dict]) -> list[dict]:
    """Format a list of Banking77 examples for training."""
    return [format_instruction(ex["text"], ex["label"]) for ex in examples]

