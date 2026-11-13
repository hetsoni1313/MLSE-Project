"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from llmops_governance.schemas.requests import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Basic health check — returns OK if the gateway is running."""
    return HealthResponse(
        status="healthy",
        gateway=True,
        version="0.1.0",
    )


@router.get("/ready", response_model=HealthResponse)
async def readiness(request: Request) -> HealthResponse:
    """Readiness check — verifies database and backend connectivity."""
    app_state = request.app.state
    details: dict = {}

    # Check database
    db_ok = False
    try:
        db = app_state.db_manager
        async with db.get_session() as session:
            await session.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
            db_ok = True
    except Exception as e:
        details["database_error"] = str(e)

    # Check local model
    local_ok = False
    try:
        local_ok = await app_state.local_backend.health_check()
    except Exception:
        pass

    # Check baseline
    baseline_ok = False
    try:
        baseline_ok = await app_state.baseline_backend.health_check()
    except Exception:
        pass

    status = "healthy" if db_ok else "degraded"
    if not db_ok:
        status = "unhealthy"

    return HealthResponse(
        status=status,
        gateway=True,
        database=db_ok,
        local_model=local_ok,
        baseline_api=baseline_ok,
        details=details,
    )

