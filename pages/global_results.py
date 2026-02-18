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
TABLE_OUTCOME_ORDER = ["failed", "ongoing", "reached"]
TABLE_MODE_ORDER = ["cooperative", "competitive", "mixed"]
DIAGNOSTIC_OUTCOME_ORDER = ["reached", "failed", "ongoing"]
DIAGNOSTIC_COLUMNS = [
    ("Persuasion", "final_persuasion"),
    ("Deception", "final_deception"),
    ("Concession", "final_concession"),
    ("Cooperation", "final_cooperation"),
]


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


def _build_mode_outcome_table(source_df: pd.DataFrame) -> pd.DataFrame:
    display_columns = ["Mode", "Failed", "Ongoing", "Reached"]
    if "mode" not in source_df.columns or "agreement_status" not in source_df.columns:
        return pd.DataFrame(columns=display_columns)

    working_df = source_df[["mode", "agreement_status"]].copy()
    working_df["mode"] = working_df["mode"].fillna("").astype(str).str.strip().str.lower()
    working_df["outcome"] = working_df["agreement_status"].apply(_normalize_status)
    working_df = working_df[
        working_df["mode"].isin(TABLE_MODE_ORDER)
        & working_df["outcome"].isin(TABLE_OUTCOME_ORDER)
    ]
    if working_df.empty:
        return pd.DataFrame(columns=display_columns)

    counts_df = (
        working_df.groupby(["mode", "outcome"])
        .size()
        .unstack(fill_value=0)
        .reindex(index=TABLE_MODE_ORDER, columns=TABLE_OUTCOME_ORDER, fill_value=0)
    )
    percentages_df = counts_df.div(counts_df.sum(axis=1).replace(0, pd.NA), axis=0) * 100.0
    percentages_df = percentages_df.fillna(0.0)
    percentages_df = (
        percentages_df.rename(
            index=lambda value: value.capitalize(),
            columns={
                "failed": "Failed",
                "ongoing": "Ongoing",
                "reached": "Reached",
            },
        )
        .reset_index()
        .rename(columns={"mode": "Mode"})
    )
    return percentages_df[display_columns]


def _build_diagnostics_outcome_table(source_df: pd.DataFrame) -> pd.DataFrame:
    display_columns = ["Outcome", "Persuasion", "Deception", "Concession", "Cooperation"]
    if "agreement_status" not in source_df.columns:
        return pd.DataFrame(columns=display_columns)

    metric_sources = [source_col for _, source_col in DIAGNOSTIC_COLUMNS]
    if any(source_col not in source_df.columns for source_col in metric_sources):
        return pd.DataFrame(columns=display_columns)

    working_df = source_df[["agreement_status", *metric_sources]].copy()
    working_df["outcome"] = working_df["agreement_status"].apply(_normalize_status)
    working_df = working_df[working_df["outcome"].isin(DIAGNOSTIC_OUTCOME_ORDER)]
    if working_df.empty:
        return pd.DataFrame(columns=display_columns)

    for source_col in metric_sources:
        working_df[source_col] = pd.to_numeric(working_df[source_col], errors="coerce")

    diagnostics_df = (
        working_df.groupby("outcome", as_index=True)[metric_sources]
        .mean(numeric_only=True)
        .reindex(DIAGNOSTIC_OUTCOME_ORDER)
        .rename(
            index=lambda value: value.capitalize(),
            columns={source_col: label for label, source_col in DIAGNOSTIC_COLUMNS},
        )
        .reset_index()
        .rename(columns={"outcome": "Outcome"})
    )
    return diagnostics_df[display_columns]


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

all_scenarios = sorted(df["scenario_name"].dropna().unique().tolist()) if "scenario_name" in df.columns else []
scenario_options = ["All"] + all_scenarios
selected_scenario = st.selectbox("Scenario (table)", scenario_options, index=0)
df_table = df.copy()
if selected_scenario != "All" and "scenario_name" in df_table.columns:
    df_table = df_table[df_table["scenario_name"] == selected_scenario].reset_index(drop=True)

if not all_scenarios:
    st.info("No scenario names available in global results.")
    st.stop()

default_chart_scenario = (
    selected_scenario if selected_scenario in all_scenarios else all_scenarios[0]
)
selected_chart_scenario = st.selectbox(
    "Scenario (charts)",
    all_scenarios,
    index=all_scenarios.index(default_chart_scenario),
)
df_charts = df[df["scenario_name"] == selected_chart_scenario].reset_index(drop=True)

status_series = df_table.get("agreement_status", pd.Series(index=df_table.index, dtype=str)).apply(_normalize_status)
outcome_series = df_table.apply(_classify_outcome, axis=1)
total_runs = len(df_table)
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

st.dataframe(df_table, width="stretch")
st.download_button(
    "Download CSV",
    data=df_table.to_csv(index=False).encode("utf-8"),
    file_name="global_results_export.csv",
    mime="text/csv",
)

