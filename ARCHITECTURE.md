# Negotiation Arena - Architecture and Application Logic

## 1) Overview

This is a multi-page Streamlit app that simulates a negotiation between LLM agents, evaluates each round with one judge model, and produces a final verdict with a second judge model.

High-level flow:

1. Scenario selection (`Home`)
2. Scenario object inspection (`Scenario Design`)
3. Global rules and model configuration (`Negotiation Rules`)
4. Round-by-round simulation + per-round evaluation (`Dialogue Simulation`)
5. Preliminary analytics on rounds (`Preliminary Results`)
6. Final verdict only after conversation termination (`Verdict`)


## 2) Module Structure

- `app.py`
  - Defines Streamlit page navigation.

- `scenario_state.py`
  - Manages the active scenario in `st.session_state`.
  - Loads JSON files from `scenarios/`.

- `negotiation_rules_state.py`
  - Manages global rules in `config/negotiation_rules.json`.
  - Normalizes values and applies safe defaults.

- `utils.py`
  - Builds each agent's system prompt (`build_system_prompt`).

- `core/director.py`
  - Runtime core of the negotiation.
  - Initializes agents.
  - Runs rounds.
  - Evaluates using judge models (`scope="round"` or `scope="final"`).
  - Applies termination logic.

- `pages/*.py`
  - UI and flow orchestration.


## 3) Core Data

### Scenario JSON

A scenario contains at least:

- `name`, `description`
- `agents` (list)
- `resources_to_negotiate` (dict)
- `metrics` (dict)

Fields used by agents in prompts:

- Per agent: `name`, `role`, `public_description`, `objective`, `resources`, `constraints`, `private_goals`
- Shared context: `description`, `resources_to_negotiate`

Fields used by judges:

- `metrics` (defines metric keys, metric types, enum values, utility direction)

### Global Rules (runtime governance)

Loaded from `config/negotiation_rules.json`:

- `max_rounds`
- `mode`
- `allow_partial_agreements`
- `require_unanimous_agreement`
- `agents_model`
- `judge_model` (round judge)
- `final_judge_model` (final judge)

Important note:

- In `Dialogue Simulation`, the active scenario is merged with active global rules, and `negotiation_rules` is overwritten with global rules.
- This means simulation behavior always follows the current global rules, not the original rules embedded in the scenario file.


## 4) Session State (Streamlit)

Main runtime keys:

- `active_scenario_file`, `active_scenario`
- `active_negotiation_rules`
- `director`, `director_scenario_file`, `director_scenario_signature`
- `history`, `round`
- `round_evaluations` (per-round evaluation records)
- `evaluations_df` (tabular view for analytics)
- `evaluation` (latest round evaluation)
- `final_evaluation`, `final_evaluation_meta` (final verdict + metadata)


## 5) End-to-End Flow

### 5.1 Home

1. Reads available files in `scenarios/`.
2. User selects a scenario.
3. Loads JSON and stores it as active scenario in session.

### 5.2 Scenario Design

1. Reads active scenario.
2. Renders JSON objects in columns for:
   - agents
   - negotiable resources
   - metrics

### 5.3 Negotiation Rules

1. Reads global rules.
2. Lets user edit runtime logic and model selection.
3. Saves to file and updates session state.

### 5.4 Dialogue Simulation

1. Builds `director_payload = scenario + global negotiation_rules`.
2. Creates or reuses `NegotiationDirector` based on scenario/rules signature.
3. For each round:
   - agents speak sequentially (`director.step`)
   - round judge evaluates (`scope="round"`)
   - evaluation is stored and registered
4. If negotiation is terminated, final judge runs (`scope="final"`), once per unique termination metadata.

### 5.5 Preliminary Results

1. Uses round-by-round data only (`evaluations_df` / `round_evaluations`).
2. Shows table, metric trends, utility trend, and per-round drill-down.

### 5.6 Verdict

1. Opens only if a valid `final_evaluation` exists for the active scenario.
2. Uses final judge output for outcome explanation.
3. Keeps round utility chart as historical context.


## 6) Director Logic

`NegotiationDirector` manages:

- agent runtime initialization (`AgentRuntime`) from `scenario["agents"]`
- dialogue history
- round counter
- termination state

### Round execution

- `step(input_message)`:
  - each agent receives the current message
  - generates output
  - output becomes input for next agent
  - increments `round` at the end

### Automatic stop

- `can_advance()` returns `False` if:
  - `is_terminated` is already `True`, or
  - `round >= max_rounds` (termination reason `stalled`)

### Evaluation-based termination

- `register_evaluation(evaluation)`:
  - extracts `agreement_status`
  - if `reached`: terminates
  - if `failed`: terminates
  - if max rounds reached: terminates as `stalled`


## 7) Judge Architecture

### 7.1 Round Judge

Where:

- `pages/dialogue_simulation.py`, inside `advance_round_and_evaluate()`

When:

- once per executed round

Model:

- `judge_model` from global rules

Input:

- full dialogue history (`history_as_text()`)
- `scenario.metrics`
- current negotiation status
- strict JSON output schema instructions

Output:

- JSON containing scenario metrics plus mandatory diagnostics fields

Persistence:

- appended to `round_evaluations`
- serialized into `evaluations_df`
- passed to `register_evaluation` to drive termination/governance

### 7.2 Final Judge

Where:

- `pages/dialogue_simulation.py`, function `_maybe_run_final_evaluation`

When:

- only when `director.is_terminated == True`

Model:

- `final_judge_model` from global rules

Input:

- same structured scheme as round judge, but with `scope="final"` and explicit instruction to evaluate the full trajectory and final outcome

Output:

- final JSON verdict saved in `st.session_state.final_evaluation`

Deduplication:

- uses `final_evaluation_meta` (`scenario_file`, `round`, `termination_reason`, `history_len`) to avoid duplicate final evaluations for the same terminal state

### 7.3 Practical separation

- Round judge:
  - iterative monitoring
  - powers round dashboards and preliminary analysis

- Final judge:
  - terminal synthesis
  - powers `Verdict` page
  - should not run while negotiation is still active


## 8) How Scenario Data and Judges Are Combined

Actual composition logic:

1. Scenario defines:
   - agent identities/objectives/resources
   - negotiable resources
   - evaluation metric schema

2. Global rules define:
   - runtime governance (`max_rounds`, unanimity, partial agreement policy)
   - model selection for agents, round judge, final judge

3. Director combines:
   - scenario domain content
   - global governance rules
   - live dialogue history

4. Judges consume:
   - scenario metrics + dialogue transcript
   - JSON/schema constraints
   - evaluation scope (`round` or `final`)

5. Analytics pages split responsibilities:
   - `Preliminary Results`: round-by-round dynamics
   - `Verdict`: final outcome via final judge


## 9) Operational Notes and Current Limits

- `utils.py` is now resilient to missing optional fields and falls back to safe defaults for prompt sections.
- `Verdict` intentionally blocks until final evaluation exists for the active scenario.
- Utility charts are computed from numeric round metrics; final narrative explanation comes from the final judge output.
