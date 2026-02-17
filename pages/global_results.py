import json

import pandas as pd
import plotly.express as px
import streamlit as st

from run_results_store import load_global_results


OUTCOME_COLOR_MAP = {
    "stalled": "#1f77b4",  # blue
    "reached": "#2ca02c",  # green
    "failed": "#d62728",   # red
}


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_status(value) -> str:
    if not isinstance(value, str):
        return "unknown"
    label = value.split(":", 1)[0].strip().lower()
    if label in {"reached", "failed", "ongoing"}:
        return label
    return "unknown"


def _classify_outcome(row: pd.Series) -> str:
    status = _normalize_status(row.get("agreement_status"))
    if status in {"reached", "failed"}:
        return status

    effective_rounds = _to_int(row.get("effective_rounds"))
    max_rounds = _to_int(row.get("max_rounds"))
    if (
        status == "ongoing"
        and effective_rounds is not None
        and max_rounds is not None
        and max_rounds > 0
        and effective_rounds >= max_rounds
    ):
        return "stalled"
    return "other"


def _parse_utility_total_history(value) -> list[dict[str, int]]:
    if isinstance(value, list):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
    else:
        return []

    if not isinstance(parsed, list):
        return []

    history = []
    for idx, item in enumerate(parsed, start=1):
        if isinstance(item, dict):
            round_id = _to_int(item.get("round"))
            utility_total = _to_int(item.get("utility_total"))
        else:
            round_id = idx
            utility_total = _to_int(item)

        if round_id is None:
            round_id = idx
        if utility_total is None:
            continue

        history.append(
            {
                "Round": round_id,
                "Utility Total": utility_total,
            }
        )
    return history


st.title("Global Results")

rows = load_global_results()
if not rows:
    st.info("No saved experiments yet. Complete or stop a simulation to persist a run.")
    st.stop()

df = pd.DataFrame(rows)
if "timestamp_utc" in df.columns:
    df = df.sort_values("timestamp_utc", ascending=False).reset_index(drop=True)

scenario_options = ["All"] + sorted(df["scenario_name"].dropna().unique().tolist()) if "scenario_name" in df.columns else ["All"]
selected_scenario = st.selectbox("Scenario", scenario_options, index=0)
if selected_scenario != "All" and "scenario_name" in df.columns:
    df = df[df["scenario_name"] == selected_scenario].reset_index(drop=True)

status_series = df.get("agreement_status", pd.Series(index=df.index, dtype=str)).apply(_normalize_status)
outcome_series = df.apply(_classify_outcome, axis=1)
total_runs = len(df)
reached_runs = int((status_series == "reached").sum())
failed_runs = int((status_series == "failed").sum())
stalled_runs = int((outcome_series == "stalled").sum())

metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
with metric_col_1:
    st.metric("Runs", total_runs)
with metric_col_2:
    st.metric("Reached", reached_runs)
with metric_col_3:
    st.metric("Failed", failed_runs)
with metric_col_4:
    st.metric("Stalled", stalled_runs)

st.dataframe(df, width="stretch")
st.download_button(
    "Download CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="global_results_export.csv",
    mime="text/csv",
)

st.subheader("Utility Trends")
utility_rows = []
for idx, row in df.reset_index(drop=True).iterrows():
    run_id = str(row.get("run_id", "")).strip()
    scenario_name = str(row.get("scenario_name", "")).strip() or "Unknown"
    timestamp_utc = str(row.get("timestamp_utc", "")).strip()
    run_key = run_id or f"row_{idx + 1}"
    run_label = run_id[:8] if run_id else f"run_{idx + 1}"
    outcome_class = _classify_outcome(row)

    for point in _parse_utility_total_history(row.get("utility_total_history", "")):
        utility_rows.append(
            {
                "run_key": run_key,
                "run_id": run_id,
                "run_label": run_label,
                "scenario_name": scenario_name,
                "timestamp_utc": timestamp_utc,
                "outcome_class": outcome_class,
                "Round": point["Round"],
                "Utility Total": point["Utility Total"],
            }
        )

if not utility_rows:
    st.info("Utility history not available yet. Run a new simulation to populate utility_total_history.")
