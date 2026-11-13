"""Pydantic models for API requests and responses."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class ClassifyRequest(BaseModel):
    """Intent classification request."""

    message: str = Field(..., min_length=1, max_length=2000, description="Customer message")
    user_id: Optional[str] = Field(default=None, description="User ID for sticky routing")
    request_id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique request identifier",
    )
    ground_truth: Optional[str] = Field(
        default=None,
        description="Ground truth label (for evaluation harness only)",
    )


class ClassifyResponse(BaseModel):
    """Intent classification response."""

    request_id: str
    prediction: str
    route: str  # "baseline" | "local"
    latency_ms: float
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    model_name: str
    valid_output: bool = True
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    shadow_prediction: Optional[str] = Field(
        default=None, description="Shadow model prediction (when shadow mode active)"
    )


class AdminConfigUpdate(BaseModel):
    """Routing configuration update request."""

    routing_mode: Optional[str] = Field(
        default=None, description="baseline|weighted|shadow|canary"
    )
    baseline_percentage: Optional[int] = Field(default=None, ge=0, le=100)
    local_percentage: Optional[int] = Field(default=None, ge=0, le=100)
    shadow_enabled: Optional[bool] = None
    reason: Optional[str] = Field(default=None, description="Reason for config change")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str  # "healthy" | "degraded" | "unhealthy"
    gateway: bool = True
    database: bool = False
    local_model: bool = False
    baseline_api: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "0.1.0"
    details: dict = Field(default_factory=dict)

