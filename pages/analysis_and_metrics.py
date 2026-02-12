import pandas as pd
import streamlit as st
import plotly.express as px

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


st.title("Analysis and Metrics")

evaluations_df = _build_evaluations_df()
if evaluations_df.empty:
    st.info("No judge data yet. Run at least one round in Dialogue Simulation.")
    st.stop()

if "round" not in evaluations_df.columns:
    evaluations_df["round"] = range(1, len(evaluations_df) + 1)

evaluations_df = evaluations_df.sort_values("round").reset_index(drop=True)
records = evaluations_df.to_dict(orient="records")

series_rows = []
agreement_round = None
for row in records:
    round_id = row.get("round")
    series_row = {
        "Round": round_id,
        "Fairness": _coalesce_numeric(row, ["fairness", "perceived_fairness"]),
        "Cooperativeness": _coalesce_numeric(row, ["cooperativeness"]),
        "Manipulativeness": _coalesce_numeric(row, ["manipulativeness", "manipulation_risk"]),
        "Conversation Quality": _coalesce_numeric(row, ["conversation_quality"]),
        "Ambiguity": _coalesce_numeric(row, ["ambiguity"]),
    }
    series_rows.append(series_row)

    status, _ = _agreement_status_and_color(row)
    if agreement_round is None and status == "reached":
        agreement_round = round_id

st.subheader("Records Table")
st.dataframe(evaluations_df, use_container_width=True)

st.subheader("Judge Metrics Over Rounds")
#plot_df = pd.DataFrame(series_rows).set_index("Round")
#fig = px.line(plot_df, x=plot_df.index, y=plot_df.columns.tolist())
#fig.update_yaxes(range=[0, 10],)
#fig.update_traces(line=dict(width=5))
#st.plotly_chart(fig, use_container_width=True)

st.subheader("Rounds to Agreement")
if agreement_round is None:
    st.metric("Rounds to Agreement", "Not reached")
else:
    st.metric("Rounds to Agreement", agreement_round)

st.subheader("Judge Report by Iteration")
metric_aliases = [
    ("Fairness", ["fairness", "perceived_fairness"]),
    ("Cooperativeness", ["cooperativeness"]),
    ("Manipulativeness", ["manipulativeness", "manipulation_risk"]),
    ("Conversation Quality", ["conversation_quality"]),
    ("Ambiguity", ["ambiguity"]),
]

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
