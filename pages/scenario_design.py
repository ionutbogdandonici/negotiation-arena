import streamlit as st

from scenario_state import get_active_scenario, list_scenario_files, load_scenario, set_active_scenario

st.title("Scenario Design")


def _render_items_in_columns(items, empty_message: str, label_prefix: str) -> None:
    if isinstance(items, dict):
        entries = list(items.items())
        cols = st.columns(len(entries), border=True)
        for i, (key, value) in enumerate(entries):
            with cols[i]:
                st.markdown(f"**{key}**")
                st.json(value, expanded=False)
        return

    if isinstance(items, list) and items:
        cols = st.columns(len(items), border=True)
        for i, item in enumerate(items):
            title = f"{label_prefix} {i + 1}"
            if isinstance(item, dict):
                item_name = item.get("name") or item.get("id")
                if item_name:
                    title = str(item_name)
            with cols[i]:
                st.markdown(f"**{title}**")
                st.json(item, expanded=False)
        return

    st.info(empty_message)


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
st.subheader("Agents")
agents = active_payload.get("agents", [])
_render_items_in_columns(agents, "No agents defined in this scenario.", "Agent")

st.subheader("Resources to Negotiate")
resources = active_payload.get("resources_to_negotiate", {})
_render_items_in_columns(
    resources, "No resources to negotiate defined in this scenario.", "Resource"
)

st.subheader("Metrics")
metrics = active_payload.get("metrics", {})
_render_items_in_columns(metrics, "No metrics defined in this scenario.", "Metric")
