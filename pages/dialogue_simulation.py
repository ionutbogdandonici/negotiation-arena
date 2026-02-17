import json
from datetime import datetime, timezone
from uuid import uuid4

import streamlit as st
import pandas as pd
from langchain_anthropic import ChatAnthropic

from core.director import NegotiationDirector
from negotiation_rules_state import get_active_rules
from run_results_store import append_global_result
from scenario_state import get_active_scenario

if "history" not in st.session_state:
    st.session_state.history = []
if "round" not in st.session_state:
    st.session_state.round = 0
if "director" not in st.session_state:
    st.session_state.director = None
if "round_evaluations" not in st.session_state:
    st.session_state.round_evaluations = []
if "evaluation" not in st.session_state:
    st.session_state.evaluation = None
if "evaluations_df" not in st.session_state:
    st.session_state.evaluations_df = pd.DataFrame()
if "final_evaluation" not in st.session_state:
    st.session_state.final_evaluation = None
if "final_evaluation_meta" not in st.session_state:
    st.session_state.final_evaluation_meta = None
if "run_id" not in st.session_state:
    st.session_state.run_id = str(uuid4())
if "run_started_at_utc" not in st.session_state:
    st.session_state.run_started_at_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
if "run_saved" not in st.session_state:
    st.session_state.run_saved = False

st.title("Dialogue Simulation")

active_file, active_payload = get_active_scenario()
if isinstance(active_payload, dict):
    active_scenario_name = active_payload.get("name", active_file or "Unknown Scenario")
else:
    active_scenario_name = active_file or "No scenario selected"

if not isinstance(active_payload, dict):
    st.warning("Select a scenario from Home before starting the dialogue.")
    st.stop()

active_rules = get_active_rules()
director_payload = {**active_payload, "negotiation_rules": dict(active_rules)}
agents_model_name = str(active_rules.get("agents_model", "claude-sonnet-4-5-20250929")).strip()
round_judge_model_name = str(active_rules.get("judge_model", "claude-sonnet-4-5-20250929")).strip()
final_judge_model_name = str(
    active_rules.get("final_judge_model", round_judge_model_name or "claude-sonnet-4-5-20250929")
).strip()
agents_temperature = float(active_rules.get("agents_temperature", 0.3))
round_judge_temperature = float(active_rules.get("judge_temperature", 0.1))
final_judge_temperature = float(active_rules.get("final_judge_temperature", round_judge_temperature))
if not agents_model_name:
    agents_model_name = "claude-sonnet-4-5-20250929"
if not round_judge_model_name:
    round_judge_model_name = "claude-sonnet-4-5-20250929"
if not final_judge_model_name:
    final_judge_model_name = round_judge_model_name


# Factory for model instances; customize this per agent if needed.
def llm_factory(_spec):
    return ChatAnthropic(model=agents_model_name, temperature=agents_temperature)


def _scenario_signature(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True)


def _normalize_agreement_status(value) -> str:
    if not isinstance(value, str):
        return "ongoing"
    label = value.split(":", 1)[0].strip().lower()
    if label in {"reached", "failed", "ongoing"}:
        return label
    return "ongoing"


def _is_numeric_metric(metric_spec: dict) -> bool:
    metric_type = str(metric_spec.get("type", "")).lower()
    return metric_type not in {"boolean", "enum", "multiclass", "categorical"}


def _utility_sign(metric_spec: dict) -> int:
    utility_score = str(metric_spec.get("utility_score", "positive")).strip().lower()
    if utility_score in {"negative", "minus", "-1"}:
        return -1
    return 1


def _round_utility_total(evaluation: dict, metrics: dict) -> int | None:
    if not isinstance(evaluation, dict) or not isinstance(metrics, dict):
        return None

    total = 0
    has_values = False
    for metric_name, metric_spec in metrics.items():
        if not isinstance(metric_spec, dict) or not _is_numeric_metric(metric_spec):
            continue
        metric_value = _to_int(evaluation.get(metric_name))
        if metric_value is None:
            continue
        total += _utility_sign(metric_spec) * metric_value
        has_values = True

    return total if has_values else None


def _utility_total_history_json() -> str:
    metrics = active_payload.get("metrics", {}) if isinstance(active_payload, dict) else {}
    history_items = []
    for round_item in st.session_state.get("round_evaluations", []):
        if not isinstance(round_item, dict):
            continue
        round_id = _to_int(round_item.get("round"))
        evaluation = round_item.get("evaluation", {})
        utility_total = _round_utility_total(evaluation, metrics)
        if round_id is None:
            continue
        history_items.append(
            {
                "round": round_id,
                "utility_total": utility_total,
            }
        )
    return json.dumps(history_items, ensure_ascii=True)


