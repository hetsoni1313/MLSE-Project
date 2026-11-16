"""Admin configuration endpoints — protected by API key."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request

from gateway.middleware.auth import require_admin_key
from gateway.routing.config import RoutingConfig
from llmops_governance.logging.setup import get_logger
from llmops_governance.metrics.database import get_db_manager
from llmops_governance.metrics.repository import RollbackRepository, RoutingConfigRepository
from llmops_governance.schemas.requests import AdminConfigUpdate

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/config")
async def get_config(
    request: Request,
    _: str = Depends(require_admin_key),
) -> dict:
    """Get current routing and gateway configuration."""
    routing = request.app.state.routing_engine.config
    return {
        "routing": routing.model_dump(),
        "rolled_back": request.app.state.routing_engine.is_rolled_back,
    }


@router.put("/config")
async def update_config(
    update: AdminConfigUpdate,
    request: Request,
    _: str = Depends(require_admin_key),
) -> dict:
    """Update routing configuration dynamically."""
    engine = request.app.state.routing_engine
    current = engine.config

    new_data = current.model_dump()
    if update.routing_mode is not None:
        new_data["mode"] = update.routing_mode
    if update.baseline_percentage is not None:
        new_data["baseline_percentage"] = update.baseline_percentage
    if update.local_percentage is not None:
        new_data["local_percentage"] = update.local_percentage
    if update.shadow_enabled is not None:
        new_data["shadow_enabled"] = update.shadow_enabled

    try:
        new_config = RoutingConfig(**new_data)
    except Exception as e:
        return {"error": str(e), "status": "rejected"}

    old = engine.update_config(new_config)

    # Log config change to DB
    try:
        db = getattr(request.app.state, "db_manager", None) or get_db_manager()
        async with db.get_session() as session:
            repo = RoutingConfigRepository(session)
            await repo.save(
                {
                    "mode": new_config.mode,
                    "baseline_pct": new_config.baseline_percentage,
                    "local_pct": new_config.local_percentage,
                    "changed_by": "admin",
                    "reason": update.reason or "Admin config update",
                }
            )
    except Exception:
        logging.exception("config_history_save_failed")

    logger.info(
        "admin_config_updated",
        old_mode=old.mode,
        new_mode=new_config.mode,
        reason=update.reason,
    )

    return {
        "status": "updated",
        "previous": old.model_dump(),
        "current": new_config.model_dump(),
    }


@router.get("/rollback-history")
async def rollback_history(
    request: Request,
    _: str = Depends(require_admin_key),
) -> dict:
    """Get rollback event history."""
    try:
        db = getattr(request.app.state, "db_manager", None) or get_db_manager()
        async with db.get_session() as session:
            repo = RollbackRepository(session)
            events = await repo.get_recent(20)
            return {
                "rollback_events": [
                    {
                        "event_id": e.event_id,
                        "timestamp": str(e.timestamp),
                        "trigger_type": e.trigger_type,
                        "metric_value": e.metric_value,
                        "threshold_value": e.threshold_value,
                        "previous_local_pct": e.previous_local_pct,
                        "details": e.details,
                    }
                    for e in events
                ]
            }
    except Exception as e:
        return {"error": str(e), "rollback_events": []}


@router.post("/check-rollback")
async def trigger_rollback_check(
    request: Request,
    _: str = Depends(require_admin_key),
) -> dict:
    """Manually trigger an immediate rollback evaluation."""
    logger_service = getattr(request.app.state, "request_logger", None)
    if logger_service is not None:
        await logger_service.flush()

    monitor = getattr(request.app.state, "rollback_monitor", None)
    if monitor is None:
        return {"error": "Rollback monitor not active"}
    result = await monitor.check_now()
    return {"status": "evaluated", "result": result}


@router.post("/reset-rollback")
async def reset_rollback(
    update: AdminConfigUpdate,
    request: Request,
    _: str = Depends(require_admin_key),
) -> dict:
    """Explicitly recover from a rollback state."""
    engine = request.app.state.routing_engine
    if not engine.is_rolled_back:
        return {"status": "not_in_rollback_state"}

    bp = update.baseline_percentage if update.baseline_percentage is not None else 90
    lp = update.local_percentage if update.local_percentage is not None else 10
    mode = update.routing_mode or ("baseline" if lp == 0 else "weighted")

    new_config = RoutingConfig(
        mode=mode,
        baseline_percentage=bp,
        local_percentage=lp,
    )
    engine.recover_from_rollback(new_config)

    logger.info("admin_rollback_recovery", new_config=new_config.model_dump())
    return {
        "status": "recovered",
        "new_config": new_config.model_dump(),
    }


@router.post("/faults")
async def toggle_faults(
    request: Request,
    body: dict,
    _: str = Depends(require_admin_key),
) -> dict:
    """Toggle fault injection modes (dev only)."""
    fault_backend = getattr(request.app.state, "fault_backend", None)
    if fault_backend is None:
        return {"error": "Fault injection not available"}

    action = body.get("action", "")
    if action == "enable":
        fault_backend.enable()
        return {"status": "enabled"}
    if action == "disable":
        fault_backend.disable()
        return {"status": "disabled"}
    if action == "set":
        fault_type = body.get("fault_type", "")
        enabled = body.get("enabled", True)
        kwargs = {k: v for k, v in body.items() if k not in ("action", "fault_type", "enabled")}
        fault_backend.set_fault(fault_type, enabled, **kwargs)
        return {"status": "set", "fault_type": fault_type, "enabled": enabled}
    return {"error": f"Unknown action: {action}"}
