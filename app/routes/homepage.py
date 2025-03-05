import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import pydeck as pdk
from datetime import datetime, timedelta
import random

from utils.helpers import load_css

# Set page config
st.set_page_config(
    layout="wide",
)

# Load CSS
load_css("app.css")


# --- Sample Data Generation for Amsterdam Waste Management ---
@st.cache_data
def generate_amsterdam_waste_data():
    # Amsterdam neighborhoods
    neighborhoods = [
        "Centrum",
        "Noord",
        "West",
        "Nieuw-West",
        "Zuid",
        "Oost",
        "Zuidoost",
        "Westpoort",
        "Weesp",
        "IJburg",
        "De Pijp",
        "Jordaan",
        "Oud-West",
        "Bos en Lommer",
        "Oud-Zuid",
    ]

    # Waste categories
    waste_categories = [
        "Recycling",
        "General Waste",
        "Paper/Carton",
        "Glass",
        "Organic",
        "Plastic",
    ]

    # Container types (underground containers and smart bins)
    container_types = ["Underground Container", "Smart Bin"]

    # Create location data for containers
    amsterdam_center = (52.3676, 4.9041)  # Amsterdam center coordinates

    # Generate container locations
    containers = []
    for neighborhood in neighborhoods:
        # Number of containers in this neighborhood
        n_containers = random.randint(5, 20)

        # Base coordinates with offsets for different neighborhoods
        base_lat = amsterdam_center[0] + random.uniform(-0.05, 0.05)
        base_lon = amsterdam_center[1] + random.uniform(-0.05, 0.05)

        for i in range(n_containers):
            container_type = random.choice(container_types)
            waste_type = random.choice(waste_categories)

            # Is it a smart bin?
            is_smart = container_type == "Smart Bin"

            # Status and fill level
            if is_smart:
                status = random.choice(["Open", "Closed"])
                fill_level = random.randint(0, 100)
            else:
                status = "N/A"
                fill_level = random.randint(30, 95)

            # Last emptied date
            days_ago = random.randint(0, 14)
            last_emptied = (datetime.now() - timedelta(days=days_ago)).strftime(
                "%Y-%m-%d"
            )

            containers.append(
                {
                    "id": f"{neighborhood[:3]}-{i + 1:03d}",
                    "neighborhood": neighborhood,
                    "lat": base_lat + random.uniform(-0.02, 0.02),
                    "lon": base_lon + random.uniform(-0.02, 0.02),
                    "type": container_type,
                    "waste_category": waste_type,
                    "fill_level": fill_level,
                    "status": status,
                    "last_emptied": last_emptied,
                    "capacity_kg": 500
                    if container_type == "Underground Container"
                    else 100,
                }
            )

    # Create waste collection data
    collection_dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
    collection_data = []

    for date in collection_dates:
        for category in waste_categories:
            collection_data.append(
                {
                    "date": date,
                    "waste_category": category,
                    "amount_kg": random.randint(500, 5000)
                    + (50 * (date.dayofweek == 1))  # More on Tuesdays
                    + (100 if category == "General Waste" else 0),  # More general waste
                }
            )

    # Create waste complaints
    complaint_types = [
        "Container full",
        "Waste next to container",
        "Container broken",
        "Smart bin not opening",
        "Bad smell",
        "Incorrect waste disposal",
        "Waste not collected",
        "Noise during collection",
    ]

    complaints = []
    for i in range(50):
        days_ago = random.randint(0, 30)
        hours_ago = random.randint(0, 24)
        submission_time = datetime.now() - timedelta(days=days_ago, hours=hours_ago)

        # Random status based on how old the complaint is
        if days_ago < 2:
            status = "New"
        elif days_ago < 7:
            status = "Pending"
        else:
            status = "Resolved"

        complaints.append(
            {
                "time": submission_time,
                "neighborhood": random.choice(neighborhoods),
                "complaint_type": random.choice(complaint_types),
                "description": f"Resident reported {random.choice(complaint_types).lower()} at {random.choice(neighborhoods)}",
                "status": status,
                "container_id": f"{random.choice(neighborhoods)[:3]}-{random.randint(1, 999):03d}"
                if random.random() > 0.3
                else "N/A",
            }
        )

    complaints.sort(key=lambda x: x["time"], reverse=True)

    # Create neighborhood statistics
    neighborhood_stats = []
    for neighborhood in neighborhoods:
        neighborhood_stats.append(
            {
                "neighborhood": neighborhood,
                "total_containers": len(
                    [c for c in containers if c["neighborhood"] == neighborhood]
                ),
                "smart_bins": len(
                    [
                        c
                        for c in containers
                        if c["neighborhood"] == neighborhood
                        and c["type"] == "Smart Bin"
                    ]
                ),
                "recycling_rate": random.uniform(0.2, 0.8),
                "complaints_count": len(
                    [c for c in complaints if c["neighborhood"] == neighborhood]
                ),
                "avg_fill_level": np.mean(
                    [
                        c["fill_level"]
                        for c in containers
                        if c["neighborhood"] == neighborhood
                    ]
                )
                if len([c for c in containers if c["neighborhood"] == neighborhood]) > 0
                else 0,
            }
        )

    # Convert to dataframes
    container_df = pd.DataFrame(containers)
    collection_df = pd.DataFrame(collection_data)
    complaints_df = pd.DataFrame(complaints)
    neighborhood_df = pd.DataFrame(neighborhood_stats)

    # Aggregate collection data by category for pie chart
    waste_by_category = (
        collection_df.groupby("waste_category")["amount_kg"].sum().reset_index()
    )

    return (
        container_df,
        collection_df,
        complaints_df,
        neighborhood_df,
        waste_by_category,
    )


