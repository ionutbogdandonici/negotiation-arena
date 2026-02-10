import json
from pathlib import Path

import streamlit as st


SCENARIOS_DIR = Path("scenarios")


def list_scenario_files() -> list[str]:
    if not SCENARIOS_DIR.exists():
        return []
    return sorted(
        p.name for p in SCENARIOS_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".json"
    )


def load_scenario(filename: str) -> dict:
    """Load a scenario JSON file and return its content as a dictionary."""
    path = SCENARIOS_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def set_active_scenario(filename: str, payload: dict) -> None:
    """Set the active scenario in Streamlit session state."""
    st.session_state.active_scenario_file = filename
    st.session_state.active_scenario = payload


def get_active_scenario() -> tuple[str | None, dict | None]:
    """Get the active scenario from Streamlit session state."""
    return (
        st.session_state.get("active_scenario_file"),
        st.session_state.get("active_scenario"),
    )
