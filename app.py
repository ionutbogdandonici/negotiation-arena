import streamlit as st

# Streamlit configuration
st.set_page_config(layout="wide")

# Add pages to a list
home_page = st.Page("pages/home.py", title="Home")
scenario_design_page = st.Page("pages/scenario_design.py", title="Scenario Design")

pages = {
    "Home": [st.Page("pages/home.py", title="Home", icon=":material/dashboard:")],
    "Implementation": [
        st.Page("pages/scenario_design.py",
                title="Scenario Design",
                icon=":material/account_tree:"),
        st.Page("pages/agent_configuration.py",
                title="Agent Configuration",
                icon=":material/settings_suggest:"),
        st.Page("pages/dialogue_simulation.py",
                title="Dialogue Simulation",
                icon=":material/psychology:"),
        st.Page("pages/analysis_and_metrics.py",
                title="Analysis and Metrics",
                icon=":material/insights:")
    ]
}

# Configure navigation
core = st.navigation(pages)
# Execute
core.run()
