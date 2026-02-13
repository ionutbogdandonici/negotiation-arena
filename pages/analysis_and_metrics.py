import pandas as pd
import streamlit as st
import plotly.express as px
from scenario_state import (
    get_active_scenario,
    list_scenario_files,
    load_scenario,
    set_active_scenario,
)


METRIC_ALIASES = {
    "fairness": ["fairness", "perceived_fairness"],
    "manipulativeness": ["manipulativeness", "manipulation_risk"],
}

def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coalesce_numeric(row: dict, keys: list[str]):
    for key in keys:
        value = _to_int(row.get(key))
        if value is not None:
            return value
    return None


def _normalize_enum_label(value):
    if not isinstance(value, str):
        return None
    return value.split(":", 1)[0].strip().lower()


def _agreement_status_and_color(row: dict) -> tuple[str, str]:
    # Backward compatibility with old boolean metric.
    legacy = row.get("agreement_reached")
    if isinstance(legacy, bool):
        return ("reached", "green") if legacy else ("failed", "red")

    status = _normalize_enum_label(row.get("agreement_status"))
    if status == "reached":
        return "reached", "green"
    if status == "failed":
        return "failed", "red"
    if status == "ongoing":
        return "ongoing", "blue"
    return "unknown", "gray"


def _metric_aliases(metric_name: str) -> list[str]:
    aliases = METRIC_ALIASES.get(metric_name, [metric_name])
    if metric_name not in aliases:
        return [metric_name] + aliases
    return aliases


def _metric_value(row: dict, metric_name: str):
    return _coalesce_numeric(row, _metric_aliases(metric_name))


def _is_numeric_metric(metric_spec: dict) -> bool:
    metric_type = str(metric_spec.get("type", "")).lower()
    return metric_type not in {"boolean", "enum", "multiclass", "categorical"}


def _metric_label(metric_name: str) -> str:
    return metric_name.replace("_", " ").title()


def _utility_sign(metric_spec: dict) -> int:
    utility_score = str(metric_spec.get("utility_score", "positive")).strip().lower()
    if utility_score in {"negative", "minus", "-1"}:
        return -1
    return 1


def _build_evaluations_df() -> pd.DataFrame:
    df = st.session_state.get("evaluations_df")
    if isinstance(df, pd.DataFrame) and not df.empty:
        return df.copy()

    rows = []
    for item in st.session_state.get("round_evaluations", []):
        round_id = item.get("round")
        evaluation = item.get("evaluation", {})
        row = {"round": round_id}
        for key, value in evaluation.items():
            if isinstance(value, list):
                row[key] = ", ".join(str(x) for x in value)
            elif isinstance(value, dict):
                row[key] = str(value)
            else:
                row[key] = value
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


st.title("Preliminary Results")

evaluations_df = _build_evaluations_df()
if evaluations_df.empty:
    st.info("No judge data yet. Run at least one round in Dialogue Simulation.")
    st.stop()

if "round" not in evaluations_df.columns:
    evaluations_df["round"] = range(1, len(evaluations_df) + 1)

evaluations_df = evaluations_df.sort_values("round").reset_index(drop=True)
records = evaluations_df.to_dict(orient="records")
round_items = {
    item.get("round"): item
    for item in st.session_state.get("round_evaluations", [])
    if isinstance(item, dict)
}
active_file, active_payload = get_active_scenario()
if not isinstance(active_payload, dict):
    scenario_files = list_scenario_files()
    if scenario_files:
        fallback_file = scenario_files[0]
        try:
            fallback_payload = load_scenario(fallback_file)
            set_active_scenario(fallback_file, fallback_payload)
            active_file, active_payload = fallback_file, fallback_payload
            st.info(f"No active scenario in session. Loaded default: {fallback_file}")
        except Exception as exc:
            st.warning(f"Unable to load default scenario `{fallback_file}`: {exc}")
            active_payload = {}
    else:
        active_payload = {}

scenario_metrics = active_payload.get("metrics", {}) if isinstance(active_payload, dict) else {}

numeric_metric_names = [
    metric_name
    for metric_name, metric_spec in scenario_metrics.items()
    if isinstance(metric_spec, dict) and _is_numeric_metric(metric_spec)
]
if not numeric_metric_names:
    numeric_metric_names = [
        "fairness",
        "cooperativeness",
        "manipulativeness",
        "conversation_quality",
        "ambiguity",
    ]

