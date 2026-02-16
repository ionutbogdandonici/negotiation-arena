import streamlit as st

from scenario_state import get_active_scenario, list_scenario_files, load_scenario, set_active_scenario

st.title("How Do Cooperative and Adversarial Behaviours Emerge Among LLM Agents in Negotiation?")

scenario_files = list_scenario_files()

if not scenario_files:
    st.error("No scenario JSON found in `scenarios/`. Add at least one `.json` file.")
    st.stop()

current_file, _ = get_active_scenario()
default_idx = scenario_files.index(current_file) if current_file in scenario_files else 0
selected_file = st.selectbox("Select scenario", scenario_files, index=default_idx)

if current_file != selected_file:
    try:
        with st.spinner(f"Loading scenario: {selected_file}..."):
            selected_payload = load_scenario(selected_file)
            set_active_scenario(selected_file, selected_payload)
    except Exception as exc:
        st.error(f"Unable to load scenario `{selected_file}`: {exc}")
        st.stop()

active_file, active_payload = get_active_scenario()
if active_payload is None:
    try:
        with st.spinner(f"Loading scenario: {selected_file}..."):
            active_payload = load_scenario(selected_file)
            set_active_scenario(selected_file, active_payload)
            active_file = selected_file
    except Exception as exc:
        st.error(f"Unable to load scenario `{selected_file}`: {exc}")
        st.stop()

st.success(f"Active scenario: {active_file}")
