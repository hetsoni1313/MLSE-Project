"""Hashing utilities for deterministic routing and file integrity checks."""

from __future__ import annotations

import hashlib
from pathlib import Path

__all__ = [
    "file_hash_sha256",
    "compute_file_hash",
    "route_for_user",
    "consistent_hash",
    "sticky_hash",
]

_CHUNK_SIZE = 8192


def file_hash_sha256(file_path: str | Path) -> str:
    """Compute the SHA-256 hex digest of a file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if path.is_dir():
        raise IsADirectoryError(f"Expected a file, got a directory: {path}")
    sha256 = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(_CHUNK_SIZE)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


# Alias for tests
compute_file_hash = file_hash_sha256


def sticky_hash(key: str, num_buckets: int, seed: int = 0) -> int:
    """Deterministic hash of a key to a bucket in [0, num_buckets).

    Used for sticky routing — same key always maps to same bucket.
    """
    if num_buckets < 1:
        raise ValueError(f"num_buckets must be >= 1, got {num_buckets}")
    digest = hashlib.sha256(f"{key}{seed}".encode("utf-8")).hexdigest()
    return int(digest, 16) % num_buckets


# Alias
consistent_hash = sticky_hash


def route_for_user(
    user_id: str,
    local_percentage: int,
    hash_seed: int = 42,
) -> str:
    """Deterministic sticky routing of a user to local or cloud."""
    if not 0 <= local_percentage <= 100:
        raise ValueError(f"local_percentage must be between 0 and 100, got {local_percentage}")
    digest = hashlib.sha256(f"{user_id}{hash_seed}".encode("utf-8")).hexdigest()
    bucket = int(digest, 16) % 100
    return "local" if bucket < local_percentage else "cloud"
