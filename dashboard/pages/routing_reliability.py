"""Page 5: Routing & Reliability — fallbacks, rollbacks, traffic split."""

from __future__ import annotations

import streamlit as st
import plotly.express as px

from dashboard.services.db_service import DashboardDB


def render() -> None:
    """Render routing and reliability page."""
    st.title("🔀 Routing & Reliability")

    db = DashboardDB()
    stats = db.get_summary_stats()

    # Current routing info
    st.subheader("Current Status")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Requests", f"{stats['total_requests']:,}")
    with col2:
        st.metric("Fallbacks", str(stats["fallback_count"]))
    with col3:
        error_rate = stats["error_count"] / stats["total_requests"] * 100 if stats["total_requests"] > 0 else 0
        st.metric("Error Rate", f"{error_rate:.1f}%")
    with col4:
        st.metric("Rollback Events", str(stats["rollback_count"]))

    st.markdown("---")

    # Traffic distribution
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Traffic Distribution")
        if stats["total_requests"] > 0:
            fig = px.pie(
                values=[stats["baseline_requests"], stats["local_requests"]],
                names=["Baseline", "Local"],
                color_discrete_sequence=["#636EFA", "#00CC96"],
            )
            fig.update_layout(height=300, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

    # Rollback events
    with col2:
        st.subheader("Rollback Events")
        rb_df = db.get_rollback_events()
        if not rb_df.empty:
            display_cols = [c for c in ["timestamp", "trigger_type", "metric_value", "threshold_value", "details"] if c in rb_df.columns]
            st.dataframe(rb_df[display_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No rollback events recorded.")

    # Fallback timeline
    st.subheader("Recent Requests with Fallback Status")
    df = db.get_requests_df(limit=200)
    if not df.empty and "fallback_used" in df.columns:
        fallback_df = df[["timestamp", "route", "fallback_used", "fallback_reason", "latency_ms", "predicted_label"]].copy()
        st.dataframe(fallback_df.head(50), use_container_width=True, hide_index=True)

        # Fallback frequency over time
        if "timestamp" in fallback_df.columns:
            fallback_df["timestamp"] = fallback_df["timestamp"].astype(str)
            fallback_counts = df.groupby("route").agg(
                total=("route", "count"),
                fallbacks=("fallback_used", "sum"),
            ).reset_index()
            if not fallback_counts.empty:
                fig = px.bar(fallback_counts, x="route", y=["total", "fallbacks"], barmode="group")
                fig.update_layout(height=300, yaxis_title="Count")
                st.plotly_chart(fig, use_container_width=True)

