import streamlit as st
import pydeck as pdk
from data.waste_data import (
    load_container_data,
    fetch_and_save_container_data,
    filter_container_data,
)
from components.map import create_map_layers, render_map_controls

# Try to load container data from local storage first
if "container_df" not in st.session_state:
    # First try loading from local storage
    st.session_state.container_df = load_container_data()

    # If local data doesn't exist or is empty, try to fetch it
    if st.session_state.container_df.empty:
        with st.spinner("Loading container data..."):
            st.session_state.container_df = fetch_and_save_container_data()

container_df = st.session_state.container_df

if not container_df.empty:
    # Set page title to emphasize hotspot identification
    st.title("Waste Management Hotspot Identification")
    st.markdown("Identify areas requiring immediate waste management attention")

    # Get map configuration from controls
    map_type, selected_waste_category, selected_neighborhood = render_map_controls(
        container_df=container_df
    )

    # Apply filters to the container data based on selections
    filtered_df = filter_container_data(
        container_df,
        waste_category=selected_waste_category,
        neighborhood=selected_neighborhood,
    )

    # Handle renamed visualization type
    if map_type == "critical_containers":
        map_layers = create_map_layers(filtered_df, "fill_level")
    else:
        map_layers = create_map_layers(filtered_df, map_type)

    # Display the map with the layers
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
            tooltip={
                "text": "{id}\nType: {type}\nWaste: {waste_category}\nFill: {fill_level}%\nStatus: {status}"
            },
        )
    )

    # Display data stats
    st.caption(
        f"Displaying {len(filtered_df)} containers from total of {len(container_df)}"
    )
else:
    st.error(
        "Unable to load container data. Please check your connection and try refreshing."
    )
    if st.button("Retry Loading Data"):
        st.session_state.container_df = fetch_and_save_container_data(
            force_refresh=True
        )
        st.rerun()
