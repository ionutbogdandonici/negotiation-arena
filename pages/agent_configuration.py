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
model_options = [
    "claude-opus-4-6",
    "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5-20251001",
]

mode_options = ["cooperative", "competitive", "mixed"]
max_rounds_value = rules.get("max_rounds", 10)
mode_value = str(rules.get("mode", "competitive")).strip().lower()
allow_partial_value = rules.get("allow_partial_agreements", True)
require_unanimous_value = rules.get("require_unanimous_agreement", True)
agents_model_value = str(rules.get("agents_model", model_options[1])).strip()
judge_model_value = str(rules.get("judge_model", model_options[1])).strip()
final_judge_model_value = str(rules.get("final_judge_model", judge_model_value or model_options[1])).strip()
agents_temperature_value = float(rules.get("agents_temperature", 0.3))
judge_temperature_value = float(rules.get("judge_temperature", 0.1))
final_judge_temperature_value = float(rules.get("final_judge_temperature", judge_temperature_value))

if mode_value not in mode_options:
    mode_value = "competitive"

col_sx, col_dx = st.columns([3, 1], vertical_alignment="top", gap="large")
with col_sx:
    row_1 = st.container()

    with row_1:
        st.subheader("Simulation Settings")
        col1, col2 = st.columns([1, 1], vertical_alignment="top")
        with col1:
            max_rounds = st.number_input(
                        "Max Rounds",
                        min_value=1,
                        step=1,
                        help="Maximum number of rounds before automatic stop (`stalled`).",
                        value=int(max_rounds_value) if isinstance(max_rounds_value, int) else 10,
                    )
        with col2:
            mode = st.selectbox(
                "Mode",
                mode_options,
                help="Negotiation behavior policy (`cooperative`, `competitive`, `mixed`).",
                index=mode_options.index(mode_value),
            )
        
        col1, col2 = st.columns([1, 1], vertical_alignment="top")
        with col1:
            allow_partial_agreements = st.toggle(
                "Allow Partial Agreements",
                help="If enabled, agents may agree on only part of the package.",
                value=bool(allow_partial_value),
            )
            st.caption("Allow agreements on only part of the negotiation package.")
        with col2:
            require_unanimous_agreement = st.toggle(
                "Require Unanimous Agreement",
                help="If enabled, all parties must explicitly confirm before closure.",
                value=bool(require_unanimous_value),
            )
            st.caption("Require all parties to explicitly agree before closing the negotiation.")
    row_2 = st.container()
    with row_2:
        st.subheader("Models Settings")
        col1, col2, col3 = st.columns([1, 1, 1], vertical_alignment="top", gap="large")
        with col1:
            st.markdown("##### From Scenario Agents")
            agents_model = st.selectbox(
                "Single Agent Model",
                model_options,
                help="Model used to generate agent turns.",
                index=model_options.index(agents_model_value)
                if agents_model_value in model_options
                else 1,
            )
            agents_temperature = st.slider(
                "Single Agent Temperature",
                help="Randomness level for agent responses (0 = deterministic, 2 = more diverse).",
                min_value=0.0,
                max_value=2.0,
                step=0.1,
                value=max(0.0, min(2.0, round(agents_temperature_value, 1))),
            )
        with col2:
            st.markdown("##### Round Annotator")
            judge_model = st.selectbox(
                "Annotator Model",
                model_options,
                help="Model used to annotate each negotiation round.",
                index=model_options.index(judge_model_value)
                if judge_model_value in model_options
                else 1,
            )
            judge_temperature = st.slider(
                "Annotator Temperature",
                help="Randomness level for per-round evaluations (0 = deterministic, 2 = more diverse).",
                min_value=0.0,
                max_value=2.0,
                step=0.1,
                value=max(0.0, min(2.0, round(judge_temperature_value, 1))),
            )
        with col3:
            st.markdown("##### Final Judge")
            final_judge_model = st.selectbox(
                "Final Judge Model",
                model_options,
                help="Model used for final judgment of negotiation outcomes.",
                index=model_options.index(final_judge_model_value)
                if final_judge_model_value in model_options
                else (
                    model_options.index(judge_model)
                    if judge_model in model_options
                    else 1
                ),
            )
            final_judge_temperature = st.slider(
                "Final Judge Temperature",
                help="Randomness level for final verdict generation (0 = deterministic, 2 = more diverse).",
                min_value=0.0,
                max_value=2.0,
                step=0.1,
                value=max(0.0, min(2.0, round(final_judge_temperature_value, 1))),
            )

updated_rules = {
    "max_rounds": int(max_rounds),
    "mode": mode,
    "allow_partial_agreements": bool(allow_partial_agreements),
    "require_unanimous_agreement": bool(require_unanimous_agreement),
    "agents_model": str(agents_model).strip(),
    "judge_model": str(judge_model).strip(),
    "final_judge_model": str(final_judge_model).strip(),
    "agents_temperature": float(agents_temperature),
    "judge_temperature": float(judge_temperature),
    "final_judge_temperature": float(final_judge_temperature),
}

with col_dx:
    st.subheader("Negotiation Rules JSON")
    st.json(updated_rules, expanded=True)
    if updated_rules != rules:
        save_global_rules(updated_rules)
        set_active_rules(updated_rules)
        st.success("Global negotiation rules updated.")

