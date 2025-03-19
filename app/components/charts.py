import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def render_waste_category_pie(waste_by_category):
    """Render pie chart showing waste by category"""
    st.subheader("Waste by Category")
    fig = px.pie(
        waste_by_category,
        values="amount_kg",
        names="waste_category",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=250)
    st.plotly_chart(fig, use_container_width=True)


def render_neighborhood_containers_chart(neighborhood_df):
    """Render bar chart showing containers by neighborhood"""
    st.subheader("Containers by Neighborhood")
    fig = px.bar(
        neighborhood_df.sort_values("total_containers", ascending=False).head(10),
        y="neighborhood",
        x=["total_containers", "smart_bins"],
        orientation="h",
        labels={"value": "Number of Containers", "variable": "Type"},
        color_discrete_sequence=["#1E3C5C", "#EC0000"],
        barmode="overlay",
    )
    fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=250)
    st.plotly_chart(fig, use_container_width=True)


@st.cache_data(ttl=3600)  # Cache for 1 hour
def render_collection_efficiency_chart(container_df):
    """Render a chart showing waste collection efficiency by neighborhood using real data"""
    st.subheader("Collection Efficiency by Neighborhood")

    if container_df is None or container_df.empty:
        st.info("No container data available to calculate efficiency.")
        return

    try:
        # Calculate efficiency metrics based on container data
        # Group by neighborhood
        neighborhood_stats = (
            container_df.groupby("neighborhood")
            .agg({"id": "count", "fill_level": "mean"})
            .reset_index()
        )

        # Rename columns
        neighborhood_stats.columns = [
            "neighborhood",
            "container_count",
            "avg_fill_level",
        ]

        # Calculate efficiency score (lower fill level means higher efficiency)
        neighborhood_stats["efficiency_score"] = 100 - (
            neighborhood_stats["avg_fill_level"] * 0.8
        )

        # Round efficiency score to 2 decimal places
        neighborhood_stats["efficiency_score"] = neighborhood_stats[
            "efficiency_score"
        ].round(2)

        # Calculate containers per truck (mock calculation based on container count)
        neighborhood_stats["containers_per_truck"] = (
            (neighborhood_stats["container_count"] / 3).clip(lower=5, upper=15).round()
        )

        # Filter to top neighborhoods by container count
        top_neighborhoods = neighborhood_stats.nlargest(8, "container_count")

        fig = px.bar(
            top_neighborhoods.sort_values("efficiency_score", ascending=False),
            y="neighborhood",
            x="efficiency_score",
            orientation="h",
            text="efficiency_score",
            color="containers_per_truck",
            color_continuous_scale="Viridis",
            labels={
                "efficiency_score": "Collection Efficiency (%)",
                "neighborhood": "Neighborhood",
                "containers_per_truck": "Containers per Truck",
            },
        )

        fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=300)
        fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")

        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error rendering collection efficiency chart: {e}")


def render_waste_trend_chart(daily_collection):
    """Render simplified line chart showing waste collection trends"""
    if daily_collection.empty:
        st.info("No collection data available to display.")
        return

    fig = px.line(
        daily_collection,
        x="date",
        y="amount_kg",
        color="waste_category",
        line_shape="spline",
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)


@st.cache_data(ttl=3600)  # Cache for 1 hour
def generate_waste_trend_data_from_containers(container_df):
    """Generate synthetic waste trend data from container data

    Note: This is used only when real collection data is unavailable.
    """
    if container_df is None or container_df.empty:
        return pd.DataFrame(columns=["date", "waste_category", "amount_kg"])

    # Get the unique waste categories from the container data
    waste_categories = container_df["waste_category"].unique()

    # Generate dates for the last 14 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)
    dates = pd.date_range(start=start_date, end=end_date, freq="D")

    # Create a data frame to store the daily collection data
    data = []

    # Create realistic collection patterns based on container fill levels
    for date in dates:
        weekend_factor = 1.3 if date.dayofweek >= 5 else 1.0

        for waste_category in waste_categories:
            # Get containers of this waste type
            category_containers = container_df[
                container_df["waste_category"] == waste_category
            ]

            if not category_containers.empty:
                # Calculate the average fill level for this category
                avg_fill = category_containers["fill_level"].mean()

                # Calculate the total capacity for this category
                total_capacity = (
                    category_containers["capacity_kg"].sum()
                    if "capacity_kg" in category_containers.columns
                    else len(category_containers) * 500
                )

                # Estimate daily collected waste based on fill levels and capacity
                base_amount = (
                    total_capacity * (avg_fill / 100) * 0.2
                )  # Assume ~20% of full capacity is collected daily

                # Add weekend variation
                amount = base_amount * weekend_factor

                # Add some random variation (±15%)
                variation_factor = 0.85 + (np.random.rand() * 0.3)
                amount = amount * variation_factor

                data.append(
                    {
                        "date": date,
                        "waste_category": waste_category,
                        "amount_kg": max(100, int(amount)),  # Ensure reasonable minimum
                    }
                )

    return pd.DataFrame(data)
