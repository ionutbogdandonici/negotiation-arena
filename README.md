# Negotiation Arena

Streamlit app to simulate multi-round negotiations between LLM agents and track judge evaluations over time.

## Features
- Scenario-driven negotiation setup from JSON files (`scenarios/`).
- Turn-by-turn conversation advance with judge evaluation at each round.
- Metrics tracking across rounds (fairness, cooperativeness, manipulativeness, conversation quality, ambiguity).
- Analysis dashboard with rounds-to-agreement and per-round metric deltas.

## Project Structure
```text
.
├── app.py
├── core/
│   └── director.py
├── pages/
│   ├── home.py
│   ├── scenario_design.py
│   ├── agent_configuration.py
│   ├── dialogue_simulation.py
│   └── analysis_and_metrics.py
├── scenarios/
│   └── resource_division.json
├── scenario_state.py
├── utils.py
└── requirements.txt
```

## Requirements
- Python 3.10+
- Anthropic API key

## Setup
1. Create and activate a virtual environment.
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Set environment variable:
```bash
# PowerShell
$env:ANTHROPIC_API_KEY="your_key_here"
```

## Run
```bash
streamlit run app.py
```

## How To Use
1. Open `Home` and select a scenario.
2. Go to `Dialogue Simulation`.
3. Click `Advance Conversation` to run one round at a time.
4. Open `Analysis and Metrics` to inspect time-series and per-round judge reports.

## Notes
- Never commit secrets (`ANTHROPIC_API_KEY`, `.streamlit/secrets.toml`).
- Add new scenarios as JSON files in `scenarios/`.