def _conversation_history_json(history: list[dict]) -> str:
    messages = []
    for item in history:
        if not isinstance(item, dict):
            continue
        agent = str(item.get("agent", "")).strip()
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        messages.append(f"{agent}: {content}" if agent else content)
    return json.dumps(messages, ensure_ascii=True)


def _new_run_identity() -> None:
    st.session_state.run_id = str(uuid4())
    st.session_state.run_started_at_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    st.session_state.run_saved = False


def _build_global_result_row(
    director: NegotiationDirector,
    final_evaluation: dict | None,
) -> dict:
    agents = active_payload.get("agents", []) if isinstance(active_payload, dict) else []
    final_eval = final_evaluation if isinstance(final_evaluation, dict) else {}
    latest_round_eval = st.session_state.get("evaluation", {})
    if not isinstance(latest_round_eval, dict):
        latest_round_eval = {}
    agreement_status = _normalize_agreement_status(
        final_eval.get("agreement_status", director.latest_agreement_status)
    )

    def _final_metric_value(metric_name: str):
        value = _to_int(final_eval.get(metric_name))
        if value is not None:
            return value
        return _to_int(latest_round_eval.get(metric_name))

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": st.session_state.get("run_id", ""),
        "scenario_file": active_file or "",
        "scenario_name": active_scenario_name,
        "num_agents": len(agents) if isinstance(agents, list) else 0,
        "agents_model": agents_model_name,
        "agents_temperature": agents_temperature,
        "round_judge_model": round_judge_model_name,
        "round_judge_temperature": round_judge_temperature,
        "final_judge_model": final_judge_model_name,
        "final_judge_temperature": final_judge_temperature,
        "mode": str(active_rules.get("mode", "")),
        "max_rounds": director.max_rounds,
        "effective_rounds": director.round,
        "allow_partial_agreements": bool(active_rules.get("allow_partial_agreements", True)),
        "require_unanimous_agreement": bool(active_rules.get("require_unanimous_agreement", True)),
        "agreement_status": agreement_status,
        "conversation_history": _conversation_history_json(director.get_history()),
        "utility_total_history": _utility_total_history_json(),
        "unanimous": final_eval.get("unanimous", ""),
        "final_persuasion": _final_metric_value("persuasion"),
        "final_deception": _final_metric_value("deception"),
        "final_concession": _final_metric_value("concession"),
        "final_cooperation": _final_metric_value("cooperation"),
        "final_summary": final_eval.get("summary", ""),
        "interaction_pattern": final_eval.get("interaction_pattern", ""),
        "dominant_agent": final_eval.get("dominant_agent", ""),
    }


def _persist_run_result(
    director: NegotiationDirector,
    final_evaluation: dict | None,
) -> None:
    if st.session_state.get("run_saved"):
        return
    if director.round <= 0 and not director.get_history():
        return

    row = _build_global_result_row(
        director=director,
        final_evaluation=final_evaluation,
    )
    append_global_result(row)
    st.session_state.run_saved = True


def get_or_create_director() -> NegotiationDirector:
    # Reuse the director in session state until the selected scenario changes.
    current_file = st.session_state.get("director_scenario_file")
    current_signature = st.session_state.get("director_scenario_signature")
    active_signature = _scenario_signature(director_payload)
    should_recreate = (
        st.session_state.director is None
        or current_file != active_file
        or current_signature != active_signature
    )

    if should_recreate:
        previous_director = st.session_state.director
        had_existing_director = previous_director is not None
        if (
            had_existing_director
            and previous_director.round > 0
            and not previous_director.is_terminated
            and not st.session_state.get("run_saved")
        ):
            _persist_run_result(
                director=previous_director,
                final_evaluation=None,
            )
        st.session_state.director = NegotiationDirector(director_payload, llm_factory)
        st.session_state.director_scenario_file = active_file
        st.session_state.director_scenario_signature = active_signature

        # Keep UI state aligned when scenario/rules change.
        if had_existing_director:
            st.session_state.history = []
            st.session_state.round = 0
            st.session_state.round_evaluations = []
            st.session_state.evaluation = None
            st.session_state.evaluations_df = pd.DataFrame()
            st.session_state.final_evaluation = None
            st.session_state.final_evaluation_meta = None
            _new_run_identity()
    return st.session_state.director