else:
    utility_df = pd.DataFrame(utility_rows)
    classified_df = utility_df[utility_df["outcome_class"].isin(["reached", "failed", "stalled"])].copy()
    if classified_df.empty:
        st.info("Not enough classified runs yet (reached/failed/stalled) to compute utility averages.")
    else:
        scenario_names = sorted(classified_df["scenario_name"].dropna().unique().tolist())
        for scenario_name in scenario_names:
            scenario_df = classified_df[classified_df["scenario_name"] == scenario_name].copy()
            if scenario_df.empty:
                continue

            st.markdown(f"### {scenario_name}")
            trend_col, final_col = st.columns([3, 2], gap="small")

            trend_df = scenario_df.groupby(["outcome_class", "Round"], as_index=False)["Utility Total"].mean()
            with trend_col:
                trend_fig = px.line(
                    trend_df,
                    x="Round",
                    y="Utility Total",
                    color="outcome_class",
                    color_discrete_map=OUTCOME_COLOR_MAP,
                    markers=True,
                    category_orders={"outcome_class": ["reached", "failed", "stalled"]},
                    title="Average Utility Trajectory by Outcome",
                )
                trend_fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(trend_fig, width="stretch")

            with final_col:
                final_utility_df = scenario_df.sort_values("Round").groupby("run_key", as_index=False).tail(1)
                global_avg_df = final_utility_df.groupby("outcome_class", as_index=False).agg(
                    avg_utility=("Utility Total", "mean"),
                    runs=("run_key", "nunique"),
                )
                global_avg_df = global_avg_df.rename(columns={"avg_utility": "Average Utility"})
                avg_fig = px.bar(
                    global_avg_df,
                    x="outcome_class",
                    y="Average Utility",
                    color="outcome_class",
                    color_discrete_map=OUTCOME_COLOR_MAP,
                    category_orders={"outcome_class": ["reached", "failed", "stalled"]},
                    text="runs",
                    title="Average Final Utility by Outcome",
                )
                avg_fig.update_traces(texttemplate="runs=%{text}", textposition="outside")
                avg_fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), xaxis_title="Outcome")
                st.plotly_chart(avg_fig, width="stretch")

st.subheader("Average Round Duration by Outcome")
duration_rows = []
for idx, row in df.reset_index(drop=True).iterrows():
    outcome_class = _classify_outcome(row)
    if outcome_class not in {"reached", "failed", "stalled"}:
        continue

    effective_rounds = _to_int(row.get("effective_rounds"))
    if effective_rounds is None:
        continue

    scenario_name = str(row.get("scenario_name", "")).strip() or "Unknown"
    run_id = str(row.get("run_id", "")).strip()
    run_key = run_id or f"row_{idx + 1}"
    duration_rows.append(
        {
            "scenario_name": scenario_name,
            "outcome_class": outcome_class,
            "effective_rounds": effective_rounds,
            "run_key": run_key,
        }
    )

if not duration_rows:
    st.info("Round duration data not available yet.")
else:
    duration_df = pd.DataFrame(duration_rows)
    scenario_names = sorted(duration_df["scenario_name"].dropna().unique().tolist())
    if not scenario_names:
        st.info("No scenario data available for duration charts.")
    else:
        scenario_cols = st.columns(len(scenario_names))
        for idx, scenario_name in enumerate(scenario_names):
            scenario_duration_df = duration_df[duration_df["scenario_name"] == scenario_name].copy()
            if scenario_duration_df.empty:
                continue

            avg_duration_df = scenario_duration_df.groupby("outcome_class", as_index=False).agg(
                avg_rounds=("effective_rounds", "mean"),
                runs=("run_key", "nunique"),
            )
            duration_fig = px.bar(
                avg_duration_df,
                x="outcome_class",
                y="avg_rounds",
                color="outcome_class",
                color_discrete_map=OUTCOME_COLOR_MAP,
                category_orders={"outcome_class": ["reached", "failed", "stalled"]},
                text="runs",
                title=scenario_name,
            )
            duration_fig.update_traces(texttemplate="runs=%{text}", textposition="outside")
            duration_fig.update_layout(
                margin=dict(l=10, r=10, t=40, b=10),
                xaxis_title="Outcome",
                yaxis_title="Average Rounds",
                showlegend=False,
            )
            with scenario_cols[idx]:
                st.plotly_chart(duration_fig, width="stretch")
