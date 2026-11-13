"""SQLAlchemy ORM models for the metrics database."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class RequestLog(Base):
    """Stores every inference request through the gateway."""

    __tablename__ = "request_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    route: Mapped[str] = mapped_column(String(32), index=True)
    model_name: Mapped[str] = mapped_column(String(128))
    input_text: Mapped[str] = mapped_column(Text, default="")
    predicted_label: Mapped[str] = mapped_column(String(128), default="")
    ground_truth_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    valid_output: Mapped[bool] = mapped_column(Boolean, default=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    tokens_per_second: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    fallback_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    experiment_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    experiment_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    __table_args__ = (
        Index("idx_request_logs_ts_route", "timestamp", "route"),
        Index("idx_request_logs_experiment", "experiment_id", "timestamp"),
    )


class ExperimentRun(Base):
    """Records a traffic simulation experiment."""

    __tablename__ = "experiment_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text, default="")
    routing_mode: Mapped[str] = mapped_column(String(32), default="")
    baseline_pct: Mapped[int] = mapped_column(Integer, default=100)
    local_pct: Mapped[int] = mapped_column(Integer, default=0)
    model_name: Mapped[str] = mapped_column(String(128), default="")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    config_snapshot: Mapped[str] = mapped_column(Text, default="{}")


class RollbackEvent(Base):
    """Records an automatic rollback event."""

    __tablename__ = "rollback_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    trigger_type: Mapped[str] = mapped_column(String(32))
    metric_value: Mapped[float] = mapped_column(Float)
    threshold_value: Mapped[float] = mapped_column(Float)
    previous_baseline_pct: Mapped[int] = mapped_column(Integer)
    previous_local_pct: Mapped[int] = mapped_column(Integer)
    new_baseline_pct: Mapped[int] = mapped_column(Integer, default=100)
    new_local_pct: Mapped[int] = mapped_column(Integer, default=0)
    evaluation_window: Mapped[int] = mapped_column(Integer, default=100)
    details: Mapped[str] = mapped_column(Text, default="")


class EvaluationSummary(Base):
    """Stores evaluation results for model comparison."""

    __tablename__ = "evaluation_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    model_name: Mapped[str] = mapped_column(String(128), index=True)
    dataset_hash: Mapped[str] = mapped_column(String(64), default="")
    accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    macro_f1: Mapped[float] = mapped_column(Float, default=0.0)
    invalid_rate: Mapped[float] = mapped_column(Float, default=0.0)
    mean_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    p50_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    p95_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    cost_per_query: Mapped[float] = mapped_column(Float, default=0.0)
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    git_commit: Mapped[str] = mapped_column(String(40), default="")


class RoutingConfigHistory(Base):
    """Audit trail for routing configuration changes."""

    __tablename__ = "routing_config_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    mode: Mapped[str] = mapped_column(String(32))
    baseline_pct: Mapped[int] = mapped_column(Integer)
    local_pct: Mapped[int] = mapped_column(Integer)
    changed_by: Mapped[str] = mapped_column(String(128), default="system")
    reason: Mapped[str] = mapped_column(Text, default="")


class CostAssumption(Base):
    """Stores API pricing assumptions for cost calculations."""

    __tablename__ = "cost_assumptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    input_price_per_token: Mapped[float] = mapped_column(Float)
    output_price_per_token: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    effective_date: Mapped[str] = mapped_column(String(32))
    source_url: Mapped[str] = mapped_column(String(512), default="")