def advance_round_and_evaluate():
    # Execute one full round and immediately evaluate the updated transcript.
    director = get_or_create_director()
    if not director.can_advance():
        return

    if director.get_history():
        input_message = director.get_history()[-1]["content"]
    else:
        input_message = "Let's begin the negotiation. Present your first proposal."

    turn_messages = director.step(input_message)

    judge_llm = ChatAnthropic(model=round_judge_model_name, temperature=round_judge_temperature)
    evaluation = director.evaluate_round(judge_llm)
    director.register_evaluation(evaluation)

    st.session_state.history = director.get_history()
    st.session_state.round = director.round
    st.session_state.evaluation = evaluation
    st.session_state.round_evaluations.append(
        {
            "round": director.round,
            "turn_messages": turn_messages,
            "evaluation": evaluation,
        }
    )
    row = _build_evaluation_row(director.round, evaluation)
    st.session_state.evaluations_df = pd.concat(
        [st.session_state.evaluations_df, pd.DataFrame([row])],
        ignore_index=True,
    )
    _maybe_run_final_evaluation(director)


def advance_until_end() -> int:
    rounds_executed = 0
    director = get_or_create_director()
    while director.can_advance():
        advance_round_and_evaluate()
        rounds_executed += 1
        director = get_or_create_director()
    return rounds_executed


def _build_evaluation_row(round_id: int, evaluation: dict) -> dict:
    row = {"round": round_id}
    for key, value in evaluation.items():
        if isinstance(value, list):
            row[key] = ", ".join(str(item) for item in value)
        elif isinstance(value, dict):
            row[key] = str(value)
        else:
            row[key] = value
    return row


def _maybe_run_final_evaluation(director: NegotiationDirector) -> None:
    if not director.is_terminated:
        return

    meta = {
        "scenario_file": active_file,
        "round": director.round,
        "termination_reason": director.termination_reason,
        "history_len": len(director.get_history()),
    }
    if st.session_state.get("final_evaluation_meta") == meta:
        existing_final = st.session_state.get("final_evaluation")
        if not st.session_state.get("run_saved") and isinstance(existing_final, dict):
            _persist_run_result(
                director=director,
                final_evaluation=existing_final,
            )
        return

    final_judge_llm = ChatAnthropic(model=final_judge_model_name, temperature=final_judge_temperature)
    final_evaluation = director.evaluate_final(final_judge_llm)
    st.session_state.final_evaluation = final_evaluation
    st.session_state.final_evaluation_meta = meta
    _persist_run_result(
        director=director,
        final_evaluation=final_evaluation,
    )


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _metric_delta(current_value, previous_value):
    current_int = _to_int(current_value)
    previous_int = _to_int(previous_value)
    if current_int is None or previous_int is None:
        return None
    return current_int - previous_int


def _normalize_enum_label(value):
    if not isinstance(value, str):
        return None
    return value.split(":", 1)[0].strip().lower()


def _enum_color_map(metric_spec: dict) -> dict[str, str]:
    color_map: dict[str, str] = {}
    values = metric_spec.get("values", [])
    if not isinstance(values, list):
        return color_map

    for raw_value in values:
        if not isinstance(raw_value, str):
            continue
        parts = raw_value.split(":", 1)
        label = parts[0].strip().lower()
        color = parts[1].strip().lower() if len(parts) == 2 else "gray"
        if label:
            color_map[label] = color
    return color_map


def _render_judge_evaluation(current_eval: dict, previous_eval: dict, metric_specs: dict):
    numeric_metrics: list[tuple[str, str, str]] = []

    for metric_name, metric_spec in metric_specs.items():
        label = metric_name.replace("_", " ").title()
        metric_type = str(metric_spec.get("type", "")).lower()

        if metric_type == "boolean":
            metric_value = current_eval.get(metric_name, "Unknown")
            if isinstance(metric_value, bool):
                st.badge(
                    f"{label}: {metric_value}",
                    color="green" if metric_value else "red",
                )
            else:
                st.caption(f"{label}: {metric_value}")
            continue

        if metric_type in ("enum", "multiclass", "categorical"):
            metric_value = current_eval.get(metric_name)
            normalized_value = _normalize_enum_label(metric_value)
            color_map = _enum_color_map(metric_spec)
            if normalized_value:
                st.badge(
                    f"{label}: {normalized_value}",
                    color=color_map.get(normalized_value, "gray"),
                )
            else:
                st.caption(f"{label}: {metric_value if metric_value is not None else 'Unknown'}")
            continue

        numeric_metrics.append((metric_name, label, f"{metric_name}_top_words"))

    if numeric_metrics:
        first_col, second_col = st.columns(2)
        for index, (metric_name, label, top_words_key) in enumerate(numeric_metrics):
            current_value = _to_int(current_eval.get(metric_name))
            previous_value = _to_int(previous_eval.get(metric_name))
            target_col = first_col if index % 2 == 0 else second_col

            with target_col:
                st.metric(
                    label=label,
                    value=current_value if current_value is not None else "N/A",
                    delta=_metric_delta(current_value, previous_value),
                )
                top_words = current_eval.get(top_words_key)
                if (
                    isinstance(top_words, list)
                    and len(top_words) == 2
                    and all(isinstance(word, str) for word in top_words)
                ):
                    st.caption(f"Top drivers: {top_words[0]}, {top_words[1]}")

    st.write(current_eval.get("summary", "No summary provided."))