# Load sample data
container_df, collection_df, complaints_df, neighborhood_df, waste_by_category = (
    generate_amsterdam_waste_data()
)

# --- Dashboard Title ---
st.header(
    "Amsterdam Waste Management Dashboard",
)

# --- Top Row Metrics ---
top_metrics = st.columns([1, 1, 1, 1])

with top_metrics[0]:
    # Use a unique key for each container
    container = st.container(key="metric-container-1")
    with container:
        st.metric(
            "Total Containers",
            f"{len(container_df):,}",
            f"{len(container_df[container_df['type'] == 'Smart Bin'])} Smart Bins",
        )

with top_metrics[1]:
    # Use a unique key for each container
    container = st.container(key="metric-container-2")
    with container:
        # Calculate total waste
        total_waste_kg = collection_df["amount_kg"].sum()

        # Calculate previous week comparison properly
        # First, ensure the date column is datetime type
        collection_df["date"] = pd.to_datetime(collection_df["date"])

        # Group by date and calculate daily totals
        daily_totals = collection_df.groupby("date")["amount_kg"].sum()

        # Get the last 7 days and previous 7 days
        last_7_days = (
            daily_totals.iloc[-7:].sum()
            if len(daily_totals) >= 7
            else daily_totals.sum()
        )
        prev_7_days = (
            daily_totals.iloc[-14:-7].sum() if len(daily_totals) >= 14 else None
        )

        # Calculate week-over-week change
        if prev_7_days and prev_7_days > 0:
            wow_change = (last_7_days / prev_7_days) - 1
            wow_text = f"{wow_change:.1%} vs previous week"
        else:
            wow_text = "No previous week data"

        st.metric(
            "Total Waste Collected (30 days)",
            f"{total_waste_kg / 1000:,.1f} tons",
            wow_text,
        )

with top_metrics[2]:
    # Use a unique key for each container
    container = st.container(key="metric-container-3")
    with container:
        open_smart_bins = len(
            container_df[
                (container_df["type"] == "Smart Bin")
                & (container_df["status"] == "Open")
            ]
        )
        closed_smart_bins = len(
            container_df[
                (container_df["type"] == "Smart Bin")
                & (container_df["status"] == "Closed")
            ]
        )
        st.metric(
            "Smart Bin Status",
            f"{open_smart_bins} Open",
            f"{closed_smart_bins} Closed",
            delta_color="off",
        )

with top_metrics[3]:
    # Use a unique key for each container
    container = st.container(key="metric-container-4")
    with container:
        active_complaints = len(complaints_df[complaints_df["status"] != "Resolved"])
        st.metric(
            "Active Complaints",
            active_complaints,
            f"{len(complaints_df[complaints_df['status'] == 'New'])} new",
        )

# --- Top Row Charts ---
top_row = st.columns([1, 1, 1])

with top_row[0]:
    # Use a unique key for each chart container
    chart_container = st.container(key="chart-container-1")
    with chart_container:
        st.subheader("Waste by Category")
        fig = px.pie(
            waste_by_category,
            values="amount_kg",
            names="waste_category",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=250)
        st.plotly_chart(fig, use_container_width=True)

