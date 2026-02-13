import streamlit as st

from negotiation_rules_state import get_active_rules, save_global_rules, set_active_rules


st.title("Negotiation Rules")
st.markdown(
    """
Configure negotiation behavior before starting the simulation.
Rules are global and shared across all scenarios.
"""
)
rules = get_active_rules()

mode_options = ["cooperative", "competitive", "mixed"]
max_rounds_value = rules.get("max_rounds", 10)
mode_value = str(rules.get("mode", "competitive")).strip().lower()
allow_partial_value = rules.get("allow_partial_agreements", True)
require_unanimous_value = rules.get("require_unanimous_agreement", True)

if mode_value not in mode_options:
    mode_value = "competitive"

layout_col_left, layout_col_right = st.columns([1, 1], gap="large")

with layout_col_left:
    first_row_left, first_row_right = st.columns([1, 1])
    with first_row_left:
        max_rounds = st.number_input(
            "Max Rounds",
            min_value=1,
            step=1,
            value=int(max_rounds_value) if isinstance(max_rounds_value, int) else 10,
        )
    with first_row_right:
        mode = st.selectbox(
            "Mode",
            mode_options,
            index=mode_options.index(mode_value),
        )

    allow_partial_agreements = st.toggle(
        "Allow Partial Agreements",
        value=bool(allow_partial_value),
    )
    st.caption("Allow agreements on only part of the negotiation package.")

    require_unanimous_agreement = st.toggle(
        "Require Unanimous Agreement",
        value=bool(require_unanimous_value),
    )
    st.caption("Require all parties to explicitly agree before closing the negotiation.")

updated_rules = {
    "max_rounds": int(max_rounds),
    "mode": mode,
    "allow_partial_agreements": bool(allow_partial_agreements),
    "require_unanimous_agreement": bool(require_unanimous_agreement),
}

if updated_rules != rules:
    save_global_rules(updated_rules)
    set_active_rules(updated_rules)
    st.success("Global negotiation rules updated.")

with layout_col_right:
    st.subheader("Negotiation Rules Preview")
    st.json(updated_rules, expanded=True)