def reset_dialogue():
    director = get_or_create_director()
    if director.round > 0 and not director.is_terminated:
        _persist_run_result(
            director=director,
            final_evaluation=None,
        )
    director.reset()
    st.session_state.history = []
    st.session_state.round = 0
    st.session_state.evaluation = None
    st.session_state.round_evaluations = []
    st.session_state.evaluations_df = pd.DataFrame()
    st.session_state.final_evaluation = None
    st.session_state.final_evaluation_meta = None
    _new_run_identity()


director = get_or_create_director()
can_advance_conversation = director.can_advance()
_maybe_run_final_evaluation(director)

with st.expander("Configuration & Status", expanded=False):
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("### Configuration")
        st.write(f"**Scenario**: {active_scenario_name}")
        st.write(f"**Mode**: {str(active_rules.get('mode', 'competitive')).capitalize()}")

    with col_b:
        st.markdown("### Progress")
        st.write(f"**Rounds completed**: {st.session_state.round}")
        st.write(f"**Max rounds**: {director.max_rounds}")

        if director.is_terminated:
            st.write("")
            if director.termination_reason == "reached":
                st.success("Agreement reached")
            elif director.termination_reason == "failed":
                st.error("Agreement failed")
            elif director.termination_reason == "stalled":
                st.warning("Stalled (max rounds)")

    with col_c:
        st.markdown("### Models")
        st.write(f"**Agents**: {agents_model_name}")
        st.write(f"**Agents temp**: {agents_temperature}")
        st.write(f"**Round judge**: {round_judge_model_name}")
        st.write(f"**Round judge temp**: {round_judge_temperature}")
        st.write(f"**Final judge**: {final_judge_model_name}")
        st.write(f"**Final judge temp**: {final_judge_temperature}")

col1, col2, col3 = st.columns([2, 2, 2], vertical_alignment="bottom")
with col1:
    if st.button("Advance Conversation", width="stretch", disabled=not can_advance_conversation):
        with st.spinner("Running round and evaluating..."):
            advance_round_and_evaluate()
with col2:
    if st.button("Reset", width="stretch"):
        reset_dialogue()
with col3:
    if st.button("Advance Until End", width="stretch", disabled=not can_advance_conversation):
        with st.spinner("Running conversation until termination..."):
            completed_rounds = advance_until_end()
        st.info(f"Auto-advanced {completed_rounds} round(s).")

if director.is_terminated and isinstance(st.session_state.get("final_evaluation"), dict):
    st.success("Final judge evaluation is available in the Verdict page.")

st.subheader("Round by Round")
if not st.session_state.round_evaluations:
    st.info("No dialogue yet. Click 'Advance Conversation' to run the first round of negotiation.")
else:
    metric_specs = active_payload.get("metrics", {})
    for idx, item in enumerate(st.session_state.round_evaluations):
        prev_eval = (
            st.session_state.round_evaluations[idx - 1]["evaluation"]
            if idx > 0
            else {}
        )
        round_id = item.get("round")
        turn_messages = item.get("turn_messages", [])
        current_eval = item.get("evaluation", {})

        st.markdown(f"**Round {round_id}**")
        dialogue_col, judge_col = st.columns([3, 1], gap="small", vertical_alignment="top")

        with dialogue_col:
            with st.container(border=True):
                for msg in turn_messages:
                    with st.chat_message(msg.get("agent", "Agent")):
                        st.write(msg.get("content", ""))

        with judge_col:
            with st.container(border=True):
                _render_judge_evaluation(current_eval, prev_eval, metric_specs)
