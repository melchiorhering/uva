import streamlit as st
import pydeck as pdk
from data.waste_data import (
    load_container_data,
    fetch_and_save_container_data,
    filter_container_data,
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

    # Return the filtered dataframe for use in other components
    return filtered_df


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

    elif map_type == "fill_level" or map_type == "critical_containers":
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
