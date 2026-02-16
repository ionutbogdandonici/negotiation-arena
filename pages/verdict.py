import pandas as pd
import plotly.express as px
import streamlit as st

from scenario_state import get_active_scenario


METRIC_ALIASES = {
    "fairness": ["fairness", "perceived_fairness"],
    "manipulativeness": ["manipulativeness", "manipulation_risk"],
}


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_non_empty(*values):
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _metric_value(row: dict, metric_name: str):
    keys = [metric_name] + METRIC_ALIASES.get(metric_name, [])
    for key in keys:
        value = _to_int(row.get(key))
        if value is not None:
            return value
    return None


def _utility_sign(metric_spec: dict) -> int:
    utility_score = str(metric_spec.get("utility_score", "positive")).strip().lower()
    return -1 if utility_score in {"negative", "minus", "-1"} else 1


st.title("Verdict")

active_file, active_payload = get_active_scenario()
final_evaluation = st.session_state.get("final_evaluation")
final_evaluation_meta = st.session_state.get("final_evaluation_meta")
final_matches_active_scenario = (
    isinstance(final_evaluation_meta, dict)
    and final_evaluation_meta.get("scenario_file") == active_file
)
final_ready = (
    isinstance(final_evaluation, dict)
    and final_evaluation
    and final_matches_active_scenario
)
if not final_ready:
    st.info(
        "Final verdict not available yet. The final judge runs only after the negotiation is terminated."
    )
    st.stop()

evaluations_df = st.session_state.get("evaluations_df")
if not isinstance(evaluations_df, pd.DataFrame) or evaluations_df.empty:
    st.info("No round data available to build verdict charts.")
    st.stop()

if "round" not in evaluations_df.columns:
    evaluations_df = evaluations_df.copy()
    evaluations_df["round"] = range(1, len(evaluations_df) + 1)

evaluations_df = evaluations_df.sort_values("round").reset_index(drop=True)
records = evaluations_df.to_dict(orient="records")

metrics = active_payload.get("metrics", {}) if isinstance(active_payload, dict) else {}
numeric_metric_names = [
    metric_name
    for metric_name, metric_spec in metrics.items()
    if isinstance(metric_spec, dict)
    and str(metric_spec.get("type", "")).lower() not in {"boolean", "enum", "multiclass", "categorical"}
]

utility_rows = []
for row in records:
    total = 0
    has_values = False
    for metric_name in numeric_metric_names:
        metric_value = _metric_value(row, metric_name)
        if metric_value is None:
            continue
        total += _utility_sign(metrics.get(metric_name, {})) * metric_value
        has_values = True
    utility_rows.append({"Round": row.get("round"), "Utility Total": total if has_values else None})

utility_df = pd.DataFrame(utility_rows).dropna(subset=["Utility Total"])
if utility_df.empty:
    st.info("Utility total is not available yet.")
    st.stop()

utility_df["Direction"] = utility_df["Utility Total"].apply(
    lambda value: "Positive" if value >= 0 else "Negative"
)
fig = px.line(
    utility_df,
    x="Round",
    y="Utility Total",
    color="Direction",
    color_discrete_map={"Positive": "#2E8B57", "Negative": "#B22222"},
)

fig.update_layout(
            showlegend=True,
        )
fig.update_traces(line={"width": 5})
fig.update_legends(title_text="Utility", orientation="h", yanchor="bottom", y=-0.3, xanchor="left", x=0)
fig.update_yaxes(range=[-20, 30])
st.plotly_chart(fig, width="stretch")

st.subheader("Outcome Explanation")
verdict_row = final_evaluation
st.caption("Using final judge evaluation.")
st.caption(
    "Metric guide: persuasion (0-10) = ability to influence with arguments; "
    "deception (0-10) = use of misleading/manipulative tactics; "
    "concession (0-10) = willingness to make trade-offs; "
    "cooperation (0-10) = collaborative, solution-oriented behavior; "
    "agreement_type = none/partial/full; "
    "unanimous = whether all parties explicitly confirmed the agreement; "
    "interaction_pattern = scripted/adaptive/mixed."
)
latest_row = records[-1] if records else {}


def _diagnostic_metric(metric_name: str):
    final_value = _to_int(verdict_row.get(metric_name))
    if final_value is not None:
        return final_value
    return _to_int(latest_row.get(metric_name))

diag_cols = st.columns(4)
diagnostic_metrics = ["persuasion", "deception", "concession", "cooperation"]
for index, metric_name in enumerate(diagnostic_metrics):
    metric_value = _diagnostic_metric(metric_name)
    with diag_cols[index]:
        st.metric(
            metric_name.title(),
            metric_value if metric_value is not None else "N/A",
        )

interaction_pattern = _first_non_empty(verdict_row.get("interaction_pattern"))
dominant_agent = _first_non_empty(verdict_row.get("dominant_agent"))
dominance_method = _first_non_empty(verdict_row.get("dominance_method"))
could_do_better = _first_non_empty(verdict_row.get("could_do_better"))
outcome_explanation = _first_non_empty(
    verdict_row.get("outcome_explanation"),
    verdict_row.get("summary"),
)

if interaction_pattern:
    st.badge(f"Interaction pattern: {interaction_pattern}", color="blue")
if dominant_agent:
    st.badge(f"Dominant agent: {dominant_agent}", color="orange")

if dominance_method:
    st.write(f"**How dominance happened:** {dominance_method}")
if could_do_better:
    st.write(f"**Could do better:** {could_do_better}")
if outcome_explanation:
    st.write(f"**Why this outcome happened:** {outcome_explanation}")
else:
    st.caption("Run at least one evaluated round to generate an explanation.")