mode_outcome_table_df = _build_mode_outcome_table(df)
diagnostics_table_df = _build_diagnostics_outcome_table(df)

summary_table_col_1, summary_table_col_2 = st.columns(2, gap="large")
with summary_table_col_1:
    st.subheader("Outcome distribution by negotiation mode (percentages)")
    if mode_outcome_table_df.empty:
        st.info("Not enough mode/outcome data available yet.")
    else:
        mode_outcome_display_df = mode_outcome_table_df.copy()
        for col_name in ["Failed", "Ongoing", "Reached"]:
            mode_outcome_display_df[col_name] = mode_outcome_display_df[col_name].map(lambda value: f"{value:.1f}%")
        st.table(mode_outcome_display_df)

with summary_table_col_2:
    st.subheader("Mean diagnostic metrics by outcome (0-10 scale)")
    if diagnostics_table_df.empty:
        st.info("Not enough diagnostic data available yet.")
    else:
        diagnostics_display_df = diagnostics_table_df.copy()
        for col_name in ["Persuasion", "Deception", "Concession", "Cooperation"]:
            diagnostics_display_df[col_name] = diagnostics_display_df[col_name].map(
                lambda value: "-" if pd.isna(value) else f"{value:.2f}"
            )
        st.table(diagnostics_display_df)

st.subheader("Utility Trends")
utility_rows = []
for idx, row in df_charts.reset_index(drop=True).iterrows():
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
    st.info(f"Utility history not available yet for scenario: {selected_chart_scenario}.")
else:
    utility_df = pd.DataFrame(utility_rows)
    classified_df = utility_df[utility_df["outcome_class"].isin(["reached", "failed", "stalled"])].copy()
    if classified_df.empty:
        st.info(f"Not enough classified runs yet for scenario: {selected_chart_scenario}.")
    else:
        trend_col, final_col = st.columns([3, 2], gap="small")

        trend_df = classified_df.groupby(["outcome_class", "Round"], as_index=False)["Utility Total"].mean()
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
            final_utility_df = classified_df.sort_values("Round").groupby("run_key", as_index=False).tail(1)
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


        duration_rows = []
        for idx, row in df_charts.reset_index(drop=True).iterrows():
            outcome_class = _classify_outcome(row)
            if outcome_class not in {"reached", "failed", "stalled"}:
                continue

            effective_rounds = _to_int(row.get("effective_rounds"))
            if effective_rounds is None:
                continue

            run_id = str(row.get("run_id", "")).strip()
            run_key = run_id or f"row_{idx + 1}"
            duration_rows.append(
                {
                    "outcome_class": outcome_class,
                    "effective_rounds": effective_rounds,
                    "run_key": run_key,
                }
            )

        if not duration_rows:
            st.caption(f"Round duration unavailable for scenario: {selected_chart_scenario}.")
        else:
            duration_df = pd.DataFrame(duration_rows)
            avg_duration_df = duration_df.groupby("outcome_class", as_index=False).agg(
                avg_rounds=("effective_rounds", "mean"),
                runs=("run_key", "nunique"),
            )
            duration_col, mode_col = st.columns([2, 1], gap="small")
            with duration_col:
                duration_fig = px.bar(
                    avg_duration_df,
                    x="avg_rounds",
                    y="outcome_class",
                    orientation="h",
                    color="outcome_class",
                    color_discrete_map=OUTCOME_COLOR_MAP,
                    category_orders={"outcome_class": ["reached", "failed", "stalled"]},
                    text="runs",
                    title="Avg Rounds by Outcome",
                )
                duration_fig.update_traces(texttemplate="runs=%{text}", textposition="outside")
                duration_fig.update_layout(
                    margin=dict(l=10, r=10, t=40, b=10),
                    xaxis_title="Avg Rounds",
                    yaxis_title="Outcome",
                    showlegend=False,
                )
                st.plotly_chart(duration_fig, width="stretch")

            with mode_col:
                mode_rows = []
                for _, mode_row in df_charts.reset_index(drop=True).iterrows():
                    effective_rounds = _to_int(mode_row.get("effective_rounds"))
                    if effective_rounds is None:
                        continue
                    mode_name = str(mode_row.get("mode", "")).strip().lower() or "unknown"
                    mode_rows.append({"mode": mode_name, "rounds": effective_rounds})

                if not mode_rows:
                    st.caption(f"Mode data unavailable for scenario: {selected_chart_scenario}.")
                else:
                    mode_df = pd.DataFrame(mode_rows).groupby("mode", as_index=False).agg(
                        rounds=("rounds", "sum")
                    )
                    mode_fig = px.pie(
                        mode_df,
                        names="mode",
                        values="rounds",
                        title="Rounds by Mode",
                    )
                    mode_fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(mode_fig, width="stretch")
