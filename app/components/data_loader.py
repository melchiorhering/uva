import streamlit as st
import os
import datetime
from data.waste_data import (
    fetch_and_save_container_data,
    load_container_data,
    PROCESSED_DATA_PATH,
)


def data_management_ui():
    """UI component for managing the GeoJSON data loading and caching"""
    st.subheader("Data Management")

    # Check if we have cached data
    if os.path.exists(PROCESSED_DATA_PATH):
        # Get file modification time
        mod_time = os.path.getmtime(PROCESSED_DATA_PATH)
        mod_time_str = datetime.datetime.fromtimestamp(mod_time).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        st.info(f"Local container data available (last updated: {mod_time_str})")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh Data", key="refresh_data_btn"):
                with st.spinner("Fetching latest data from Amsterdam API..."):
                    fetch_and_save_container_data(force_refresh=True)
                    st.success("Data refreshed successfully!")
                    st.rerun()

        with col2:
            if st.button("📊 View Data Stats", key="view_stats_btn"):
                df = load_container_data()
                if not df.empty:
                    st.write(f"Total containers: {len(df)}")
                    st.write(
                        f"Waste categories: {', '.join(df['waste_category'].unique())}"
                    )
                    st.write(f"Neighborhoods: {len(df['neighborhood'].unique())}")

    else:
        st.warning("No local container data found.")
        if st.button("📥 Fetch Container Data", key="fetch_initial_data"):
            with st.spinner("Fetching data from Amsterdam API..."):
                fetch_and_save_container_data()
                st.success("Data fetched and saved successfully!")
                st.rerun()
