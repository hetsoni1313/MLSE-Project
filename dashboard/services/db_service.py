"""Dashboard database service — sync queries for Streamlit."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Generator

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


def _get_sync_url() -> str:
    """Convert async DB URL to sync for Streamlit."""
    url = os.getenv("DATABASE_URL", "sqlite:///./data/llmops.db")
    url = url.replace("sqlite+aiosqlite", "sqlite")
    url = url.replace("postgresql+asyncpg", "postgresql")
    return url


class DashboardDB:
    """Sync database access for the Streamlit dashboard."""

    def __init__(self) -> None:
        url = _get_sync_url()
        self._engine = create_engine(url, echo=False)
        self._Session = sessionmaker(bind=self._engine)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        s = self._Session()
        try:
            yield s
        finally:
            s.close()

    def get_summary_stats(self) -> dict[str, Any]:
        """Get overall gateway statistics."""
        try:
            with self.session() as s:
                row = s.execute(text("""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN route = 'baseline' THEN 1 ELSE 0 END) as baseline_count,
                        SUM(CASE WHEN route = 'local' THEN 1 ELSE 0 END) as local_count,
                        AVG(latency_ms) as avg_latency,
                        SUM(estimated_cost) as total_cost,
                        SUM(CASE WHEN fallback_used = 1 THEN 1 ELSE 0 END) as fallback_count,
                        SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) as error_count
                    FROM request_logs
                """)).fetchone()

                if not row or row[0] == 0:
                    return self._empty_stats()

                # Accuracy (only labelled)
                acc_row = s.execute(text("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) as correct
                    FROM request_logs WHERE ground_truth_label IS NOT NULL
                """)).fetchone()

                accuracy = acc_row[1] / acc_row[0] if acc_row and acc_row[0] > 0 else 0.0

                # Rollback count
                rb_count = s.execute(text(
                    "SELECT COUNT(*) FROM rollback_events"
                )).scalar() or 0

                return {
                    "total_requests": row[0],
                    "baseline_requests": row[1] or 0,
                    "local_requests": row[2] or 0,
                    "avg_latency_ms": round(row[3] or 0, 2),
                    "total_cost": round(row[4] or 0, 6),
                    "fallback_count": row[5] or 0,
                    "error_count": row[6] or 0,
                    "accuracy": round(accuracy, 4),
                    "rollback_count": rb_count,
                }
        except Exception:
            return self._empty_stats()

    def _empty_stats(self) -> dict[str, Any]:
        return {
            "total_requests": 0, "baseline_requests": 0, "local_requests": 0,
            "avg_latency_ms": 0, "total_cost": 0, "fallback_count": 0,
            "error_count": 0, "accuracy": 0, "rollback_count": 0,
        }

    def get_requests_df(self, limit: int = 1000) -> pd.DataFrame:
        """Get recent requests as DataFrame."""
        try:
            return pd.read_sql(
                f"SELECT * FROM request_logs ORDER BY timestamp DESC LIMIT {limit}",
                self._engine,
            )
        except Exception:
            return pd.DataFrame()

    def get_latency_by_route(self) -> pd.DataFrame:
        """Get latency percentiles by route."""
        try:
            return pd.read_sql(
                "SELECT route, latency_ms FROM request_logs WHERE latency_ms > 0",
                self._engine,
            )
        except Exception:
            return pd.DataFrame()

    def get_cost_by_route(self) -> dict[str, float]:
        """Get total cost by route."""
        try:
            with self.session() as s:
                rows = s.execute(text(
                    "SELECT route, SUM(estimated_cost) as total, COUNT(*) as cnt "
                    "FROM request_logs GROUP BY route"
                )).fetchall()
                return {r[0]: {"total_cost": r[1] or 0, "count": r[2]} for r in rows}
        except Exception:
            return {}

    def get_rollback_events(self) -> pd.DataFrame:
        """Get rollback events."""
        try:
            return pd.read_sql(
                "SELECT * FROM rollback_events ORDER BY timestamp DESC",
                self._engine,
            )
        except Exception:
            return pd.DataFrame()

    def get_experiments(self) -> pd.DataFrame:
        """Get experiment runs."""
        try:
            return pd.read_sql(
                "SELECT * FROM experiment_runs ORDER BY started_at DESC",
                self._engine,
            )
        except Exception:
            return pd.DataFrame()

