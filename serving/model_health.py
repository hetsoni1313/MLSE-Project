"""Health checking for the llama.cpp server."""

from __future__ import annotations

import os
import httpx


async def check_llama_health(server_url: str | None = None) -> dict:
    """Check if the llama.cpp server is healthy."""
    url = server_url or os.getenv("LLAMA_SERVER_URL", "http://localhost:8081")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{url}/health")
            return {"healthy": resp.status_code == 200, "url": url}
    except Exception as e:
        return {"healthy": False, "url": url, "error": str(e)}

