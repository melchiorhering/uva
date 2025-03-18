import streamlit as st


navigation = st.navigation(
    [
        st.Page(
            "routes/homepage.py",
            title="Amsterdam Waste Management",
            icon=":material/delete:",
            default=True,
        ),
        # st.Page("routes/map.py", title="Map", icon=":material/favorite:"),
    ]
)
navigation.run()
