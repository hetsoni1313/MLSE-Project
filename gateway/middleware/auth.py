"""API key authentication for admin endpoints."""

from __future__ import annotations

import os

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_admin_key(
    api_key: str | None = Security(_api_key_header),
) -> str:
    """Dependency that validates the admin API key.

    Raises HTTPException 401/403 if the key is missing or invalid.
    """
    expected = os.getenv("ADMIN_API_KEY", "change-me-in-production")

    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    if api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return api_key
