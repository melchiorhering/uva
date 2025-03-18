import streamlit as st
import plotly.express as px


def render_waste_category_pie(waste_by_category):
    """Render pie chart showing waste by category"""
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


def render_neighborhood_containers_chart(neighborhood_df):
    """Render bar chart showing containers by neighborhood"""
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
