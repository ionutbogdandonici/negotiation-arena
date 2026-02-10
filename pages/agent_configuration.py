import streamlit as st

st.title("Agent Configuration")
st.markdown("""
Instantiate two or more LLM agents with distinct "personas" or objectives. Examples:

 - Agent A seeks maximum profit
 - Agent B seeks values fairness
 - Agent C minimizes risk.
 
Optionally, include an adjudicator model (or a human evaluator) to judge outcomes.
""")

agent_a_tab, agent_b_tab, agent_adjudicator_tab = st.tabs(["Agent A", "Agent B", "Adjudicator Agent"])