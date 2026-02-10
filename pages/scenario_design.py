import streamlit as st

from scenario_state import get_active_scenario, list_scenario_files, load_scenario, set_active_scenario

st.title("Scenario Design")
st.markdown("""
Negotiation settings such as:

- resource division (splitting items or money)
- task scheduling (allocating responsibilities)
- preference alignment (choosing the best option for both parties))

Each agent receives private information or asymmetric incentives encoded in its prompt.
""")

active_file, active_payload = get_active_scenario()

if active_payload is None:
    scenario_files = list_scenario_files()
    if scenario_files:
        fallback_file = scenario_files[0]
        try:
            fallback_payload = load_scenario(fallback_file)
            set_active_scenario(fallback_file, fallback_payload)
            active_file, active_payload = fallback_file, fallback_payload
            st.info(f"No scenario selected in Home. Loaded default: {fallback_file}")
        except Exception as exc:
            st.error(f"Unable to load default scenario `{fallback_file}`: {exc}")
            st.stop()
    else:
        st.error("No scenario JSON found in `scenarios/`.")
        st.stop()

st.caption(f"Scenario file: {active_file}")
st.json(active_payload, expanded=True)
