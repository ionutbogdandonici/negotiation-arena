# Negotiation Arena

Streamlit app to simulate multi-round negotiations between LLM agents, evaluate each round, and aggregate cross-run results.

## Features
- Scenario-driven setup from JSON files in `scenarios/`.
- Multi-agent negotiation loop with configurable mode: `cooperative`, `competitive`, `mixed`.
- Dual-judge evaluation:
  - `Round Judge` for incremental round annotations.
  - `Final Judge` for terminal verdict and diagnostics.
- Analysis pages for per-run metrics and global aggregates.
- Dedicated `Prompts` page showing the source code used to build:
  - Agent system prompt
  - Round Judge system prompt
  - Final Judge system prompt
- Global Results scenario filter with options:
  - `Resource Division`
  - `Salary Negotiation`
  - `All`

## Project Structure
```text
.
|- app.py
|- core/
|  `- director.py
|- pages/
|  |- home.py
|  |- scenario_design.py
|  |- agent_configuration.py
|  |- dialogue_simulation.py
|  |- analysis_and_metrics.py
|  |- verdict.py
|  |- global_results.py
|  `- prompts.py
|- scenarios/
|- output/
|  `- global_results.csv
|- scenario_state.py
|- run_results_store.py
`- utils.py
```

## Requirements
- Python 3.10+
- Valid API credentials configured in Streamlit secrets

## Run
```bash
streamlit run app.py
```

## Typical Workflow
1. Open `Home` and select a scenario.
2. Configure models/rules in `Negotiation Rules`.
3. Run rounds in `Dialogue Simulation`.
4. Inspect round metrics in `Preliminary Results`.
5. Inspect final diagnostics in `Verdict`.
6. Compare runs in `Global Results`.
7. Inspect prompt builders in `Prompts`.

## Output Policy
- Only `output/global_results.csv` is versioned.
- All other files under `output/` are ignored.
## Notes
- Do not commit secrets (`.streamlit/secrets.toml`, API keys).
- Add or edit scenarios in `scenarios/` as JSON files.
