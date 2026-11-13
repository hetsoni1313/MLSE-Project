"""Page 4: Cost Intelligence — break-even analysis and cost comparison."""

from __future__ import annotations

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

from dashboard.services.db_service import DashboardDB
from evaluation.cost import CostCalculator, PricingAssumptions


def render() -> None:
    """Render cost intelligence page."""
    st.title("💰 Cost Intelligence")

    db = DashboardDB()
    cost_data = db.get_cost_by_route()

    # Interactive assumptions
    st.sidebar.subheader("💰 Cost Assumptions")
    api_input_price = st.sidebar.number_input("API input price ($/1M tokens)", value=0.15, step=0.01, format="%.2f")
    api_output_price = st.sidebar.number_input("API output price ($/1M tokens)", value=0.60, step=0.01, format="%.2f")
    machine_cost = st.sidebar.number_input("Machine cost ($/hour)", value=0.25, step=0.01, format="%.2f")
    local_qph = st.sidebar.number_input("Local queries/hour", value=200, step=10)

    assumptions = PricingAssumptions(
        api_input_price_per_mtok=api_input_price,
        api_output_price_per_mtok=api_output_price,
        machine_cost_per_hour_base=machine_cost,
        local_queries_per_hour=float(local_qph),
    )
    calc = CostCalculator(assumptions)

    # Cost per 1K queries comparison
    st.subheader("Cost per 1,000 Queries")
    api_cost_1k = calc.cost_per_1k(calc.api_query_cost())
    local_cost_1k = calc.cost_per_1k(calc.local_query_cost("base"))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("API Cost / 1K", f"${api_cost_1k:.4f}")
    with col2:
        st.metric("Local Cost / 1K", f"${local_cost_1k:.4f}")
    with col3:
        savings = ((api_cost_1k - local_cost_1k) / api_cost_1k * 100) if api_cost_1k > 0 else 0
        st.metric("Savings", f"{savings:.1f}%")

    # Bar chart comparison
    fig = go.Figure(data=[
        go.Bar(name="API", x=["Cost per 1K Queries"], y=[api_cost_1k], marker_color="#636EFA"),
        go.Bar(name="Local", x=["Cost per 1K Queries"], y=[local_cost_1k], marker_color="#00CC96"),
    ])
    fig.update_layout(barmode="group", yaxis_title="USD", height=300)
    st.plotly_chart(fig, use_container_width=True)

    # Break-even analysis
    st.subheader("Break-Even Analysis")
    be = calc.break_even_monthly_queries("base")
    if be and be > 0:
        st.success(f"Break-even at **{be:,.0f}** queries/month with current assumptions")

        # Cumulative cost chart
        queries = np.linspace(0, be * 2, 100)
        api_costs = queries * calc.api_query_cost()
        local_costs = machine_cost * 24 * 30 * np.ones_like(queries)  # Fixed monthly cost

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=queries, y=api_costs, name="API Cost", line=dict(color="#636EFA")))
        fig.add_trace(go.Scatter(x=queries, y=local_costs, name="Local Cost (fixed)", line=dict(color="#00CC96")))
        fig.add_vline(x=be, line_dash="dash", line_color="red", annotation_text=f"Break-even: {be:,.0f}")
        fig.update_layout(xaxis_title="Monthly Queries", yaxis_title="Monthly Cost (USD)", height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Local inference is not cheaper per-query under current assumptions. Adjust machine cost or throughput.")

    # Sensitivity analysis
    st.subheader("Sensitivity Analysis")
    sensitivity = calc.sensitivity_analysis()

    sens_df_data = []
    for scenario, data in sensitivity.items():
        sens_df_data.append({
            "Scenario": scenario.title(),
            "API $/1K": f"${data['api_cost_per_1k']:.4f}",
            "Local $/1K": f"${data['local_cost_per_1k']:.4f}",
            "Break-even (monthly)": f"{data['break_even_monthly_queries']:,.0f}" if data['break_even_monthly_queries'] > 0 else "Never",
            "Savings at 10K/mo": f"${data['savings_at_10k_monthly']:.2f}",
        })

    import pandas as pd
    st.dataframe(pd.DataFrame(sens_df_data), use_container_width=True, hide_index=True)

    # Actual cost from database
    if cost_data:
        st.subheader("Actual Recorded Costs")
        for route, data in cost_data.items():
            cost_per_1k = (data["total_cost"] / data["count"] * 1000) if data["count"] > 0 else 0
            st.metric(f"{route.title()} — {data['count']} requests", f"${data['total_cost']:.6f} total (${cost_per_1k:.4f}/1K)")

