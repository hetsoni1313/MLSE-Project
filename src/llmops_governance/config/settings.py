"""Centralized application settings loaded from environment variables and YAML configs.

Uses pydantic-settings for typed, validated configuration with env-var overrides.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CONFIGS_DIR = _PROJECT_ROOT / "configs"


def _load_yaml(filename: str) -> dict[str, Any]:
    """Load a YAML config file from the configs/ directory."""
    path = _CONFIGS_DIR / filename
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    url: str = Field(
        default="sqlite+aiosqlite:///./data/llmops.db",
        alias="DATABASE_URL",
    )
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10


class RoutingSettings(BaseSettings):
    """Routing engine configuration."""

    mode: str = Field(default="baseline", description="baseline|weighted|shadow|canary")
    baseline_percentage: int = Field(default=100, ge=0, le=100)
    local_percentage: int = Field(default=0, ge=0, le=100)
    sticky_enabled: bool = True
    shadow_enabled: bool = False
    canary_stages: list[int] = Field(default_factory=lambda: [5, 25, 50, 100])

    @field_validator("local_percentage")
    @classmethod
    def percentages_sum_to_100(cls, v: int, info: Any) -> int:
        _TOTAL_PERCENT = 100  # noqa: N806
        baseline = info.data.get("baseline_percentage", 100)
        if baseline + v != _TOTAL_PERCENT:
            msg = f"baseline_percentage ({baseline}) + local_percentage ({v}) must equal 100"
            raise ValueError(msg)
        return v


class RollbackSettings(BaseSettings):
    """Automatic rollback thresholds."""

    enabled: bool = True
    evaluation_window: int = 100
    min_labelled_samples: int = 30
    min_accuracy: float = 0.85
    max_error_rate: float = 0.05
    max_p95_latency_ms: float = 5000.0
    check_interval_seconds: int = 30
    local_percentage_on_rollback: int = 0


class ModelSettings(BaseSettings):
    """Model serving configuration."""

    llama_server_url: str = Field(default="http://localhost:8081")
    local_model_timeout_ms: int = 10000
    max_concurrent_requests: int = 4
    context_size: int = 2048
    n_threads: int = 4
    model_cache_dir: str = Field(default=os.path.expanduser("~/.cache/llmops-governance/models"))


class PricingConfig(BaseSettings):
    """API pricing configuration."""

    provider: str = "openai"
    model: str = "gpt-4o-mini"
    input_price_per_mtok: float = 0.15  # USD per 1M input tokens
    output_price_per_mtok: float = 0.60  # USD per 1M output tokens
    currency: str = "USD"
    effective_date: str = "2024-07-18"
    source_url: str = "https://openai.com/api/pricing/"


class GatewaySettings(BaseSettings):
    """Gateway server configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    admin_api_key: str = Field(default="change-me-in-production", alias="ADMIN_API_KEY")
    fault_injection_enabled: bool = Field(default=False, alias="FAULT_INJECTION_ENABLED")


class Settings(BaseSettings):
    """Root application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app_name: str = "LLMOps Cost & Latency Governance Platform"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    routing: RoutingSettings = Field(default_factory=RoutingSettings)
    rollback: RollbackSettings = Field(default_factory=RollbackSettings)
    model: ModelSettings = Field(default_factory=ModelSettings)
    pricing: PricingConfig = Field(default_factory=PricingConfig)
    gateway: GatewaySettings = Field(default_factory=GatewaySettings)

    @classmethod
    def from_yaml(cls) -> Settings:
        """Load settings by merging YAML configs with env-var overrides."""
        routing_cfg = _load_yaml("routing.yaml")
        thresholds_cfg = _load_yaml("thresholds.yaml")
        pricing_cfg = _load_yaml("pricing.yaml")
        model_cfg = _load_yaml("model.yaml")

        overrides: dict[str, Any] = {}
        if routing_cfg.get("routing"):
            overrides["routing"] = routing_cfg["routing"]
        if thresholds_cfg.get("rollback"):
            overrides["rollback"] = thresholds_cfg["rollback"]
        if pricing_cfg.get("pricing"):
            overrides["pricing"] = pricing_cfg["pricing"]
        if model_cfg.get("model"):
            overrides["model"] = model_cfg["model"]

        return cls(**overrides)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    try:
        return Settings.from_yaml()
    except Exception:
        return Settings()
