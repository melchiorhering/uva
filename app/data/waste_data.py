import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import streamlit as st
import requests
import json
import os

# Amsterdam data constants
NEIGHBORHOODS = [
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

WASTE_CATEGORIES = [
    "Recycling",
    "General Waste",
    "Paper/Carton",
    "Glass",
    "Organic",
    "Plastic",
]

CONTAINER_TYPES = ["Underground Container", "Smart Bin"]

COMPLAINT_TYPES = [
    "Container full",
    "Waste next to container",
    "Container broken",
    "Smart bin not opening",
    "Bad smell",
    "Incorrect waste disposal",
    "Waste not collected",
    "Noise during collection",
]

# Amsterdam center coordinates
AMSTERDAM_CENTER = (52.3676, 4.9041)

# URL for the Amsterdam Waste Container GeoJSON data
GEOJSON_URL = "https://map.data.amsterdam.nl/maps/afval?request=getfeature&service=wfs&version=1.1.0&typename=container_coordinaten&outputformat=geojson"

# Define the path where the GeoJSON data will be stored
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_cache")
GEOJSON_DATA_PATH = os.path.join(DATA_DIR, "amsterdam_containers.json")
PROCESSED_DATA_PATH = os.path.join(DATA_DIR, "processed_containers.csv")


def ensure_data_dir_exists():
    """Ensure the data directory exists"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def fetch_and_save_container_data(force_refresh=False):
    """Fetch GeoJSON data from API, process it, and save locally

    Parameters:
    force_refresh (bool): If True, fetch from API even if local files exist

    Returns:
    DataFrame: Processed container data
    """
    # Ensure data directory exists
    ensure_data_dir_exists()

    # Check if we need to fetch data
    need_to_fetch = force_refresh or not os.path.exists(PROCESSED_DATA_PATH)

    if need_to_fetch:
        st.info("Fetching container data from Amsterdam API...")
        try:
            response = requests.get(GEOJSON_URL)
            response.raise_for_status()  # Raise error for bad responses
            geojson_data = response.json()

            # Save raw GeoJSON
            with open(GEOJSON_DATA_PATH, "w") as f:
                json.dump(geojson_data, f)

            # Process and save as CSV for faster loading
            df = parse_geojson(geojson_data)
            df.to_csv(PROCESSED_DATA_PATH, index=False)

            st.success("Data successfully fetched and saved.")
            return df

        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching data: {e}")
            # Try to load existing data if available
            if os.path.exists(PROCESSED_DATA_PATH):
                st.warning("Using previously cached data instead.")
                return load_container_data()
            return pd.DataFrame()  # Return empty DataFrame on failure
    else:
        # Data exists locally, just load it
        return load_container_data()


def load_container_data():
    """Load container data from local storage

    Returns:
    DataFrame: Processed container data
    """
    try:
        if os.path.exists(PROCESSED_DATA_PATH):
            df = pd.read_csv(PROCESSED_DATA_PATH)
            return df
        else:
            st.warning("No local data found. Please fetch data first.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()


def fetch_container_data():
    """Fetch Amsterdam waste container data and convert it to DataFrame
    (Legacy function - now tries to load local data first, then fetches if needed)
    """
    # Try to load local data first
    df = load_container_data()

    # If no local data, fetch from API
    if df.empty:
        try:
            response = requests.get(GEOJSON_URL)
            response.raise_for_status()  # Raise error for bad responses
            geojson_data = response.json()

            return parse_geojson(geojson_data)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data: {e}")
            return pd.DataFrame()  # Return empty DataFrame on failure

    return df


def parse_geojson(geojson_data):
    """Extract relevant fields from GeoJSON and augment with mock data where needed"""
    containers = []

    # Map common container types from Amsterdam data - updated to match actual values
    container_type_mapping = {
        "Rest": "Rest",
        "Papier": "Paper/Carton",
        "Glas": "Glass",
        "Plastic": "Plastic",
        "GFT": "Organic",
        "Textiel": "Textiles",
        "Restafval": "Rest",
        "Restafval ondergronds": "Rest",
        "Plastic afval": "Plastic",
        "Groente fruit en tuinafval": "Organic",
        "Textielcontainer": "Textiles",
        "Glas-gemengd": "Glass",
        "Karton/papier": "Paper/Carton",
    }

    # Define neighborhoods with "recently emptied" containers (lower fill levels)
    recently_emptied = ["Oost", "Nieuw-West", "IJburg", "Weesp"]

    # Define neighborhoods with higher fill levels (needing attention soon)
    needs_attention = ["Centrum", "De Pijp", "Zuid", "Jordaan"]

    # Track containers by neighborhood for consistent fill patterns
    neighborhood_fill_patterns = {}

    for feature in geojson_data["features"]:
        props = feature["properties"]
        coords = feature["geometry"]["coordinates"]

        # Get waste type from Amsterdam data or default
        # First check 'fractie_omschrijving', fall back to other fields if needed
        waste_category = props.get("fractie_omschrijving", "Unknown")
        if waste_category in container_type_mapping:
            waste_category = container_type_mapping[waste_category]

        # Container ID - use actual ID or generate one
        container_id = props.get("id", f"AMS-{len(containers):04d}")

        # Get neighborhood or district information
        neighborhood = props.get("eigenaar_naam", "Unknown")
        if neighborhood == "Unknown":
            # Try alternate fields
            neighborhood = props.get("stadsdeel", props.get("buurt", "Amsterdam"))

        # Generate realistic fill levels based on neighborhood patterns
        if neighborhood not in neighborhood_fill_patterns:
            # Create a new base fill pattern for this neighborhood
            if neighborhood in recently_emptied:
                # Recently emptied neighborhoods have lower fill levels
                base_fill = random.randint(10, 40)
            elif neighborhood in needs_attention:
                # High demand areas have higher fill levels
                base_fill = random.randint(60, 85)
            else:
                # Other neighborhoods have moderate fill levels
                base_fill = random.randint(30, 60)

            # Add some random variation but keep neighborhood consistency
            variation = random.randint(5, 15)
            neighborhood_fill_patterns[neighborhood] = {
                "base_fill": base_fill,
                "variation": variation,
            }

        # Get the pattern for this neighborhood
        pattern = neighborhood_fill_patterns[neighborhood]

        # Calculate fill level with variation but keep neighborhood pattern
        fill_level = max(
            5,
            min(
                95,
                pattern["base_fill"]
                + random.randint(-pattern["variation"], pattern["variation"]),
            ),
        )

        # Adjust for waste type (organic tends to fill faster, glass slower)
        if waste_category == "Organic":
            fill_level = min(95, fill_level + random.randint(5, 15))
        elif waste_category == "Glass":
            fill_level = max(5, fill_level - random.randint(5, 15))

        # Status based on fill level
        status = "Open" if fill_level < 80 or random.random() > 0.7 else "Closed"

        # Last emptied date correlates with fill level
        days_ago = int((fill_level / 100) * 14)  # 0% = just emptied, 100% = 14 days
        last_emptied = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

        # Determine capacity based on container type (default value)
        capacity_kg = 500

        containers.append(
            {
                "id": container_id,
                "neighborhood": neighborhood,
                "lat": coords[1],  # Ensure correct order (lat, lon)
                "lon": coords[0],
                "waste_category": waste_category,
                "fill_level": fill_level,
                "status": status,
                "last_emptied": last_emptied,
                "capacity_kg": capacity_kg,
            }
        )

    return pd.DataFrame(containers)


@st.cache_data
def generate_amsterdam_waste_data():
    """Generate sample data for Amsterdam waste management dashboard"""

    # Create container data
    containers = _generate_container_data()

    # Create waste collection data
    collection_data = _generate_collection_data()

    # Create waste complaints
    complaints = _generate_complaints_data(containers)

    # Create neighborhood statistics
    neighborhood_stats = _generate_neighborhood_stats(containers, complaints)

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


def _generate_container_data():
    """Generate sample container data"""
    containers = []
    for neighborhood in NEIGHBORHOODS:
        # Number of containers in this neighborhood
        n_containers = random.randint(5, 100)

        # Base coordinates with offsets for different neighborhoods
        base_lat = AMSTERDAM_CENTER[0] + random.uniform(-0.05, 0.05)
        base_lon = AMSTERDAM_CENTER[1] + random.uniform(-0.05, 0.05)

        for i in range(n_containers):
            container_type = random.choice(CONTAINER_TYPES)
            waste_type = random.choice(WASTE_CATEGORIES)

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
    return containers


def _generate_collection_data():
    """Generate sample waste collection data"""
    collection_dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
    collection_data = []

    for date in collection_dates:
        for category in WASTE_CATEGORIES:
            collection_data.append(
                {
                    "date": date,
                    "waste_category": category,
                    "amount_kg": random.randint(500, 5000)
                    + (50 * (date.dayofweek == 1))  # More on Tuesdays
                    + (100 if category == "General Waste" else 0),  # More general waste
                }
            )
    return collection_data


def _generate_complaints_data(containers):
    """Generate sample waste complaint data"""
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

        neighborhood = random.choice(NEIGHBORHOODS)
        complaint_type = random.choice(COMPLAINT_TYPES)

        complaints.append(
            {
                "time": submission_time,
                "neighborhood": neighborhood,
                "complaint_type": complaint_type,
                "description": f"Resident reported {complaint_type.lower()} at {neighborhood}",
                "status": status,
                "container_id": f"{random.choice(NEIGHBORHOODS)[:3]}-{random.randint(1, 999):03d}"
                if random.random() > 0.3
                else "N/A",
            }
        )

    complaints.sort(key=lambda x: x["time"], reverse=True)
    return complaints


def _generate_neighborhood_stats(containers, complaints):
    """Generate neighborhood statistics based on containers and complaints"""
    neighborhood_stats = []
    for neighborhood in NEIGHBORHOODS:
        neighborhood_containers = [
            c for c in containers if c["neighborhood"] == neighborhood
        ]

        neighborhood_stats.append(
            {
                "neighborhood": neighborhood,
                "total_containers": len(neighborhood_containers),
                "smart_bins": len(
                    [c for c in neighborhood_containers if c["type"] == "Smart Bin"]
                ),
                "recycling_rate": random.uniform(0.2, 0.8),
                "complaints_count": len(
                    [c for c in complaints if c["neighborhood"] == neighborhood]
                ),
                "avg_fill_level": np.mean(
                    [c["fill_level"] for c in neighborhood_containers]
                )
                if neighborhood_containers
                else 0,
            }
        )
    return neighborhood_stats


# Helper functions for data manipulation
def filter_container_data(container_df, waste_category=None, neighborhood=None):
    """Filter container data based on selected criteria"""
    filtered_df = container_df.copy()

    if waste_category and waste_category != "All Categories":
        filtered_df = filtered_df[filtered_df["waste_category"] == waste_category]

    if neighborhood and neighborhood != "All Neighborhoods":
        filtered_df = filtered_df[filtered_df["neighborhood"] == neighborhood]

    return filtered_df


def filter_complaints_data(complaints_df, status_filter=None, neighborhood=None):
    """Filter complaints data based on selected criteria"""
    filtered_df = complaints_df.copy()

    if status_filter:
        filtered_df = filtered_df[filtered_df["status"].isin(status_filter)]

    if neighborhood and neighborhood != "All Neighborhoods":
        filtered_df = filtered_df[filtered_df["neighborhood"] == neighborhood]

    return filtered_df


def get_high_fill_containers(container_df, threshold=80, limit=5):
    """Get containers with high fill levels"""
    return (
        container_df[container_df["fill_level"] > threshold]
        .sort_values("fill_level", ascending=False)
        .head(limit)
    )


def get_waste_trend_data(collection_df, days=10):
    """Prepare data for waste collection trends chart"""
    daily_collection = (
        collection_df.groupby(["date", "waste_category"])["amount_kg"]
        .sum()
        .reset_index()
    )
    # Only show the last n days for clarity
    return daily_collection[
        daily_collection["date"]
        >= daily_collection["date"].max() - pd.Timedelta(days=days)
    ]


def get_waste_type_colors():
    """Return mapping of waste types to colors"""
    return {
        "Recycling": [46, 139, 87],
        "Rest": [128, 128, 128],
        "General Waste": [128, 128, 128],
        "Paper/Carton": [70, 130, 180],
        "Glass": [0, 128, 128],
        "Organic": [139, 69, 19],
        "Plastic": [255, 165, 0],
        "Textiles": [218, 112, 214],
        "Unknown": [200, 200, 200],
    }
