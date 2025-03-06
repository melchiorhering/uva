import streamlit as st
from datetime import datetime


def render_container_table(container_df):
    """Render the waste container data table with search and sort"""
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

    # Add buttons for actions
    render_container_action_buttons(table_df)

    return table_df


def render_container_action_buttons(table_df):
    """Render action buttons for container table"""
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


def render_complaints_section(complaints_df):
    """Render waste complaints section with filters"""
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
    render_complaints_list(filtered_complaints)

    # Add a divider
    st.divider()

    # Form to report a new complaint
    render_complaint_form()


def render_complaints_list(filtered_complaints):
    """Render list of complaints with formatting"""
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


def render_complaint_form():
    """Render form to submit a new complaint"""
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
        st.form_submit_button("Submit Report")
