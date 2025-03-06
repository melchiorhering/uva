import streamlit as st
import pandas as pd


def render_top_metrics(container_df, collection_df, complaints_df):
    """Render the top metrics row"""
    top_metrics = st.columns([1, 1, 1, 1])

    with top_metrics[0]:
        render_container_metric(container_df)

    with top_metrics[1]:
        render_waste_metric(collection_df)

    with top_metrics[2]:
        render_smart_bin_metric(container_df)

    with top_metrics[3]:
        render_complaints_metric(complaints_df)


def render_container_metric(container_df):
    """Render the container count metric"""
    container = st.container(key="metric-container-1")
    with container:
        st.metric(
            "Total Containers",
            f"{len(container_df):,}",
            f"{len(container_df[container_df['type'] == 'Smart Bin'])} Smart Bins",
        )


def render_waste_metric(collection_df):
    """Render the total waste collected metric with week-over-week comparison"""
    container = st.container(key="metric-container-2")
    with container:
        # Calculate total waste
        total_waste_kg = collection_df["amount_kg"].sum()

        # Calculate previous week comparison properly
        # First, ensure the date column is datetime type
        collection_df["date"] = pd.to_datetime(collection_df["date"])

        # Group by date and calculate daily totals
        daily_totals = collection_df.groupby("date")["amount_kg"].sum()

        # Get the last 7 days and previous 7 days
        last_7_days = (
            daily_totals.iloc[-7:].sum()
            if len(daily_totals) >= 7
            else daily_totals.sum()
        )
        prev_7_days = (
            daily_totals.iloc[-14:-7].sum() if len(daily_totals) >= 14 else None
        )

        # Calculate week-over-week change
        if prev_7_days and prev_7_days > 0:
            wow_change = (last_7_days / prev_7_days) - 1
            wow_text = f"{wow_change:.1%} vs previous week"
        else:
            wow_text = "No previous week data"

        st.metric(
            "Total Waste Collected (30 days)",
            f"{total_waste_kg / 1000:,.1f} tons",
            wow_text,
        )


def render_smart_bin_metric(container_df):
    """Render the smart bin status metric"""
    container = st.container(key="metric-container-3")
    with container:
        open_smart_bins = len(
            container_df[
                (container_df["type"] == "Smart Bin")
                & (container_df["status"] == "Open")
            ]
        )
        closed_smart_bins = len(
            container_df[
                (container_df["type"] == "Smart Bin")
                & (container_df["status"] == "Closed")
            ]
        )
        st.metric(
            "Smart Bin Status",
            f"{open_smart_bins} Open",
            f"{closed_smart_bins} Closed",
            delta_color="off",
        )


def render_complaints_metric(complaints_df):
    """Render the active complaints metric"""
    container = st.container(key="metric-container-4")
    with container:
        active_complaints = len(complaints_df[complaints_df["status"] != "Resolved"])
        st.metric(
            "Active Complaints",
            active_complaints,
            f"{len(complaints_df[complaints_df['status'] == 'New'])} new",
        )