series_rows = []
utility_rows = []
agreement_round = None
for row in records:
    round_id = row.get("round")
    series_row = {"Round": round_id}
    utility_total = 0
    has_utility_values = False

    for metric_name in numeric_metric_names:
        metric_value = _metric_value(row, metric_name)
        series_row[_metric_label(metric_name)] = metric_value
        if metric_value is None:
            continue
        metric_spec = scenario_metrics.get(metric_name, {}) if isinstance(scenario_metrics, dict) else {}
        utility_total += _utility_sign(metric_spec) * metric_value
        has_utility_values = True

    series_rows.append(series_row)
    utility_rows.append(
        {
            "Round": round_id,
            "Utility Total": utility_total if has_utility_values else None,
        }
    )

    status, _ = _agreement_status_and_color(row)
    if agreement_round is None and status == "reached":
        agreement_round = round_id

st.subheader("Records Table")
st.dataframe(evaluations_df, use_container_width=True)

st.subheader("Judge Metrics Over Rounds")
plot_df = pd.DataFrame(series_rows)
utility_df = pd.DataFrame(utility_rows)
trend_col, utility_col = st.columns([3, 2], gap="small")

with trend_col:
    metric_columns = [col for col in plot_df.columns if col != "Round"]
    if metric_columns:
        long_df = plot_df.melt(id_vars=["Round"], value_vars=metric_columns, var_name="Metric", value_name="Value")
        long_df = long_df.dropna(subset=["Value"])
        if not long_df.empty:
            trend_fig = px.line(long_df, x="Round", y="Value", color="Metric")
            trend_fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            trend_fig.update_yaxes(range=[0, 10])
            trend_fig.update_traces(line={"width": 3})
            trend_fig.update_legends(title_text="Metrics", orientation="h", yanchor="bottom", y=-0.3, xanchor="left", x=0)
            st.plotly_chart(trend_fig, width="stretch")
        else:
            st.caption("No numeric metric values available yet.")
    else:
        st.caption("No numeric metrics found in the active scenario.")

with utility_col:
    utility_plot = utility_df.dropna(subset=["Utility Total"]).copy()
    if not utility_plot.empty:
        utility_plot["Direction"] = utility_plot["Utility Total"].apply(
            lambda value: "Positive" if value >= 0 else "Negative"
        )
        utility_fig = px.line(
            utility_plot,
            x="Round",
            y="Utility Total",
            color="Direction",
            color_discrete_map={"Positive": "#2E8B57", "Negative": "#B22222"},
        )
        utility_fig.update_layout(
            showlegend=True,
        )
        utility_fig.update_traces(line={"width": 5})
        utility_fig.update_legends(title_text="Utility", orientation="h", yanchor="bottom", y=-0.3, xanchor="left", x=0)
        utility_fig.update_yaxes(range=[-20, 30])
        st.plotly_chart(utility_fig, width="stretch")
    else:
        st.caption("Utility total unavailable.")


st.subheader("Judge Report by Iteration")
metric_aliases = [(_metric_label(metric_name), _metric_aliases(metric_name)) for metric_name in numeric_metric_names]

report_details = st.expander("Details for each round", expanded=False)
with report_details:
    for idx, row in enumerate(records):
        prev_row = records[idx - 1] if idx > 0 else {}
        round_id = row.get("round")

        with st.container(border=True):
            st.markdown(f"**Round {round_id}**")

            status, color = _agreement_status_and_color(row)
            st.badge(f"Agreement status: {status}", color=color)

            columns = st.columns(5)
            for col_idx, (label, aliases) in enumerate(metric_aliases):
                current_value = _coalesce_numeric(row, aliases)
                previous_value = _coalesce_numeric(prev_row, aliases)
                delta = None
                if current_value is not None and previous_value is not None:
                    delta = current_value - previous_value

                with columns[col_idx]:
                    st.metric(
                        label=label,
                        value=current_value if current_value is not None else "N/A",
                        delta=delta,
                    )

            summary = row.get("summary")
            if isinstance(summary, str) and summary.strip():
                st.write(f"Summary: {summary}")

            round_item = round_items.get(round_id, {})
            turn_messages = round_item.get("turn_messages", [])
            with st.expander("Conversation"):
                if turn_messages:
                    for msg in turn_messages:
                        speaker = msg.get("agent", "Agent")
                        content = msg.get("content", "")
                        st.markdown(f"**{speaker}:** {content}")
                else:
                    st.caption("No conversation details available for this round.")
