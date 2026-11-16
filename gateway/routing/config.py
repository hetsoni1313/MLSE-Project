"""Routing configuration model with validation."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class RoutingConfig(BaseModel):
    """Validated routing configuration."""

    mode: str = Field(default="baseline", pattern=r"^(baseline|weighted|shadow|canary)$")
    baseline_percentage: int = Field(default=100, ge=0, le=100)
    local_percentage: int = Field(default=0, ge=0, le=100)
    sticky_enabled: bool = True
    shadow_enabled: bool = False
    canary_stages: list[int] = Field(default_factory=lambda: [5, 25, 50, 100])
    current_canary_stage: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_percentages(self) -> RoutingConfig:
        """Ensure percentages sum to 100."""
        _TOTAL_PERCENT = 100  # noqa: N806
        if (
            self.mode in ("weighted", "canary")
            and self.baseline_percentage + self.local_percentage != _TOTAL_PERCENT
        ):
            msg = (
                f"baseline_percentage ({self.baseline_percentage}) + "
                f"local_percentage ({self.local_percentage}) must equal 100"
            )
            raise ValueError(msg)
        return self

    def to_baseline_only(self) -> RoutingConfig:
        """Create a baseline-only config (used during rollback)."""
        return RoutingConfig(
            mode="baseline",
            baseline_percentage=100,
            local_percentage=0,
            sticky_enabled=self.sticky_enabled,
            shadow_enabled=False,
        )
