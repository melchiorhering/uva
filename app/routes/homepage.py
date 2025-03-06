import streamlit as st

from utils.helpers import load_css
from data.waste_data import generate_amsterdam_waste_data, get_waste_trend_data
from components.metrics import render_top_metrics
from components.charts import (
    render_waste_category_pie,
    render_waste_trend_chart,
    render_neighborhood_containers_chart,
)
from components.map import render_map_container, render_map_controls
from components.tables import render_container_table, render_complaints_section

# Set page config
st.set_page_config(
    layout="wide",
)

# Load CSS
load_css("app.css")


def main():
    """Main function to render the Amsterdam Waste Management Dashboard"""
    # Load sample data
    container_df, collection_df, complaints_df, neighborhood_df, waste_by_category = (
        generate_amsterdam_waste_data()
    )

    # --- Dashboard Title ---
    st.header(
        "Amsterdam Waste Management Dashboard",
    )

    # --- Top Row Metrics ---
    render_top_metrics(container_df, collection_df, complaints_df)

    # --- Top Row Charts ---
    top_row = st.columns([1, 1, 1])

    with top_row[0]:
        render_waste_category_pie(waste_by_category)

    with top_row[1]:
        # Prepare data for waste trend chart
        daily_collection = get_waste_trend_data(collection_df, days=10)
        render_waste_trend_chart(daily_collection)

    with top_row[2]:
        render_neighborhood_containers_chart(neighborhood_df)

    # --- Middle Section - Map and Controls ---
    middle_row = st.columns([2, 1])  # 2/3 for map, 1/3 for controls

    # First handle the controls to get the current selection
    with middle_row[1]:
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
        render_map_container(
            container_df,
            st.session_state.selected_waste_category,
            st.session_state.selected_neighborhood,
            st.session_state.map_type,
        )

    # --- Bottom Section - Container Data Table and Complaints ---
    bottom_row = st.columns(2)  # 1/2 for table, 1/2 for notifications

    with bottom_row[0]:
        render_container_table(container_df)

    with bottom_row[1]:
        render_complaints_section(complaints_df)


main()
