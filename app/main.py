import streamlit as st
import pydeck as pdk
from components.map import render_map_controls, create_map_layers  
from data.waste_data import fetch_container_data

# Navigation (if you need it)
navigation = st.navigation(
    [
        st.Page(
            "routes/homepage.py",
            title="Amsterdam Waste Management",
            icon=":material/delete:",
            default=True,
        ),
        st.Page(
            "routes/statistics.py", title="Statistics", icon=":material/favorite:"
        ),
    ]
)
navigation.run()

st.title("🚮 Amsterdam Waste Management Map")

container_df = fetch_container_data()

if not container_df.empty:
    map_type, container_df = render_map_controls()

    map_layers = create_map_layers(container_df, map_type)

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
else:
    st.error("⚠️ No data available. Please check the API connection.")