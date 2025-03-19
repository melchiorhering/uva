import streamlit as st
import pydeck as pdk
import pandas as pd
import random
from datetime import datetime
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
    if map_type == "open_bins":
        # Generate mock data for open waste bins
        open_bins_df = generate_mock_open_bins(selected_neighborhood)
        layers = create_map_layers(open_bins_df, map_type)
        # Use the open bins dataframe for display and metrics
        display_df = open_bins_df
    else:
        layers = create_map_layers(filtered_df, map_type)
        display_df = filtered_df

    # Create and display the map
    r = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip={
            "text": "{id}\nType: {bin_type}\nWaste: {waste_category}\nFill: {fill_level}%\nStatus: {status}\nCapacity: {capacity_liters} liters\nLast emptied: {last_emptied}"
            if map_type == "open_bins"
            else "{id}\nType: {type}\nWaste: {waste_category}\nFill: {fill_level}%\nStatus: {status}"
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
    elif map_type == "fill_level" or map_type == "critical_containers":
        render_fill_level_legend(map_container)
    elif map_type == "open_bins":
        render_open_bins_legend(map_container)

    # Return the filtered dataframe for use in other components
    return display_df


def generate_mock_open_bins(selected_neighborhood):
    """Generate mock data for smaller open waste bins around Amsterdam with realistic distribution"""
    # Amsterdam center coordinates
    center_lat, center_lon = 52.3676, 4.9041

    # Dictionary of Amsterdam neighborhoods with approximate centers
    neighborhoods = {
        "Centrum": (52.3700, 4.9000),
        "Noord": (52.3900, 4.9200),
        "West": (52.3750, 4.8700),
        "Nieuw-West": (52.3600, 4.8000),
        "Zuid": (52.3400, 4.8800),
        "Oost": (52.3600, 4.9400),
        "Zuidoost": (52.3100, 4.9700),
        "Westpoort": (52.4100, 4.8300),
        "Weesp": (52.3050, 5.0430),
        "IJburg": (52.3500, 5.0000),
        "De Pijp": (52.3550, 4.8950),
        "Jordaan": (52.3700, 4.8850),
        "Oud-West": (52.3650, 4.8750),
        "Bos en Lommer": (52.3800, 4.8530),
        "Oud-Zuid": (52.3500, 4.8800),
    }

    # Define hotspot and coldspot areas (tourist vs residential)y
    hotspots = {
        "Centrum": {"weight": 0.85, "bins_factor": 2.5},  # Tourist center - many bins
        "De Pijp": {"weight": 0.75, "bins_factor": 2.0},  # Popular area with many cafes
        "Jordaan": {"weight": 0.70, "bins_factor": 1.8},  # Tourist/shopping area
        "Zuid": {"weight": 0.65, "bins_factor": 1.5},  # Business district
        "Oud-West": {"weight": 0.65, "bins_factor": 1.5},  # Popular residential area
    }

    coldspots = {
        "Noord": {"weight": 0.3, "bins_factor": 0.7},  # Less dense residential area
        "Nieuw-West": {"weight": 0.4, "bins_factor": 0.6},  # More suburban
        "Zuidoost": {"weight": 0.3, "bins_factor": 0.5},  # Less dense
        "Westpoort": {"weight": 0.2, "bins_factor": 0.4},  # Industrial area
        "Weesp": {"weight": 0.25, "bins_factor": 0.3},  # Far from center
    }

    # Generate more bins across Amsterdam (60-120)
    num_bins = random.randint(60, 120)

    # If specific neighborhood is selected, generate more bins there
    if (
        selected_neighborhood != "All Neighborhoods"
        and selected_neighborhood in neighborhoods
    ):
        if selected_neighborhood in hotspots:
            factor = hotspots[selected_neighborhood]["bins_factor"]
        elif selected_neighborhood in coldspots:
            factor = (
                coldspots[selected_neighborhood]["bins_factor"] * 2
            )  # Boost selected coldspots
        else:
            factor = 1.5
        num_bins = int(num_bins * factor)

    bins = []

    # Different bin types with realistic distribution
    bin_types = ["Standard", "Recycling", "Cigarette", "Solar Compactor"]

    # Adjust weights based on urban realities - standard bins most common,
    # solar compactors rare and mostly in high-traffic areas
    base_weights = {
        "Standard": 0.65,
        "Recycling": 0.20,
        "Cigarette": 0.10,
        "Solar Compactor": 0.05,
    }

    # Generate bins with realistic geographic distribution
    for _ in range(num_bins):
        if (
            selected_neighborhood != "All Neighborhoods"
            and selected_neighborhood in neighborhoods
        ):
            # Generate bins in the selected neighborhood
            center = neighborhoods[selected_neighborhood]
            # Smaller spread for specific neighborhood
            lat = center[0] + random.uniform(-0.015, 0.015)
            lon = center[1] + random.uniform(-0.015, 0.015)
            neighborhood = selected_neighborhood

            # Adjust bin type weights for this specific neighborhood
            bin_type_weights = list(base_weights.values())
        else:
            # Distribute bins with higher concentration in hotspots
            if random.random() < 0.85:  # 85% in defined neighborhoods
                # Weight neighborhood selection by hotspot/coldspot factors
                hood_weights = []
                hood_names = []

                for hood, data in hotspots.items():
                    hood_weights.append(data["weight"])
                    hood_names.append(hood)

                for hood, data in coldspots.items():
                    hood_weights.append(data["weight"])
                    hood_names.append(hood)

                for hood in neighborhoods.keys():
                    if hood not in hotspots and hood not in coldspots:
                        hood_weights.append(0.5)  # Default weight
                        hood_names.append(hood)

                # Normalize weights
                total_weight = sum(hood_weights)
                hood_weights = [w / total_weight for w in hood_weights]

                # Select neighborhood based on weights
                neighborhood = random.choices(hood_names, weights=hood_weights, k=1)[0]
                center = neighborhoods[neighborhood]

                # Add some geographic clustering - bins tend to be placed near each other
                cluster_size = random.randint(1, 4)  # 1-4 bins in a cluster
                if len(bins) > 0 and random.random() < 0.4 and cluster_size > 1:
                    # 40% chance to create a cluster by using a nearby bin's location
                    recent_bins = bins[-10:]  # Look at the 10 most recently added bins
                    if recent_bins and neighborhood == recent_bins[-1]["neighborhood"]:
                        # Cluster around a recent bin in the same neighborhood
                        base_lat = recent_bins[-1]["lat"]
                        base_lon = recent_bins[-1]["lon"]
                        # Small spread within cluster
                        lat = base_lat + random.uniform(-0.002, 0.002)
                        lon = base_lon + random.uniform(-0.002, 0.002)
                    else:
                        # Add some randomness within neighborhood
                        spread = 0.008 if neighborhood in hotspots else 0.015
                        lat = center[0] + random.uniform(-spread, spread)
                        lon = center[1] + random.uniform(-spread, spread)
                else:
                    # Add some randomness within neighborhood
                    spread = 0.008 if neighborhood in hotspots else 0.015
                    lat = center[0] + random.uniform(-spread, spread)
                    lon = center[1] + random.uniform(-spread, spread)

                # Adjust bin type weights based on neighborhood type
                if neighborhood in hotspots:
                    # More recycling and solar compactors in hotspots
                    bin_type_weights = [0.55, 0.25, 0.10, 0.10]
                elif neighborhood in coldspots:
                    # Mostly standard bins in coldspots, rarely solar compactors
                    bin_type_weights = [0.75, 0.15, 0.08, 0.02]
                else:
                    # Default weights
                    bin_type_weights = list(base_weights.values())
            else:
                # Some bins spread around generally
                lat = center_lat + random.uniform(-0.05, 0.05)
                lon = center_lon + random.uniform(-0.05, 0.05)
                neighborhood = "Other area"
                bin_type_weights = list(base_weights.values())

        # Generate bin data with more variation
        bin_type = random.choices(bin_types, weights=bin_type_weights, k=1)[0]

        # Capacity varies by bin type
        if bin_type == "Solar Compactor":
            capacity = random.randint(120, 180)  # liters - larger capacity
        elif bin_type == "Recycling":
            capacity = random.randint(60, 120)  # liters
        elif bin_type == "Cigarette":
            capacity = random.randint(10, 30)  # liters - small
        else:
            capacity = random.randint(40, 90)  # liters

        # Fill level - create realistic distribution with geographic patterns
        # Base fill level varies by neighborhood type
        if neighborhood in hotspots:
            base_fill_level = random.randint(30, 60)  # Busier areas have more waste
        elif neighborhood in coldspots:
            base_fill_level = random.randint(10, 40)  # Less busy areas have less waste
        else:
            base_fill_level = random.randint(15, 50)  # Medium waste levels

        # Add bin type factor - some bin types fill faster
        type_factor = 0
        if bin_type == "Standard":
            type_factor = random.randint(5, 15)
        elif bin_type == "Recycling":
            type_factor = random.randint(0, 10)
        elif bin_type == "Solar Compactor":
            type_factor = random.randint(-10, 0)  # Compactors stay emptier longer
        elif bin_type == "Cigarette":
            type_factor = random.randint(15, 30)  # Cigarette bins fill quickly

        # Day of week effect - bins are typically emptier on Monday (assume day 0)
        day_of_week = datetime.now().weekday()
        day_factor = min(day_of_week * 3, 15)  # Adds up to 15% for weekends

        fill_level = min(95, max(5, base_fill_level + type_factor + day_factor))

        # Last emptied between 0-10 days ago, correlated with fill level
        # Fuller bins tend to have been emptied longer ago
        days_corr = max(0, min(10, int(fill_level / 10)))
        days_random = random.randint(-2, 2)  # Add some randomness
        days_ago = max(0, min(10, days_corr + days_random))

        bins.append(
            {
                "id": f"BIN-{len(bins):03d}",
                "neighborhood": neighborhood,
                "lat": lat,
                "lon": lon,
                "type": "Small Bin",
                "bin_type": bin_type,
                "waste_category": "General Waste"
                if bin_type != "Recycling"
                else "Mixed Recycling",
                "fill_level": fill_level,
                "status": "Open",  # All these bins are open by definition
                "capacity_liters": capacity,
                "last_emptied": f"{days_ago} days ago",
            }
        )

    return pd.DataFrame(bins)


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


def render_open_bins_legend(container):
    """Render legend for open waste bins"""
    container.markdown("### Open Waste Bins Legend")
    legend_cols = container.columns(5)  # Changed from 4 to 5 columns to include routes

    legend_cols[0].markdown(
        "<div style='display: flex; align-items: center;'>"
        "<div style='background-color: #0064FF; width: 15px; height: 15px; margin-right: 10px;'></div>"
        "Standard</div>",
        unsafe_allow_html=True,
    )
    legend_cols[1].markdown(
        "<div style='display: flex; align-items: center;'>"
        "<div style='background-color: #00B464; width: 15px; height: 15px; margin-right: 10px;'></div>"
        "Recycling</div>",
        unsafe_allow_html=True,
    )
    legend_cols[2].markdown(
        "<div style='display: flex; align-items: center;'>"
        "<div style='background-color: #FF6400; width: 15px; height: 15px; margin-right: 10px;'></div>"
        "Cigarette</div>",
        unsafe_allow_html=True,
    )
    legend_cols[3].markdown(
        "<div style='display: flex; align-items: center;'>"
        "<div style='background-color: #8000FF; width: 15px; height: 15px; margin-right: 10px;'></div>"
        "Solar Compactor</div>",
        unsafe_allow_html=True,
    )
    legend_cols[4].markdown(
        "<div style='display: flex; align-items: center;'>"
        "<div style='border: 2px dashed #FFFFFF; width: 15px; height: 2px; margin-right: 10px;'></div>"
        "Collection Routes</div>",
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

    elif map_type == "open_bins":
        # Custom visualization for open waste bins with type-based colors
        filtered_df["color"] = filtered_df["bin_type"].apply(
            lambda x: {
                "Standard": [0, 100, 255, 180],  # Blue for standard bins
                "Recycling": [0, 180, 100, 180],  # Green for recycling bins
                "Cigarette": [255, 100, 0, 180],  # Orange for cigarette bins
                "Solar Compactor": [128, 0, 255, 180],  # Purple for solar compactors
            }.get(x, [100, 100, 100, 180])  # Gray for unknown types
        )

        # Create bin icons with size based on capacity and fill level
        filtered_df["radius"] = filtered_df.apply(
            lambda row: max(
                25,
                min((row["capacity_liters"] / 2) * (0.8 + row["fill_level"] / 100), 80),
            ),
            axis=1,
        )

        # Small waste bin layer
        bin_layer = pdk.Layer(
            "ScatterplotLayer",
            filtered_df,
            get_position=["lon", "lat"],
            get_color="color",
            get_radius="radius",
            pickable=True,
            auto_highlight=True,
            radiusMinPixels=5,
            radiusMaxPixels=15,
        )

        # Add labels for bin types
        text_layer = pdk.Layer(
            "TextLayer",
            filtered_df,
            get_position=["lon", "lat"],
            get_text="bin_type",
            get_size=12,
            get_color=[255, 255, 255],
            get_angle=0,
            get_text_anchor="middle",
            get_alignment_baseline="center",
            pickable=True,
            sizeScale=0.6,
            sizeUnits="pixels",
            sizeMinPixels=8,
            sizeMaxPixels=16,
        )

        # Generate optimized routes between bins
        routes_df = generate_optimized_routes(filtered_df)

        # If routes were successfully generated, add a path layer
        if not routes_df.empty:
            route_layer = pdk.Layer(
                "PathLayer",
                routes_df,
                get_path="path",
                get_color="color",
                width_scale=15,
                width_min_pixels=2,
                width_max_pixels=5,
                get_width=5,
                pickable=True,
                auto_highlight=True,
                joint_rounded=True,
                dash_size=10,
                dash_gap=5,
                get_dash_array=[10, 10],  # Creates a dashed line effect
                highlight_color=[255, 255, 0, 128],  # Yellow highlight when clicked
            )

            # Add an icon at the start of each route to indicate the starting point
            start_points = []
            for path in routes_df["path"]:
                if path and len(path) > 0:
                    start_points.append({"position": path[0], "name": "Start"})

            if start_points:
                start_df = pd.DataFrame(start_points)
                start_layer = pdk.Layer(
                    "IconLayer",
                    start_df,
                    get_position="position",
                    get_icon="name",
                    get_size=5,
                    size_scale=8,
                    pickable=True,
                    get_color=[255, 255, 0, 200],  # Yellow
                    icon_atlas="https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/icon-atlas.png",
                    icon_mapping={
                        "Start": {
                            "x": 0,
                            "y": 0,
                            "width": 128,
                            "height": 128,
                            "mask": True,
                        }
                    },
                )
                return [route_layer, bin_layer, text_layer, start_layer]

            return [route_layer, bin_layer, text_layer]

        return [bin_layer, text_layer]

    return []  # Default empty layers


def generate_optimized_routes(bins_df, num_routes=5):
    """Generate optimized collection routes between open waste bins"""
    if len(bins_df) < 3:  # Need at least 3 bins for a meaningful route
        return pd.DataFrame()

    routes = []
    route_ids = []
    bins_by_type = {}

    # Group bins by type for more realistic collection routes (different trucks for different waste types)
    for bin_type in bins_df["bin_type"].unique():
        bins_by_type[bin_type] = bins_df[bins_df["bin_type"] == bin_type]

    # Process each bin type that has enough bins
    route_counter = 0
    for bin_type, type_bins in bins_by_type.items():
        if len(type_bins) < 3:
            continue

        # Determine how many routes to create for this bin type
        # More common types get more routes
        routes_for_type = max(1, int(len(type_bins) / 15))  # Roughly 15 bins per route
        routes_for_type = min(routes_for_type, num_routes - route_counter)

        for r in range(routes_for_type):
            if route_counter >= num_routes:
                break

            # Select a subset of bins for this route
            sample_size = min(random.randint(5, 15), len(type_bins))
            route_bins = type_bins.sample(sample_size)

            # Sort bins by fill level (descending) to prioritize fuller bins
            route_bins = route_bins.sort_values("fill_level", ascending=False)

            # Start from a random bin weighted by fill level
            weights = route_bins["fill_level"].values
            start_idx = random.choices(range(len(route_bins)), weights=weights)[0]

            # Nearest neighbor algorithm for route optimization
            route_points = []
            unvisited = set(range(len(route_bins)))
            current = start_idx
            route_points.append(
                (route_bins.iloc[current]["lon"], route_bins.iloc[current]["lat"])
            )
            unvisited.remove(current)

            # Find nearest neighbors
            while unvisited:
                current_lon = route_bins.iloc[current]["lon"]
                current_lat = route_bins.iloc[current]["lat"]

                # Calculate distances to all unvisited bins
                min_dist = float("inf")
                next_idx = None

                for idx in unvisited:
                    lon = route_bins.iloc[idx]["lon"]
                    lat = route_bins.iloc[idx]["lat"]
                    # Simple Euclidean distance (sufficient for our visualization purposes)
                    dist = ((current_lon - lon) ** 2 + (current_lat - lat) ** 2) ** 0.5

                    if dist < min_dist:
                        min_dist = dist
                        next_idx = idx

                current = next_idx
                route_points.append(
                    (route_bins.iloc[current]["lon"], route_bins.iloc[current]["lat"])
                )
                unvisited.remove(current)

            # Add a route color based on bin type
            if bin_type == "Standard":
                color = [0, 100, 255]  # Blue
            elif bin_type == "Recycling":
                color = [0, 180, 100]  # Green
            elif bin_type == "Cigarette":
                color = [255, 100, 0]  # Orange
            elif bin_type == "Solar Compactor":
                color = [128, 0, 255]  # Purple
            else:
                color = [100, 100, 100]  # Gray

            routes.append(route_points)
            route_ids.append(f"Route {route_counter + 1}: {bin_type}")
            route_counter += 1

    if not routes:
        return pd.DataFrame()

    # Create a DataFrame with route information
    routes_df = pd.DataFrame(
        {
            "path": routes,
            "name": route_ids,
            "color": [get_color_for_route(rid) for rid in route_ids],
        }
    )

    return routes_df


def get_color_for_route(route_id):
    """Get color for a route based on the bin type in the route name"""
    if "Standard" in route_id:
        return [0, 100, 255, 180]  # Blue for standard bins
    elif "Recycling" in route_id:
        return [0, 180, 100, 180]  # Green for recycling bins
    elif "Cigarette" in route_id:
        return [255, 100, 0, 180]  # Orange for cigarette bins
    elif "Solar Compactor" in route_id:
        return [128, 0, 255, 180]  # Purple for solar compactors
    else:
        return [100, 100, 100, 180]  # Gray for unknown types
