import streamlit as st
import pydeck as pdk
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data.waste_data import (
    load_container_data,
    fetch_and_save_container_data,
    filter_container_data,
    get_waste_trend_data,  # Import this to use real collection data when available
    get_container_type_colors,
    get_waste_type_colors,
)


@st.fragment
def render_map_container(
    container_df, selected_waste_category, selected_neighborhood, map_type
):
    """Render Amsterdam waste container map with filters"""
    # IMPORTANT: Always use session state data first - this ensures we're using real data
    # not mock data from homepage.py
    if "container_df" in st.session_state and not st.session_state.container_df.empty:
        # Use the real data from session state (loaded in real-data.py)
        container_df = st.session_state.container_df
    elif container_df is None or container_df.empty:
        # If no data in session state or passed in, try loading from file
        container_df = load_container_data()
        if not container_df.empty:
            # Cache it for future use
            st.session_state.container_df = container_df
        else:
            # If still empty, show error and option to fetch
            st.error("No container data available. Please refresh the data.")
            if st.button("Fetch Container Data"):
                with st.spinner("Fetching data..."):
                    container_df = fetch_and_save_container_data(force_refresh=True)
                    if container_df is not None:
                        st.session_state.container_df = container_df
                        st.rerun()
            return

    st.subheader("Amsterdam Waste Container Map")

    # Set initial view state - centered on Amsterdam
    view_state = pdk.ViewState(
        latitude=52.3676,
        longitude=4.9041,
        zoom=11,
        pitch=50,
    )

    # Filter data based on selections using the common filter_container_data function
    filtered_df = filter_container_data(
        container_df,
        waste_category=selected_waste_category,
        neighborhood=selected_neighborhood,
    )

    # Create layers based on selection
    layers = create_map_layers(filtered_df, map_type)

    # Create and display the map
    r = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip={
            "text": "{id}\nType: {type}\nWaste: {waste_category}\nFill: {fill_level}%\nStatus: {status}"
        },
    )

    map_container = st.container(key="map-container")
    map_container.pydeck_chart(r)
    map_container.markdown("**👆 Click on containers to see details**")

    # Add legends directly in the main container instead of sidebar
    if map_type == "categories":
        render_waste_type_legend(filtered_df, map_container)
    elif map_type == "container_types":
        render_container_type_legend(filtered_df, map_container)
    elif map_type == "fill_level":
        render_fill_level_legend(map_container)

    # Add container metrics and collection chart side by side
    st.markdown("### Container Status Overview")

    # Use main columns without nesting
    left_col, right_col = st.columns(2)

    # Render fullness metrics directly (avoiding nested columns)
    with left_col:
        render_container_fullness_metrics(filtered_df)

    with right_col:
        # Use the actual container data for the collection efficiency chart
        render_collection_efficiency_chart(container_df)

    # Add waste trend chart below the map (full width)
    st.markdown("---")
    st.markdown("### Waste Collection Trends")

    # Check if we have real collection data in session state
    if "collection_df" in st.session_state and not st.session_state.collection_df.empty:
        # Use real collection data from session state
        collection_df = st.session_state.collection_df
        # Get the trend data from the real collection data
        daily_collection = get_waste_trend_data(collection_df)
        st.caption("Showing real waste collection data")
    else:
        # No real collection data available, generate synthetic data based on containers
        daily_collection = generate_waste_trend_data_from_containers(container_df)
        st.caption("Showing estimated waste collection trends based on container data")

    render_waste_trend_chart(daily_collection)


