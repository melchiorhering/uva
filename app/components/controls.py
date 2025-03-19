import streamlit as st
import pandas as pd
from data.waste_data import load_container_data, fetch_and_save_container_data


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
