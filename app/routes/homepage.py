import streamlit as st
from utils.helpers import load_css
from data.waste_data import (
    generate_amsterdam_waste_data,
    fetch_and_save_container_data,
    load_container_data,
    get_waste_trend_data,
)

from components.metrics import (
    render_top_metrics,
    render_container_fullness_metrics,
)

from components.charts import (
    render_waste_category_pie,
    render_neighborhood_containers_chart,
    render_collection_efficiency_chart,
    render_waste_trend_chart,
    generate_waste_trend_data_from_containers,
)
from components.map import render_map_container
from components.controls import render_map_controls
from components.tables import render_container_table, render_complaints_section

# Set page config
st.set_page_config(layout="wide")

# Load CSS
load_css("app.css")


def main():
    """Main function to render the Amsterdam Waste Management Dashboard"""
    # Load sample data
    container_df, collection_df, complaints_df, neighborhood_df, waste_by_category = (
        generate_amsterdam_waste_data()
    )

    # --- Dashboard Title ---
    st.header("Amsterdam Waste Management Dashboard")

    # --- Top Row Metrics ---
    render_top_metrics(container_df, collection_df, complaints_df)

    # --- Top Row Charts ---
    top_row = st.columns([1, 1, 1])  # Three columns of equal width

    with top_row[0]:
        render_waste_category_pie(waste_by_category)

    with top_row[1]:
        render_neighborhood_containers_chart(neighborhood_df)

    with top_row[2]:
        render_collection_efficiency_chart(container_df)

    # --- Middle Section - Map and Controls ---
    middle_row = st.columns([2, 1])  # 2/3 for map, 1/3 for controls

    # First handle the controls to get the current selection
    with middle_row[1]:
        st.session_state.container_df = load_container_data()

        # If local data doesn't exist or is empty, try to fetch it
        if st.session_state.container_df.empty:
            with st.spinner("Loading container data..."):
                st.session_state.container_df = fetch_and_save_container_data()

        # Render map controls and get user selections
        map_type, selected_waste_category, selected_neighborhood = render_map_controls(
            container_df
        )

        # Initialize session state if needed
        if "map_type" not in st.session_state:
            st.session_state.map_type = "pins"
        if "selected_waste_category" not in st.session_state:
            st.session_state.selected_waste_category = "All Categories"
        if "selected_neighborhood" not in st.session_state:
            st.session_state.selected_neighborhood = "All Neighborhoods"

        # Update session state with new selections
        st.session_state.map_type = map_type
        st.session_state.selected_waste_category = selected_waste_category
        st.session_state.selected_neighborhood = selected_neighborhood

    # Then render the map with the updated selections
    with middle_row[0]:
        # Render the map with current selections
        filtered_df = render_map_container(
            container_df,
            st.session_state.selected_waste_category,
            st.session_state.selected_neighborhood,
            st.session_state.map_type,
        )

    # --- Container Status and Waste Trends section ---
    st.markdown("---")
    data_insights_row = st.columns(2)

    with data_insights_row[0]:
        st.markdown("### Container Status Overview")
        if filtered_df is not None:
            render_container_fullness_metrics(filtered_df)

    with data_insights_row[1]:
        st.markdown("### Waste Collection Trends")
        # Check if we have real collection data in session state
        if (
            "collection_df" in st.session_state
            and not st.session_state.collection_df.empty
        ):
            # Use real collection data from session state
            collection_df = st.session_state.collection_df
            # Get the trend data from the real collection data
            daily_collection = get_waste_trend_data(collection_df)
            st.caption("Showing real waste collection data")
        else:
            # No real collection data available, generate synthetic data based on containers
            daily_collection = generate_waste_trend_data_from_containers(container_df)
            st.caption(
                "Showing estimated waste collection trends based on container data"
            )

        render_waste_trend_chart(daily_collection)

    # --- Bottom Section - Container Data Table and Complaints ---
    bottom_row = st.columns(2)  # 1/2 for table, 1/2 for notifications

    with bottom_row[0]:
        render_container_table(container_df)

    with bottom_row[1]:
        render_complaints_section(complaints_df)


main()
