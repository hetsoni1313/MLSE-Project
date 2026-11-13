"""Reusable KPI card components for the dashboard."""

from __future__ import annotations

import streamlit as st


def kpi_card(label: str, value: str | float | int, delta: str | None = None, color: str = "normal") -> None:
    """Render a KPI metric card."""
    st.metric(label=label, value=value, delta=delta)


def kpi_row(metrics: list[dict]) -> None:
    """Render a row of KPI cards."""
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            kpi_card(
                label=m["label"],
                value=m["value"],
                delta=m.get("delta"),
            )