with top_row[1]:
    # Use a unique key for each chart container
    chart_container = st.container(key="chart-container-2")
    with chart_container:
        st.subheader("Waste Collection Trends")
        # Prepare data - summarize by date
        daily_collection = (
            collection_df.groupby(["date", "waste_category"])["amount_kg"]
            .sum()
            .reset_index()
        )
        # Only show the last 10 days for clarity
        daily_collection = daily_collection[
            daily_collection["date"]
            >= daily_collection["date"].max() - pd.Timedelta(days=10)
        ]

        fig = px.line(
            daily_collection,
            x="date",
            y="amount_kg",
            color="waste_category",
            line_shape="spline",
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=250)
        st.plotly_chart(fig, use_container_width=True)

with top_row[2]:
    # Use a unique key for each chart container
    chart_container = st.container(key="chart-container-3")
    with chart_container:
        st.subheader("Containers by Neighborhood")

        fig = px.bar(
            neighborhood_df.sort_values("total_containers", ascending=False).head(10),
            y="neighborhood",
            x=["total_containers", "smart_bins"],
            orientation="h",
            labels={"value": "Number of Containers", "variable": "Type"},
            color_discrete_sequence=["#1E3C5C", "#EC0000"],
            barmode="overlay",
        )
        fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=250)
        st.plotly_chart(fig, use_container_width=True)

# --- Middle Section - Map and Controls ---
middle_row = st.columns([2, 1])  # 2/3 for map, 1/3 for controls

