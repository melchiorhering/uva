import streamlit as st


navigation = st.navigation(
    [
        st.Page(
            "routes/homepage.py",
            title="Amsterdam Waste Management",
            icon=":material/delete:",
            default=True,
        ),
        st.Page(
            "routes/statistics.py", title="Second page", icon=":material/favorite:"
        ),
    ]
)
navigation.run()
