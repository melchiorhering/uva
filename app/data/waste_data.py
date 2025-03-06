import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import streamlit as st

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
        n_containers = random.randint(5, 20)

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