with middle_row[0]:
    # Use a unique key for each chart container
    chart_container = st.container(key="chart-container-4")
    with chart_container:
        st.subheader("Amsterdam Waste Container Map")

        # Set initial view state - centered on Amsterdam
        view_state = pdk.ViewState(
            latitude=52.3676,
            longitude=4.9041,
            zoom=11,
            pitch=50,
        )

        # Get map type selection from session state or set default
        if "map_type" not in st.session_state:
            st.session_state.map_type = "pins"

        if "selected_waste_category" not in st.session_state:
            st.session_state.selected_waste_category = "All Categories"

        if "selected_neighborhood" not in st.session_state:
            st.session_state.selected_neighborhood = "All Neighborhoods"

        # Filter data based on selections
        filtered_df = container_df.copy()

        if st.session_state.selected_waste_category != "All Categories":
            filtered_df = filtered_df[
                filtered_df["waste_category"]
                == st.session_state.selected_waste_category
            ]

        if st.session_state.selected_neighborhood != "All Neighborhoods":
            filtered_df = filtered_df[
                filtered_df["neighborhood"] == st.session_state.selected_neighborhood
            ]

        # Create layers based on selection
        if st.session_state.map_type == "pins":
            # Function to color markers by waste category
            def get_color(waste_type):
                colors = {
                    "Recycling": [46, 139, 87],
                    "General Waste": [128, 128, 128],
                    "Paper/Carton": [70, 130, 180],
                    "Glass": [0, 128, 128],
                    "Organic": [139, 69, 19],
                    "Plastic": [255, 165, 0],
                }
                return colors.get(waste_type, [200, 200, 200])

            # Add a custom icon layer for waste containers
            layer = pdk.Layer(
                "ScatterplotLayer",
                filtered_df,
                get_position=["lon", "lat"],
                get_color=[255, 0, 0, 140],  # Default red color for all pins
                get_fill_color="fill_color",
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

            layers = [layer, text_layer]

        elif st.session_state.map_type == "heatmap":
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

            layers = [layer]

        elif st.session_state.map_type == "categories":
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

            layers = [layer]

        elif st.session_state.map_type == "fill_level":
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

            layers = [layer]

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

with middle_row[1]:
    # Use a unique key for each chart container
    chart_container = st.container(key="chart-container-5")
    chart_container.subheader("Map Controls")

    # Map type selector
    map_type = chart_container.radio(
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
    st.session_state.map_type = map_type

    # Category filter
    categories = ["All Categories"] + list(container_df["waste_category"].unique())
    selected_waste_category = chart_container.selectbox(
        "Filter by Waste Category", categories, key="waste-category-selector"
    )
    st.session_state.selected_waste_category = selected_waste_category

    # Neighborhood filter
    neighborhoods = ["All Neighborhoods"] + list(container_df["neighborhood"].unique())
    selected_neighborhood = chart_container.selectbox(
        "Filter by Neighborhood", neighborhoods, key="neighborhood-selector"
    )
    st.session_state.selected_neighborhood = selected_neighborhood

    # Add a divider
    st.divider()

    # # Smart Bin Status Summary
    # st.subheader("Smart Bin Status")

    # # Get smart bin data
    # smart_bins = container_df[container_df["type"] == "Smart Bin"]
    # open_bins = smart_bins[smart_bins["status"] == "Open"]
    # closed_bins = smart_bins[smart_bins["status"] == "Closed"]

    # # Create a simple gauge chart for open/closed status
    # fig = go.Figure(
    #     go.Indicator(
    #         mode="gauge+number+delta",
    #         value=len(open_bins),
    #         domain={"x": [0, 1], "y": [0, 1]},
    #         title={"text": "Smart Bins Available"},
    #         delta={
    #             "reference": len(smart_bins) / 2,
    #             "increasing": {"color": "green"},
    #         },
    #         gauge={
    #             "axis": {"range": [None, len(smart_bins)]},
    #             "bar": {"color": "green"},
    #             "steps": [
    #                 {"range": [0, len(smart_bins) / 3], "color": "red"},
    #                 {
    #                     "range": [len(smart_bins) / 3, 2 * len(smart_bins) / 3],
    #                     "color": "orange",
    #                 },
    #                 {
    #                     "range": [2 * len(smart_bins) / 3, len(smart_bins)],
    #                     "color": "lightgreen",
    #                 },
    #             ],
    #             "threshold": {
    #                 "line": {"color": "green", "width": 4},
    #                 "thickness": 0.75,
    #                 "value": len(smart_bins) * 0.8,
    #             },
    #         },
    #     )
    # )
    # fig.update_layout(height=200, margin=dict(l=20, r=20, t=30, b=20))
    # st.plotly_chart(fig, use_container_width=True)

    # # Show percentage in text
    # st.html(
    #     f"""
    # <div style="display: flex; justify-content: space-around; text-align: center;">
    #     <div>
    #         <div style="font-size: 1.2em;" class="container-open">{len(open_bins)}</div>
    #         <div>Open</div>
    #     </div>
    #     <div>
    #         <div style="font-size: 1.2em;" class="container-closed">{len(closed_bins)}</div>
    #         <div>Closed</div>
    #     </div>
    #     <div>
    #         <div style="font-size: 1.2em;">{len(open_bins) / len(smart_bins):.1%}</div>
    #         <div>Availability</div>
    #     </div>
    # </div>
    # """,
    # )

    # # High-fill containers
    # st.divider()
    # st.subheader("Containers Needing Attention")

    # # Get containers with high fill levels
    # high_fill = (
    #     container_df[container_df["fill_level"] > 80]
    #     .sort_values("fill_level", ascending=False)
    #     .head(5)
    # )

    # for _, container in high_fill.iterrows():
    #     st.html(
    #         f"""
    #     <div style="padding: 10px; margin-bottom: 8px; border-radius: 5px; border: 1px solid #ddd;">
    #         <div style="display: flex; justify-content: space-between;">
    #             <div><strong>{container["id"]}</strong> ({container["waste_category"]})</div>
    #             <div style="color: {"red" if container["fill_level"] > 90 else "orange"}"><strong>{container["fill_level"]}%</strong> full</div>
    #         </div>
    #         <div style="font-size: 0.9em; color: #666;">{container["neighborhood"]}</div>
    #         <div style="font-size: 0.8em;">Last emptied: {container["last_emptied"]}</div>
    #     </div>
    #     """,
    #     )

# --- Bottom Section - Complaints and Data Table ---
bottom_row = st.columns(2)  # 1/2 for table, 1/2 for notifications

with bottom_row[0]:
    # Use a unique key for each chart container
    chart_container = st.container(key="chart-container-6")
    with chart_container:
        st.subheader("Waste Container Data")

        # Add a search function
        search_term = st.text_input(
            "Search containers by ID or neighborhood", "", key="search-input"
        )

        # Filter the dataframe based on search term
        if search_term:
            table_df = container_df[
                container_df["id"].str.contains(search_term, case=False)
                | container_df["neighborhood"].str.contains(search_term, case=False)
            ]
        else:
            table_df = container_df

        # Add sorting options
        sort_by = st.selectbox(
            "Sort by",
            [
                "Fill Level (high to low)",
                "Neighborhood",
                "Waste Category",
                "Last Emptied",
            ],
            key="sort-selector",
        )

        if sort_by == "Fill Level (high to low)":
            table_df = table_df.sort_values("fill_level", ascending=False)
        elif sort_by == "Neighborhood":
            table_df = table_df.sort_values("neighborhood")
        elif sort_by == "Waste Category":
            table_df = table_df.sort_values("waste_category")
        elif sort_by == "Last Emptied":
            table_df = table_df.sort_values("last_emptied")

        # Reset index for display
        table_df = table_df.reset_index(drop=True)

        # Display the dataframe
        st.dataframe(
            table_df,
            height=400,
            column_config={
                "id": "Container ID",
                "neighborhood": "Neighborhood",
                "type": "Container Type",
                "waste_category": "Waste Type",
                "fill_level": st.column_config.ProgressColumn(
                    "Fill Level",
                    help="Current fill level of the container",
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                ),
                "status": st.column_config.SelectboxColumn(
                    "Status",
                    help="Status for smart bins",
                    width="medium",
                    options=["Open", "Closed", "N/A"],
                    required=True,
                ),
                "last_emptied": "Last Emptied",
                "capacity_kg": st.column_config.NumberColumn(
                    "Capacity (kg)", help="Maximum capacity in kilograms"
                ),
                "lat": None,  # Hide lat/lon columns
                "lon": None,
            },
            use_container_width=True,
            hide_index=True,
            key="container-table",
        )

        # Action buttons
        action_cols = st.columns(3)
        with action_cols[0]:
            if st.button("📥 Export Data", key="export-button"):
                csv = table_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download CSV",
                    csv,
                    "amsterdam_waste_containers.csv",
                    "text/csv",
                    key="download-csv",
                )

        with action_cols[1]:
            if st.button("🗑️ Request Emptying", key="empty-button"):
                st.info("Emptying request sent for selected containers (demo only)")

        with action_cols[2]:
            if st.button("🔄 Refresh Data", key="refresh-button"):
                st.rerun()

with bottom_row[1]:
    # Use a unique key for each chart container
    chart_container = st.container(key="chart-container-7")
    with chart_container:
        st.subheader("Waste Complaints")

        # Create complaint filters
        status_filter = st.multiselect(
            "Filter by status",
            ["New", "Pending", "Resolved"],
            default=["New", "Pending"],
            key="status-filter",
        )

        # Add neighborhood filter
        complaint_neighborhood = st.selectbox(
            "Filter by neighborhood",
            ["All Neighborhoods"] + list(complaints_df["neighborhood"].unique()),
            key="complaint-neighborhood",
        )

        # Filter complaints
        filtered_complaints = complaints_df[complaints_df["status"].isin(status_filter)]
        if complaint_neighborhood != "All Neighborhoods":
            filtered_complaints = filtered_complaints[
                filtered_complaints["neighborhood"] == complaint_neighborhood
            ]

        # Display complaints
        if len(filtered_complaints) == 0:
            st.info("No complaints match your filter criteria")
        else:
            for _, complaint in filtered_complaints.head(10).iterrows():
                time_str = complaint["time"].strftime("%Y-%m-%d %H:%M")
                time_ago = datetime.now() - complaint["time"]

                if time_ago.days > 0:
                    time_display = f"{time_ago.days} days ago"
                elif time_ago.seconds >= 3600:
                    time_display = f"{time_ago.seconds // 3600} hours ago"
                else:
                    time_display = f"{time_ago.seconds // 60} minutes ago"

                notification_class = (
                    f"notification-item notification-{complaint['status'].lower()}"
                )

                container_info = (
                    f"Container ID: {complaint['container_id']}"
                    if complaint["container_id"] != "N/A"
                    else ""
                )

                st.html(
                    f"""
                <div class="{notification_class}">
                    <div class="notification-time">{time_str} ({time_display}) - {complaint["status"]}</div>
                    <div><strong>{complaint["complaint_type"]}</strong> in {complaint["neighborhood"]}</div>
                    <div>{complaint["description"]}</div>
                    <div style="font-size: 0.9em; margin-top: 5px;">{container_info}</div>
                </div>
                """,
                )

        # Add a divider
        st.divider()

        # Form to report a new complaint
        st.subheader("Report New Waste Issue")

        with st.form("report_issue_form"):
            complaint_type = st.selectbox(
                "Issue Type",
                [
                    "Container full",
                    "Waste next to container",
                    "Container broken",
                    "Smart bin not opening",
                    "Bad smell",
                    "Incorrect waste disposal",
                    "Waste not collected",
                    "Noise during collection",
                ],
            )
            st.form_submit_button("submit")
