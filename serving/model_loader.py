"""Model loader — resolves model paths and validates GGUF files."""

from __future__ import annotations

import os
from pathlib import Path


def get_model_cache_dir() -> Path:
    """Get the model cache directory."""
    return Path(os.getenv("MODEL_CACHE_DIR", os.path.expanduser("~/.cache/llmops-governance/models")))


def find_gguf_model(name: str = "qwen2.5-1.5b-instruct-q4_k_m.gguf") -> Path | None:
    """Find a GGUF model file in the cache directory."""
    cache_dir = get_model_cache_dir()
    model_path = cache_dir / name
    if model_path.exists():
        return model_path
    # Search for any matching .gguf file
    for path in cache_dir.glob("*.gguf"):
        if name.replace(".gguf", "") in path.stem:
            return path
    return None


def validate_gguf(path: Path) -> dict:
    """Basic validation of a GGUF file."""
    if not path.exists():
        return {"valid": False, "error": "File not found"}
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb < 10:
        return {"valid": False, "error": f"File too small: {size_mb:.1f} MB"}
    return {"valid": True, "size_mb": round(size_mb, 1), "path": str(path)}

