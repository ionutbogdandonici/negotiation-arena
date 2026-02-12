from copy import deepcopy

import streamlit as st

from scenario_state import get_active_scenario, list_scenario_files, load_scenario, set_active_scenario


st.title("Negotiation Rules")
st.markdown(
    """
Configure negotiation behavior before starting the simulation.
Rules are loaded from `scenario.negotiation_rules` and saved to the active scenario in session.
"""
)


def _format_label(key: str) -> str:
    return key.replace("_", " ").title()


def _resolve_rule_spec(rule_value):
    if isinstance(rule_value, dict) and "type" in rule_value:
        spec_type = str(rule_value.get("type", "string")).lower()
        default_value = rule_value.get("value")
        values = rule_value.get("values")
        description = rule_value.get("description")
        return {
            "kind": "spec",
            "type": spec_type,
            "default": default_value,
            "values": values if isinstance(values, list) else None,
            "description": description if isinstance(description, str) else None,
            "source": rule_value,
        }

    if isinstance(rule_value, bool):
        return {"kind": "raw", "type": "boolean", "default": rule_value, "source": rule_value}
    if isinstance(rule_value, int) and not isinstance(rule_value, bool):
        return {"kind": "raw", "type": "integer", "default": rule_value, "source": rule_value}
    if isinstance(rule_value, float):
        return {"kind": "raw", "type": "number", "default": rule_value, "source": rule_value}
    if isinstance(rule_value, str):
        return {"kind": "raw", "type": "string", "default": rule_value, "source": rule_value}

    return {"kind": "raw", "type": "string", "default": str(rule_value), "source": rule_value}


def _render_rule_input(rule_name: str, rule_spec: dict):
    key = f"negotiation_rule_{rule_name}"
    rule_type = rule_spec["type"]
    default_value = rule_spec["default"]
    values = rule_spec.get("values")

    if rule_type == "boolean":
        return st.toggle(_format_label(rule_name), value=bool(default_value), key=key)

    if rule_type == "integer":
        safe_value = int(default_value) if isinstance(default_value, int) else 0
        return st.number_input(_format_label(rule_name), value=safe_value, step=1, key=key)

    if rule_type in ("number", "float"):
        safe_value = float(default_value) if isinstance(default_value, (int, float)) else 0.0
        return st.number_input(_format_label(rule_name), value=safe_value, key=key)

    if rule_type in ("enum", "multiclass", "categorical") and isinstance(values, list) and values:
        normalized_values = [str(v) for v in values]
        safe_value = str(default_value) if default_value is not None else normalized_values[0]
        index = normalized_values.index(safe_value) if safe_value in normalized_values else 0
        return st.selectbox(_format_label(rule_name), normalized_values, index=index, key=key)

    safe_value = "" if default_value is None else str(default_value)
    return st.text_input(_format_label(rule_name), value=safe_value, key=key)


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

rules = active_payload.get("negotiation_rules")
if not isinstance(rules, dict) or not rules:
    st.warning("No `negotiation_rules` block found in the active scenario.")
    st.stop()

updated_rules = {}
for rule_name, rule_value in rules.items():
    spec = _resolve_rule_spec(rule_value)
    with st.container(border=True):
        description = spec.get("description")
        if description:
            st.caption(description)
        new_value = _render_rule_input(rule_name, spec)

    if spec["kind"] == "spec":
        updated_spec = deepcopy(spec["source"])
        updated_spec["value"] = new_value
        updated_rules[rule_name] = updated_spec
    else:
        updated_rules[rule_name] = new_value

if updated_rules != rules:
    updated_payload = deepcopy(active_payload)
    updated_payload["negotiation_rules"] = updated_rules
    set_active_scenario(active_file, updated_payload)
    st.success("Negotiation rules updated for the active scenario.")

with st.expander("Negotiation Rules Preview"):
    st.json(updated_rules, expanded=False)
