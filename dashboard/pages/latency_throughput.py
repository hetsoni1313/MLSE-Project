"""Page 3: Latency & Throughput."""

from __future__ import annotations

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from dashboard.services.db_service import DashboardDB


def render() -> None:
    """Render latency and throughput analysis page."""
    st.title("⏱️ Latency & Throughput")

    db = DashboardDB()
    df = db.get_latency_by_route()

    if df.empty:
        st.info("No latency data available yet.")
        return

    # Latency distribution by route
    st.subheader("Latency Distribution by Route")
    fig = px.histogram(df, x="latency_ms", color="route", nbins=50, barmode="overlay",
                       opacity=0.7, color_discrete_map={"baseline": "#636EFA", "local": "#00CC96"})
    fig.update_layout(xaxis_title="Latency (ms)", yaxis_title="Count", height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Percentile comparison
    st.subheader("Latency Percentiles")
    col1, col2 = st.columns(2)

    for route in df["route"].unique():
        route_df = df[df["route"] == route]
        lats = sorted(route_df["latency_ms"].tolist())
        n = len(lats)
        if n == 0:
            continue

        stats = {
            "p50": lats[int(n * 0.50)],
            "p95": lats[min(int(n * 0.95), n - 1)],
            "p99": lats[min(int(n * 0.99), n - 1)],
            "mean": sum(lats) / n,
        }

        target = col1 if route == "baseline" else col2
        with target:
            st.markdown(f"**{route.title()} ({n} requests)**")
            st.metric("p50", f"{stats['p50']:.1f} ms")
            st.metric("p95", f"{stats['p95']:.1f} ms")
            st.metric("p99", f"{stats['p99']:.1f} ms")
            st.metric("Mean", f"{stats['mean']:.1f} ms")

    # Box plot comparison
    st.subheader("Latency Box Plot")
    fig = px.box(df, x="route", y="latency_ms", color="route",
                 color_discrete_map={"baseline": "#636EFA", "local": "#00CC96"})
    fig.update_layout(yaxis_title="Latency (ms)", height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Throughput
    st.subheader("Tokens Per Second")
    full_df = db.get_requests_df(limit=2000)
    if not full_df.empty and "tokens_per_second" in full_df.columns:
        tps_df = full_df.dropna(subset=["tokens_per_second"])
        if not tps_df.empty:
            fig = px.histogram(tps_df, x="tokens_per_second", color="route", nbins=30, barmode="overlay")
            fig.update_layout(xaxis_title="Tokens/Second", height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No tokens-per-second data recorded.")

