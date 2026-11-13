"""Page 1: Executive Overview — KPI cards and traffic summary."""

from __future__ import annotations

import streamlit as st

from dashboard.components.kpi_cards import kpi_row
from dashboard.services.db_service import DashboardDB


def render() -> None:
    """Render the executive overview page."""
    st.title("📊 Executive Overview")

    db = DashboardDB()
    stats = db.get_summary_stats()

    if stats["total_requests"] == 0:
        st.info("No requests logged yet. Start the gateway and send traffic to see metrics.")
        st.markdown("### Quick Start")
        st.code("# Start gateway\nuvicorn gateway.main:app --port 8000\n\n# Send a test request\ncurl -X POST http://localhost:8000/classify -H 'Content-Type: application/json' -d '{\"message\": \"How do I change my PIN?\"}'", language="bash")
        return

    # KPI Row 1
    kpi_row([
        {"label": "Total Requests", "value": f"{stats['total_requests']:,}"},
        {"label": "Baseline Traffic", "value": f"{stats['baseline_requests']:,}"},
        {"label": "Local Traffic", "value": f"{stats['local_requests']:,}"},
        {"label": "Accuracy", "value": f"{stats['accuracy']:.1%}" if stats['accuracy'] > 0 else "N/A"},
    ])

    # KPI Row 2
    kpi_row([
        {"label": "Avg Latency (ms)", "value": f"{stats['avg_latency_ms']:.1f}"},
        {"label": "Total Cost", "value": f"${stats['total_cost']:.4f}"},
        {"label": "Fallbacks", "value": str(stats["fallback_count"])},
        {"label": "Rollbacks", "value": str(stats["rollback_count"])},
    ])

    st.markdown("---")

    # Traffic distribution
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Traffic Distribution")
        import plotly.express as px

        dist_data = {"Route": ["Baseline", "Local"], "Requests": [stats["baseline_requests"], stats["local_requests"]]}
        if sum(dist_data["Requests"]) > 0:
            fig = px.pie(dist_data, values="Requests", names="Route", color_discrete_sequence=["#636EFA", "#00CC96"])
            fig.update_layout(height=300, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Recent Requests")
        df = db.get_requests_df(limit=10)
        if not df.empty:
            display_cols = [c for c in ["timestamp", "route", "predicted_label", "latency_ms", "fallback_used"] if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No data available")

