import streamlit as st


def load_css(file_path: str):
    with open(file_path, "r") as f:
        st.html(f"<style>{f.read()}</style>")
