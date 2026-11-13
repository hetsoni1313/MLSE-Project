"""Page 6: Experiments — compare experiment results."""

from __future__ import annotations

import streamlit as st
import plotly.express as px

from dashboard.services.db_service import DashboardDB


def render() -> None:
    """Render experiments page."""
    st.title("🧪 Experiments")

    db = DashboardDB()
    exp_df = db.get_experiments()

    if exp_df.empty:
        st.info("No experiments recorded yet. Run traffic scenarios to create experiment data.")
        st.markdown("""
        ### How to run experiments
        ```bash
        # Run the traffic replay engine
        python -m loadtest.replay --scenario baseline --requests 100
        python -m loadtest.replay --scenario shadow --requests 100
        python -m loadtest.replay --scenario canary_50 --requests 100
        ```
        """)
        return

    st.subheader("Experiment Runs")
    st.dataframe(exp_df, use_container_width=True, hide_index=True)

    # Select experiment for detail view
    if "experiment_id" in exp_df.columns:
        selected = st.selectbox("Select experiment for details", exp_df["experiment_id"].tolist())
        if selected:
            exp_requests = db.get_requests_df(limit=5000)
            if not exp_requests.empty and "experiment_id" in exp_requests.columns:
                filtered = exp_requests[exp_requests.get("experiment_id") == selected]
                if not filtered.empty:
                    st.subheader(f"Experiment: {selected}")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Requests", len(filtered))
                    with col2:
                        avg_lat = filtered["latency_ms"].mean()
                        st.metric("Avg Latency", f"{avg_lat:.1f} ms")
                    with col3:
                        if "correct" in filtered.columns:
                            labelled = filtered.dropna(subset=["correct"])
                            acc = labelled["correct"].mean() if len(labelled) > 0 else 0
                            st.metric("Accuracy", f"{acc:.1%}")

                    # Latency distribution for this experiment
                    fig = px.histogram(filtered, x="latency_ms", color="route", nbins=30)
                    fig.update_layout(height=300, xaxis_title="Latency (ms)")
                    st.plotly_chart(fig, use_container_width=True)

