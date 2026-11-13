"""LLMOps Governance Dashboard — Main Application.

Professional Streamlit dashboard for monitoring the LLMOps gateway.
"""

import streamlit as st

st.set_page_config(
    page_title="LLMOps Governance Dashboard",
    page_icon="🔀",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    """Main dashboard entry point."""
    st.sidebar.title("🔀 LLMOps Governance")
    st.sidebar.markdown("---")

    # Navigation
    page = st.sidebar.radio(
        "Navigation",
        [
            "📊 Executive Overview",
            "🤖 Model Performance",
            "⏱️ Latency & Throughput",
            "💰 Cost Intelligence",
            "🔀 Routing & Reliability",
            "🧪 Experiments",
        ],
    )

    st.sidebar.markdown("---")

    # Auto-refresh
    refresh = st.sidebar.selectbox("Auto-refresh", ["Off", "10s", "30s", "60s"], index=0)
    if refresh != "Off":
        seconds = int(refresh.replace("s", ""))
        st.sidebar.info(f"Refreshing every {seconds}s")
        import time
        time.sleep(0)  # Placeholder; Streamlit >= 1.37 has st.fragment

    # Database connection info
    import os
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/llmops.db")
    st.sidebar.caption(f"DB: {db_url.split('@')[-1] if '@' in db_url else 'SQLite'}")

    # Route to page
    if "Executive" in page:
        from dashboard.pages.executive_overview import render
        render()
    elif "Model" in page:
        from dashboard.pages.model_performance import render
        render()
    elif "Latency" in page:
        from dashboard.pages.latency_throughput import render
        render()
    elif "Cost" in page:
        from dashboard.pages.cost_intelligence import render
        render()
    elif "Routing" in page:
        from dashboard.pages.routing_reliability import render
        render()
    elif "Experiments" in page:
        from dashboard.pages.experiments import render
        render()


if __name__ == "__main__":
    main()

