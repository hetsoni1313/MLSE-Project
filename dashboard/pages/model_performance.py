"""Page 2: Model Performance — Accuracy, F1, per-class comparisons."""

from __future__ import annotations

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from dashboard.services.db_service import DashboardDB


def render() -> None:
    """Render model performance comparison page."""
    st.title("🤖 Model Performance")

    db = DashboardDB()
    df = db.get_requests_df(limit=5000)

    if df.empty or "ground_truth_label" not in df.columns:
        st.info("No labelled prediction data available yet. Run evaluation scenarios to populate.")
        return

    labelled = df.dropna(subset=["ground_truth_label"])
    if labelled.empty:
        st.info("No ground-truth labels in logged requests. Use the evaluation harness with ground_truth parameter.")
        return

    # Per-route accuracy
    st.subheader("Accuracy by Route")
    routes = labelled.groupby("route").apply(
        lambda g: pd.Series({
            "accuracy": (g["correct"] == True).sum() / len(g) if len(g) > 0 else 0,  # noqa: E712
            "total": len(g),
            "correct": (g["correct"] == True).sum(),  # noqa: E712
        })
    ).reset_index()

    if not routes.empty:
        fig = px.bar(routes, x="route", y="accuracy", text="accuracy",
                     color="route", color_discrete_map={"baseline": "#636EFA", "local": "#00CC96"})
        fig.update_traces(texttemplate='%{text:.1%}', textposition='outside')
        fig.update_layout(yaxis_range=[0, 1.1], height=400, yaxis_title="Accuracy")
        st.plotly_chart(fig, use_container_width=True)

    # Per-class performance (top/bottom)
    st.subheader("Per-Class Accuracy (Top & Bottom 10)")
    if "predicted_label" in labelled.columns:
        class_acc = labelled.groupby("ground_truth_label").apply(
            lambda g: (g["correct"] == True).sum() / len(g) if len(g) > 0 else 0  # noqa: E712
        ).reset_index(name="accuracy")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Top 10 classes**")
            top10 = class_acc.nlargest(10, "accuracy")
            fig = px.bar(top10, x="accuracy", y="ground_truth_label", orientation="h",
                        color_discrete_sequence=["#00CC96"])
            fig.update_layout(height=350, xaxis_range=[0, 1.1], yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Bottom 10 classes**")
            bottom10 = class_acc.nsmallest(10, "accuracy")
            fig = px.bar(bottom10, x="accuracy", y="ground_truth_label", orientation="h",
                        color_discrete_sequence=["#EF553B"])
            fig.update_layout(height=350, xaxis_range=[0, 1.1], yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

    # Valid vs Invalid predictions
    st.subheader("Prediction Validity")
    if "valid_output" in labelled.columns:
        validity = labelled.groupby(["route", "valid_output"]).size().reset_index(name="count")
        fig = px.bar(validity, x="route", y="count", color="valid_output",
                     barmode="group", color_discrete_map={True: "#00CC96", False: "#EF553B"})
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

