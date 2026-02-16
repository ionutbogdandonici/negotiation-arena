import json
from pathlib import Path
from typing import Any

import streamlit as st


RULES_PATH = Path("config") / "negotiation_rules.json"
DEFAULT_RULES = {
    "max_rounds": 10,
    "mode": "competitive",
    "allow_partial_agreements": True,
    "require_unanimous_agreement": True,
    "agents_model": "claude-sonnet-4-5-20250929",
    "judge_model": "claude-sonnet-4-5-20250929",
    "final_judge_model": "claude-sonnet-4-5-20250929",
}
MODE_OPTIONS = {"cooperative", "competitive", "mixed"}


def _read_rule_value(value: Any, default: Any) -> Any:
    if isinstance(value, dict) and "value" in value:
        return value.get("value", default)
    if value is None:
        return default
    return value


def _normalize_rules(raw_rules: dict[str, Any]) -> dict[str, Any]:
    max_rounds = _read_rule_value(raw_rules.get("max_rounds"), DEFAULT_RULES["max_rounds"])
    mode = str(_read_rule_value(raw_rules.get("mode"), DEFAULT_RULES["mode"])).strip().lower()
    allow_partial = _read_rule_value(
        raw_rules.get("allow_partial_agreements"), DEFAULT_RULES["allow_partial_agreements"]
    )
    require_unanimous = _read_rule_value(
        raw_rules.get("require_unanimous_agreement"), DEFAULT_RULES["require_unanimous_agreement"]
    )
    agents_model = str(
        _read_rule_value(raw_rules.get("agents_model"), DEFAULT_RULES["agents_model"])
    ).strip()
    judge_model = str(
        _read_rule_value(raw_rules.get("judge_model"), DEFAULT_RULES["judge_model"])
    ).strip()
    final_judge_model = str(
        _read_rule_value(raw_rules.get("final_judge_model"), judge_model or DEFAULT_RULES["final_judge_model"])
    ).strip()

    if not isinstance(max_rounds, int) or max_rounds < 1:
        max_rounds = DEFAULT_RULES["max_rounds"]
    if mode not in MODE_OPTIONS:
        mode = DEFAULT_RULES["mode"]
    if not agents_model:
        agents_model = DEFAULT_RULES["agents_model"]
    if not judge_model:
        judge_model = DEFAULT_RULES["judge_model"]
    if not final_judge_model:
        final_judge_model = judge_model

    return {
        "max_rounds": int(max_rounds),
        "mode": mode,
        "allow_partial_agreements": bool(allow_partial),
        "require_unanimous_agreement": bool(require_unanimous),
        "agents_model": agents_model,
        "judge_model": judge_model,
        "final_judge_model": final_judge_model,
    }


def load_global_rules() -> dict[str, Any]:
    if not RULES_PATH.exists():
        return DEFAULT_RULES.copy()

    try:
        with RULES_PATH.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return DEFAULT_RULES.copy()

    if not isinstance(raw, dict):
        return DEFAULT_RULES.copy()
    return _normalize_rules(raw)


def save_global_rules(rules: dict[str, Any]) -> None:
    normalized = _normalize_rules(rules)
    RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RULES_PATH.open("w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=True)


def set_active_rules(rules: dict[str, Any]) -> None:
    st.session_state.active_negotiation_rules = _normalize_rules(rules)


def get_active_rules() -> dict[str, Any]:
    active = st.session_state.get("active_negotiation_rules")
    if isinstance(active, dict):
        normalized = _normalize_rules(active)
        st.session_state.active_negotiation_rules = normalized
        return normalized

    loaded = load_global_rules()
    st.session_state.active_negotiation_rules = loaded
    return loaded
