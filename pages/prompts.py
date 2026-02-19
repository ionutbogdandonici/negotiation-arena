import inspect
import textwrap

import streamlit as st

from core.director import NegotiationDirector
from utils import build_system_prompt


def _get_source_code(obj) -> str:
    try:
        return textwrap.dedent(inspect.getsource(obj))
    except (OSError, TypeError):
        return "Source code not available."


st.title("Prompts")
st.write(
    "This page shows the code used to build the agent system prompt and the two judge system prompts."
)

with st.expander("Agent System Prompt Builder (`utils.build_system_prompt`)", expanded=True):
    st.code(_get_source_code(build_system_prompt), language="python")

with st.expander(
    "Round Judge System Prompt (`NegotiationDirector._build_round_judge_prompt`)",
    expanded=False,
):
    st.code(_get_source_code(NegotiationDirector._build_round_judge_prompt), language="python")

with st.expander(
    "Final Judge System Prompt (`NegotiationDirector._build_final_judge_prompt`)",
    expanded=False,
):
    st.code(_get_source_code(NegotiationDirector._build_final_judge_prompt), language="python")
