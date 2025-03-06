import streamlit as st
import pydeck as pdk


@st.fragment
def render_map_container(
    container_df, selected_waste_category, selected_neighborhood, map_type
):
    """Render Amsterdam waste container map with filters"""
    st.subheader("Amsterdam Waste Container Map")

    # Set initial view state - centered on Amsterdam
    view_state = pdk.ViewState(
        latitude=52.3676,
        longitude=4.9041,
        zoom=11,
        pitch=50,
    )

    # Filter data based on selections
    filtered_df = container_df.copy()

    if selected_waste_category != "All Categories":
        filtered_df = filtered_df[
            filtered_df["waste_category"] == selected_waste_category
        ]

    if selected_neighborhood != "All Neighborhoods":
        filtered_df = filtered_df[filtered_df["neighborhood"] == selected_neighborhood]

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
        filtered_df["color"] = filtered_df["waste_category"].apply(
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
        # 3D columns showing fill level
        filtered_df["height"] = filtered_df["fill_level"] * 10
        filtered_df["color"] = filtered_df.apply(
            lambda row: [
                min(255, row["fill_level"] * 2.55),
                max(0, 255 - row["fill_level"] * 2.55),
                0,
                180,
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

    # Map type selector
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

    # Category filter
    categories = ["All Categories"] + list(container_df["waste_category"].unique())
    selected_waste_category = st.selectbox(
        "Filter by Waste Category", categories, key="waste-category-selector"
    )

    # Neighborhood filter
    neighborhoods = ["All Neighborhoods"] + list(container_df["neighborhood"].unique())
    selected_neighborhood = st.selectbox(
        "Filter by Neighborhood", neighborhoods, key="neighborhood-selector"
    )
    return map_type, selected_waste_category, selected_neighborhood