def render_container_fullness_metrics(filtered_df):
    """Display container fullness metrics with visual indicators"""
    st.subheader("Container Fullness Status")

    # Handle empty dataframe case
    if filtered_df.empty:
        st.info("No containers match the selected filters.")
        return

    # Calculate fullness metrics
    critical_containers = len(filtered_df[filtered_df["fill_level"] >= 80])
    warning_containers = len(
        filtered_df[
            (filtered_df["fill_level"] >= 60) & (filtered_df["fill_level"] < 80)
        ]
    )
    ok_containers = len(filtered_df[filtered_df["fill_level"] < 60])
    total = len(filtered_df)

    # Create progress bars with proper colors
    critical_percent = critical_containers / total * 100 if total > 0 else 0
    warning_percent = warning_containers / total * 100 if total > 0 else 0
    ok_percent = ok_containers / total * 100 if total > 0 else 0

    # Display metrics without nested columns
    st.markdown(
        f"""
    <div style="display: flex; justify-content: space-between; text-align: center; margin-bottom: 10px;">
        <div style="flex: 1;">
            <h3 style="color: red; margin: 0; font-size: 24px;">{critical_containers}</h3>
            <p style="margin: 0;">Critical (80-100%)</p>
        </div>
        <div style="flex: 1;">
            <h3 style="color: orange; margin: 0; font-size: 24px;">{warning_containers}</h3>
            <p style="margin: 0;">Warning (60-80%)</p>
        </div>
        <div style="flex: 1;">
            <h3 style="color: green; margin: 0; font-size: 24px;">{ok_containers}</h3>
            <p style="margin: 0;">OK (0-60%)</p>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Display percentage bars
    st.progress(critical_percent / 100, "Critical")
    st.progress(warning_percent / 100, "Warning")
    st.progress(ok_percent / 100, "OK")

    # Add insight text
    if critical_percent > 20:
        st.error(f"🚨 {critical_percent:.1f}% of containers need immediate attention!")
    elif warning_percent > 30:
        st.warning(f"⚠️ {warning_percent:.1f}% of containers filling up quickly")
    else:
        st.success("✅ Most containers have adequate capacity")


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

        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error rendering collection efficiency chart: {e}")


def render_waste_type_legend(filtered_df, container):
    """Render waste type legend in the specified container"""
    waste_colors = get_waste_type_colors()
    container.markdown("### Waste Type Legend")
    legend_cols = container.columns(5)  # Organize legend into 5 columns

    i = 0
    for waste_type, color in waste_colors.items():
        if waste_type != "Unknown" and any(filtered_df["waste_category"] == waste_type):
            color_hex = "#{:02x}{:02x}{:02x}".format(color[0], color[1], color[2])
            legend_cols[i % 5].markdown(
                f"<div style='display: flex; align-items: center;'>"
                f"<div style='background-color: {color_hex}; width: 15px; height: 15px; margin-right: 10px;'></div>"
                f"{waste_type}</div>",
                unsafe_allow_html=True,
            )
            i += 1


def render_container_type_legend(filtered_df, container):
    """Render container type legend in the specified container"""
    container_colors = get_container_type_colors()
    container.markdown("### Container Type Legend")
    legend_cols = container.columns(5)  # Organize legend into 5 columns

    i = 0
    for container_type, color in container_colors.items():
        if container_type != "Unknown" and any(filtered_df["type"] == container_type):
            color_hex = "#{:02x}{:02x}{:02x}".format(color[0], color[1], color[2])
            legend_cols[i % 5].markdown(
                f"<div style='display: flex; align-items: center;'>"
                f"<div style='background-color: {color_hex}; width: 15px; height: 15px; margin-right: 10px;'></div>"
                f"{container_type}</div>",
                unsafe_allow_html=True,
            )
            i += 1


def render_fill_level_legend(container):
    """Render fill level legend in the specified container"""
    container.markdown("### Fill Level Legend")
    legend_cols = container.columns(3)

    legend_cols[0].markdown(
        "<div style='display: flex; align-items: center;'>"
        "<div style='background-color: #00FF00; width: 15px; height: 15px; margin-right: 10px;'></div>"
        "Low (0-25%)</div>",
        unsafe_allow_html=True,
    )
    legend_cols[1].markdown(
        "<div style='display: flex; align-items: center;'>"
        "<div style='background-color: #FFFF00; width: 15px; height: 15px; margin-right: 10px;'></div>"
        "Medium (25-75%)</div>",
        unsafe_allow_html=True,
    )
    legend_cols[2].markdown(
        "<div style='display: flex; align-items: center;'>"
        "<div style='background-color: #FF0000; width: 15px; height: 15px; margin-right: 10px;'></div>"
        "High (75-100%) - Needs attention</div>",
        unsafe_allow_html=True,
    )


def create_map_layers(filtered_df, map_type):
    """Create map layers based on selected visualization type"""
    if map_type == "pins":
        # Add a custom icon layer for waste containers
        layer = pdk.Layer(
            "ScatterplotLayer",
            filtered_df,
            get_position=["lon", "lat"],
            get_fill_color=[180, 0, 200, 140],  # Set an RGBA value for fill
            get_radius=100,  # Fixed size for all points
            pickable=True,
            auto_highlight=True,
            radiusMinPixels=5,
            radiusMaxPixels=15,
        )

        # Add a text layer for container IDs
        text_layer = pdk.Layer(
            "TextLayer",
            filtered_df,
            get_position=["lon", "lat"],
            get_text="id",
            get_size=12,
            get_color=[0, 0, 0],
            get_angle=0,
            get_text_anchor="middle",
            get_alignment_baseline="bottom",
            pickable=True,
            sizeScale=0.8,
            sizeUnits="pixels",
            sizeMinPixels=10,
            sizeMaxPixels=25,
        )

        return [layer, text_layer]

    elif map_type == "heatmap":
        # Heatmap layer based on fill level
        layer = pdk.Layer(
            "HeatmapLayer",
            filtered_df,
            get_position=["lon", "lat"],
            get_weight="fill_level",
            opacity=0.8,
            pickable=False,
            aggregation="SUM",
        )
        return [layer]

    elif map_type == "categories":
        # Custom point layer with colors based on waste category
        waste_colors = get_waste_type_colors()
        filtered_df["color"] = filtered_df["waste_category"].apply(
            lambda x: waste_colors.get(x, waste_colors["Unknown"])
        )

        layer = pdk.Layer(
            "ScatterplotLayer",
            filtered_df,
            get_position=["lon", "lat"],
            get_color="color",
            get_radius=100,
            pickable=True,
            auto_highlight=True,
            radiusMinPixels=5,
            radiusMaxPixels=15,
        )

        return [layer]

    elif map_type == "container_types":
        # Custom point layer with colors based on container type
        container_colors = get_container_type_colors()
        filtered_df["color"] = filtered_df["type"].apply(
            lambda x: container_colors.get(x, container_colors["Unknown"])
        )

        layer = pdk.Layer(
            "ScatterplotLayer",
            filtered_df,
            get_position=["lon", "lat"],
            get_color="color",
            get_radius=100,
            pickable=True,
            auto_highlight=True,
            radiusMinPixels=5,
            radiusMaxPixels=15,
        )

        return [layer]

    elif map_type == "fill_level":
        # Enhanced 3D columns showing fill level with improved color scheme for hotspot identification
        filtered_df["height"] = (
            filtered_df["fill_level"] * 10
        )  # Scale height by fill level

        # Color gradient: Green (low) -> Yellow (medium) -> Red (high)
        filtered_df["color"] = filtered_df.apply(
            lambda row: [
                min(
                    255, int(255 if row["fill_level"] > 50 else row["fill_level"] * 5.1)
                ),  # Red component
                min(
                    255, int(255 - abs(row["fill_level"] - 50) * 5.1)
                ),  # Green component
                0,  # Blue component
                180,  # Alpha
            ],
            axis=1,
        )

        layer = pdk.Layer(
            "ColumnLayer",
            filtered_df,
            get_position=["lon", "lat"],
            get_elevation="height",
            elevation_scale=1,
            radius=50,
            get_fill_color="color",
            pickable=True,
            auto_highlight=True,
        )

        return [layer]

    return []  # Default empty layers


def render_map_controls(container_df):
    """Render map controls sidebar"""
    st.subheader("Map Controls")

    # IMPORTANT: First priority is using real data from session state
    if "container_df" in st.session_state and not st.session_state.container_df.empty:
        container_df = st.session_state.container_df
    # Second priority is data passed in
    elif container_df is None or container_df.empty:
        # Third priority is loading from file
        container_df = load_container_data()
        if not container_df.empty:
            st.session_state.container_df = container_df

    # Add option to refresh the container data
    if st.button("🔄 Refresh Container Data", key="refresh-container-data"):
        with st.spinner("Fetching latest container data..."):
            updated_df = fetch_and_save_container_data(force_refresh=True)
            if updated_df is not None and not updated_df.empty:
                st.session_state.container_df = updated_df
                st.success("Data refreshed successfully!")
                container_df = updated_df
                st.rerun()
            else:
                st.error("Failed to refresh data. Using existing data.")

    # Fall back to empty dataframe with correct structure if needed
    if container_df is None or container_df.empty:
        st.warning("No container data available. Some features may be limited.")
        container_df = pd.DataFrame(
            columns=["id", "waste_category", "neighborhood", "fill_level", "type"]
        )

    # Map type selector with improved descriptions
    map_type = st.radio(
        "Visualization Type",
        ["critical_containers", "heatmap", "categories", "container_types", "pins"],
        format_func=lambda x: {
            "critical_containers": "⚠️ Critical Containers (Need Emptying)",
            "heatmap": "🔥 Waste Hotspot Zones",
            "categories": "🗑️ Waste Problem Analysis",
            "container_types": "🚛 Container Distribution",
            "pins": "📍 All Container Locations",
        }[x],
        key="radio-selector",
    )

    # Help text to explain visualization purpose
    if map_type == "critical_containers":
        st.info(
            "Identifies containers that need immediate attention - taller and redder containers are critically full"
        )
    elif map_type == "heatmap":
        st.info(
            "Shows areas with high waste concentration - red zones need urgent cleaning services"
        )
    elif map_type == "categories":
        st.info(
            "Analyzes distribution of waste types - useful for identifying problem areas with specific waste"
        )
    elif map_type == "container_types":
        st.info(
            "Shows container distribution - helps identify areas that need more containers"
        )
    elif map_type == "pins":
        st.info("Basic overview of all container locations")

    # Category filter with error handling
    try:
        categories = ["All Categories"]
        if not container_df.empty and "waste_category" in container_df.columns:
            categories += sorted(list(container_df["waste_category"].unique()))
        selected_waste_category = st.selectbox(
            "Filter by Waste Category", categories, key="waste-category-selector"
        )
    except Exception:
        selected_waste_category = "All Categories"
        st.warning("Error loading waste categories")

    # Neighborhood filter with error handling
    try:
        neighborhoods = ["All Neighborhoods"]
        if not container_df.empty and "neighborhood" in container_df.columns:
            neighborhoods += sorted(list(container_df["neighborhood"].unique()))
        selected_neighborhood = st.selectbox(
            "Filter by Neighborhood", neighborhoods, key="neighborhood-selector"
        )
    except Exception:
        selected_neighborhood = "All Neighborhoods"
        st.warning("Error loading neighborhoods")

    # Show data summary if data is available
    if not container_df.empty:
        with st.expander("Data Summary"):
            st.write(f"Total containers: {len(container_df)}")
            if "waste_category" in container_df.columns:
                st.write(
                    f"Unique waste types: {len(container_df['waste_category'].unique())}"
                )
            if "type" in container_df.columns:
                st.write(
                    f"Unique container types: {len(container_df['type'].unique())}"
                )
            if "neighborhood" in container_df.columns:
                st.write(f"Neighborhoods: {len(container_df['neighborhood'].unique())}")

    return map_type, selected_waste_category, selected_neighborhood
