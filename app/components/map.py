import streamlit as st
import pydeck as pdk
from data.waste_data import fetch_container_data
import streamlit as st
import pydeck as pdk

@st.fragment
def render_map_controls():
    """Render sidebar controls for filtering the map."""
    st.subheader("Map Controls")

    map_type = st.radio(
        "Visualization Type",
        ["pins", "heatmap", "categories", "fill_level"],
        format_func=lambda x: {
            "pins": "📍 Container Locations",
            "heatmap": "🔥 Fill Level Heatmap",
            "categories": "🗑️ Waste Categories",
            "fill_level": "📊 3D Fill Levels",
        }[x],
        key="radio-selector",
    )

    categories = ["All Categories", "General Waste", "Recycling", "Plastic", "Glass", "Organic"]
    selected_waste_category = st.selectbox(
        "Filter by Waste Category", categories, key="waste-category-selector"
    )

    neighborhoods = ["All Neighborhoods", "Centrum", "Noord", "West", "Zuid", "Oost"]
    selected_neighborhood = st.selectbox(
        "Filter by Neighborhood", neighborhoods, key="neighborhood-selector"
    )

    return map_type, selected_waste_category, selected_neighborhood



def create_map_layers(container_df, map_type):
    """Dynamically generate PyDeck map layers based on GeoJSON container data"""

    if container_df.empty:
        st.warning("⚠️ No container data available.")
        return []

    if map_type == "pins":
        layer = pdk.Layer(
            "ScatterplotLayer",
            container_df,
            get_position=["lon", "lat"],
            get_fill_color=[0, 200, 0, 140], 
            get_radius=100,
            pickable=True,
            auto_highlight=True,
        )
        return [layer]

    elif map_type == "heatmap":
        layer = pdk.Layer(
            "HeatmapLayer",
            container_df,
            get_position=["lon", "lat"],
            get_weight=1,
            opacity=0.8,
            pickable=False,
        )
        return [layer]

    elif map_type == "categories":
        container_df["color"] = container_df["waste_category"].apply(
            lambda x: {
                "Recycling": [46, 139, 87],
                "General Waste": [128, 128, 128],
                "Paper/Carton": [70, 130, 180],
                "Glass": [0, 128, 128],
                "Organic": [139, 69, 19],
                "Plastic": [255, 165, 0],
            }.get(x, [200, 200, 200])
        )
        layer = pdk.Layer(
            "ScatterplotLayer",
            container_df,
            get_position=["lon", "lat"],
            get_color="color",
            get_radius=100,
            pickable=True,
            auto_highlight=True,
        )
        return [layer]

    return []