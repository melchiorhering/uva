import streamlit as st
import pydeck as pdk

from utils.helpers import load_css
from data.waste_data import generate_amsterdam_waste_data, get_waste_trend_data
from components.metrics import render_top_metrics
from components.charts import (
    render_waste_category_pie,
    render_waste_trend_chart,
    render_neighborhood_containers_chart,
)
from components.map import render_map_controls, create_map_layers
from components.tables import render_container_table, render_complaints_section

# Set page config
st.set_page_config(layout="wide")

# Load CSS
load_css("app.css")


def main():
    """Main function to render the Amsterdam Waste Management Dashboard"""
    container_df, collection_df, complaints_df, neighborhood_df, waste_by_category = (
        generate_amsterdam_waste_data()
    )

    st.header("Amsterdam Waste Management Dashboard")

    render_top_metrics(container_df, collection_df, complaints_df)

    top_row = st.columns([1, 1, 1])

    with top_row[0]:
        render_waste_category_pie(waste_by_category)

    with top_row[1]:
        daily_collection = get_waste_trend_data(collection_df, days=10)
        render_waste_trend_chart(daily_collection)

    with top_row[2]:
        render_neighborhood_containers_chart(neighborhood_df)

    middle_row = st.columns([2, 1]) 

    with middle_row[1]:
        map_type, selected_waste_category, selected_neighborhood = render_map_controls()

        st.session_state.map_type = map_type
        st.session_state.selected_waste_category = selected_waste_category
        st.session_state.selected_neighborhood = selected_neighborhood

    with middle_row[0]:
        filtered_containers = container_df 

        if st.session_state.selected_waste_category != "All Categories":
            filtered_containers = filtered_containers[
                filtered_containers["waste_category"] == st.session_state.selected_waste_category
            ]

        if st.session_state.selected_neighborhood != "All Neighborhoods":
            filtered_containers = filtered_containers[
                filtered_containers["neighborhood"] == st.session_state.selected_neighborhood
            ]

        # Create map layers
        map_layers = create_map_layers(filtered_containers, st.session_state.map_type)

        # Display the map
        st.pydeck_chart(
            pdk.Deck(
                map_style="mapbox://styles/mapbox/light-v9",
                initial_view_state=pdk.ViewState(
                    latitude=52.3676,
                    longitude=4.9041,
                    zoom=12,
                    pitch=45,
                ),
                layers=map_layers,
            )
        )

    
    bottom_row = st.columns(2) 

    with bottom_row[0]:
        render_container_table(container_df)

    with bottom_row[1]:
        render_complaints_section(complaints_df)


main()