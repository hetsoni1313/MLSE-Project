"""Pydantic models for metrics, evaluations, and experiment tracking."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class RequestLogRecord(BaseModel):
    """A single logged request with all tracked metrics."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_id: str
    user_id: str | None = None
    route: str
    model_name: str
    input_text: str = ""
    predicted_label: str = ""
    ground_truth_label: str | None = None
    correct: bool | None = None
    valid_output: bool = True
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    tokens_per_second: float | None = None
    estimated_cost: float = 0.0
    fallback_used: bool = False
    fallback_reason: str | None = None
    error: str | None = None
    experiment_mode: str | None = None
    experiment_id: str | None = None


class EvaluationResult(BaseModel):
    """Summary of an evaluation run."""

    model_name: str
    dataset_hash: str = ""
    accuracy: float = 0.0
    macro_f1: float = 0.0
    invalid_rate: float = 0.0
    mean_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    cost_per_query: float = 0.0
    cost_per_1k_queries: float = 0.0
    total_requests: int = 0
    error_rate: float = 0.0
    throughput_qps: float = 0.0
    avg_input_tokens: float = 0.0
    avg_output_tokens: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    git_commit: str = ""
    config_snapshot: dict = Field(default_factory=dict)
    per_class_accuracy: dict[str, float] = Field(default_factory=dict)


class CostAnalysisResult(BaseModel):
    """Cost comparison and break-even analysis."""

    api_cost_per_query: float = 0.0
    api_cost_per_1k: float = 0.0
    local_cost_per_query: float = 0.0
    local_cost_per_1k: float = 0.0
    break_even_monthly_queries: float | None = None
    monthly_api_cost_at_1k: float = 0.0
    monthly_local_cost_at_1k: float = 0.0
    savings_pct_at_break_even: float = 0.0
    assumptions: dict = Field(default_factory=dict)
    sensitivity: dict = Field(default_factory=dict)


class ExperimentRunRecord(BaseModel):
    """Record of a traffic simulation experiment."""

    experiment_id: str
    name: str
    description: str = ""
    routing_mode: str = ""
    baseline_pct: int = 100
    local_pct: int = 0
    model_name: str = ""
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ended_at: datetime | None = None
    total_requests: int = 0
    config_snapshot: dict = Field(default_factory=dict)


class RollbackEventRecord(BaseModel):
    """Record of an automatic rollback event."""

    event_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    trigger_type: str  # "accuracy" | "error_rate" | "p95_latency"
    metric_value: float
    threshold_value: float
    previous_baseline_pct: int
    previous_local_pct: int
    new_baseline_pct: int = 100
    new_local_pct: int = 0
    evaluation_window: int = 100
    details: str = ""
