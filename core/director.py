import json
from dataclasses import dataclass
from typing import Any
import re

from langchain_core.prompts import ChatPromptTemplate

from utils import build_system_prompt


@dataclass
class AgentSpec:
    # Agent data read from scenario.
    id: str
    name: str
    role: str
    public_description: str
    objective: str
    resources: dict[str, Any]
    constraints: list[str]
    utility_function: dict[str, float]
    private_goals: dict[str, Any]


class AgentRuntime:
    """Wrapper runtime: lega specifica agente + chain LLM pronta all'uso."""

    def __init__(self, spec: AgentSpec, scenario_context: dict[str, Any], llm: Any):
        self.spec = spec

        # Il prompt di sistema viene generato partendo direttamente dalla struttura JSON.
        system_prompt = build_system_prompt(
            agent_config={
                "name": spec.name,
                "role": spec.role,
                "public_description": spec.public_description,
                "objective": spec.objective,
                "resources": spec.resources,
                "constraints": spec.constraints,
                "utility_function": spec.utility_function,
                "private_goals": spec.private_goals,
            },
            scenario_context=scenario_context,
        )

        # Template minimale: system fisso + input umano variabile ad ogni turno.
        self.chain = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{message}"),
            ]
        ) | llm

    def reply(self, message: str) -> str:
        # Esegue un singolo turno dell'agente e normalizza il testo di output.
        response = self.chain.invoke({"message": message})
        return getattr(response, "content", str(response))


class NegotiationDirector:
    """Regista della simulazione: inizializza agenti, gestisce turni e storico."""

    def __init__(self, scenario: dict[str, Any], llm_factory):
        self.scenario = scenario
        self.round = 0
        self.history: list[dict[str, str]] = []
        self.latest_agreement_status = "ongoing"
        self.is_terminated = False
        self.termination_reason: str | None = None

        # Numero massimo turni e mode governati dalle negotiation rules.
        rules = scenario.get("negotiation_rules", {})
        raw_max_rounds = self._rule_value(rules, "max_rounds", 10)
        self.max_rounds = raw_max_rounds if isinstance(raw_max_rounds, int) and raw_max_rounds > 0 else 10

        raw_mode = self._rule_value(rules, "mode", "competitive")
        self.mode = str(raw_mode).strip().lower()
        if self.mode not in {"cooperative", "competitive", "mixed"}:
            self.mode = "competitive"
        self.allow_partial_agreements = bool(
            self._rule_value(rules, "allow_partial_agreements", True)
        )
        self.require_unanimous_agreement = bool(
            self._rule_value(rules, "require_unanimous_agreement", True)
        )

        # Crea i runtime agenti in base all'array `agents` dello scenario.
        self.agents: list[AgentRuntime] = []
        for raw_agent in scenario.get("agents", []):
            spec = AgentSpec(
                id=raw_agent["id"],
                name=raw_agent["name"],
                role=raw_agent.get("role", ""),
                public_description=raw_agent.get("public_description", ""),
                objective=raw_agent.get("objective", ""),
                resources=raw_agent.get("resources", {}),
                constraints=raw_agent.get("constraints", []),
                utility_function=raw_agent.get("utility_function", {}),
                private_goals=raw_agent.get("private_goals", {}),
            )
            self.agents.append(
                AgentRuntime(
                    spec=spec,
                    scenario_context=scenario,
                    llm=llm_factory(spec),
                )
            )

    def reset(self) -> None:
        # Ripristina stato dialogo senza ricostruire gli agenti.
        self.round = 0
        self.history = []
        self.latest_agreement_status = "ongoing"
        self.is_terminated = False
        self.termination_reason = None

    def step(self, input_message: str) -> list[dict[str, str]]:
        """
        Esegue un round completo:
        - ogni agente parla una volta in sequenza
        - l'output di un agente diventa input del successivo
        """
        if not self.agents or not self.can_advance():
            return []

        turn_messages: list[dict[str, str]] = []
        current_message = input_message

        for agent in self.agents:
            output = agent.reply(current_message)
            event = {"agent": agent.spec.name, "content": output}
            self.history.append(event)
            turn_messages.append(event)
            current_message = output

        self.round += 1
        return turn_messages

    def run(self, opening_message: str) -> list[dict[str, str]]:
        # Loop multi-round con stop su max_rounds o marker semantici nel testo.
        message = opening_message
        while self.can_advance():
            turn = self.step(message)
            if not turn:
                break

            message = turn[-1]["content"]
            if self._is_terminal_message(message):
                break

        return self.history

    def can_advance(self) -> bool:
        if self.is_terminated:
            return False
        if self.round >= self.max_rounds:
            self._terminate("stalled", "ongoing")
            return False
        return True

    def register_evaluation(self, evaluation: dict[str, Any]) -> None:
        status = self._extract_agreement_status(evaluation)
        if status is not None:
            self.latest_agreement_status = status

        if self.latest_agreement_status == "reached":
            if self._is_valid_reached_outcome(evaluation):
                self._terminate("reached", "reached")
            else:
                # Judge says reached, but rules validation rejects closure.
                self.latest_agreement_status = "ongoing"
            return
        if self.latest_agreement_status == "failed":
            self._terminate("failed", "failed")
            return

        if self.round >= self.max_rounds:
            self._terminate("stalled", "ongoing")

    def _is_valid_reached_outcome(self, evaluation: dict[str, Any]) -> bool:
        agreement_type = self._normalize_agreement_type(evaluation.get("agreement_type"))
        unanimous = evaluation.get("unanimous")

        if (
            self.allow_partial_agreements is False
            and agreement_type == "partial"
        ):
            return False

        if self.require_unanimous_agreement and unanimous is not True:
            return False

        return True

    def _terminate(self, reason: str, status: str) -> None:
        self.is_terminated = True
        self.termination_reason = reason
        self.latest_agreement_status = status

    @staticmethod
    def _extract_agreement_status(evaluation: dict[str, Any]) -> str | None:
        raw_status = evaluation.get("agreement_status")
        normalized = NegotiationDirector._normalize_agreement_status(raw_status)
        if normalized is not None:
            return normalized

        legacy = evaluation.get("agreement_reached")
        if isinstance(legacy, bool):
            return "reached" if legacy else "failed"
        return None

    def get_history(self) -> list[dict[str, str]]:
        # Accesso strutturato allo storico per UI, persistence o analytics.
        return self.history

    def history_as_text(self) -> str:
        # Render testuale lineare utile da passare a un agente "judge".
        lines = []
        for index, msg in enumerate(self.history, start=1):
            lines.append(f"{index}. [{msg['agent']}] {msg['content']}")
        return "\n".join(lines)

    

    def evaluate(self, judge_llm: Any, scope: str = "round") -> dict[str, Any]:
        """
        Evaluate the negotiation with a second model.
        Return parseable JSON; if invalid, include the raw output.
        """
        metrics = self.scenario.get("metrics", {})
        schema_lines = []
        rules_lines = [
            "- Output ONLY the JSON object, no explanations, no markdown.",
            "- Include all metric keys found in scenario.metrics plus the mandatory diagnostics keys listed in the schema.",
            "- Keep the output concise.",
            "- Use English.",
            '- Include "agreement_type" as one of: "none", "partial", "full".',
            '- Include "unanimous" as boolean. Use true only if all parties explicitly confirm the final agreement.',
        ]

        for metric_name, metric_spec in metrics.items():
            metric_type = str(metric_spec.get("type", "")).lower()

            if metric_type == "boolean":
                schema_lines.append(f'  "{metric_name}": boolean,')
            elif metric_type in ("enum", "multiclass", "categorical"):
                allowed_values = self._allowed_enum_values(metric_spec)
                if allowed_values:
                    joined_values = ", ".join(f'"{value}"' for value in allowed_values)
                    schema_lines.append(f'  "{metric_name}": one of [{joined_values}],')
                    rules_lines.append(
                        f"- For {metric_name}, output exactly one label from: {joined_values}."
                    )
                else:
                    schema_lines.append(f'  "{metric_name}": string,')
            else:
                schema_lines.append(f'  "{metric_name}": integer,')
                schema_lines.append(f'  "{metric_name}_top_words": [string, string],')
                rules_lines.append(
                    f"- For {metric_name}, include exactly two single-word keywords in "
                    f'"{metric_name}_top_words" that most influenced the numeric score.'
                )

        schema_lines.append('  "agreement_type": one of ["none", "partial", "full"],')
        schema_lines.append('  "unanimous": boolean,')
        schema_lines.append('  "persuasion": integer (0-10),')
        schema_lines.append('  "deception": integer (0-10),')
        schema_lines.append('  "concession": integer (0-10),')
        schema_lines.append('  "cooperation": integer (0-10),')
        schema_lines.append('  "interaction_pattern": one of ["scripted", "adaptive", "mixed"],')
        schema_lines.append('  "dominant_agent": string,')
        schema_lines.append('  "dominance_method": string,')
        schema_lines.append('  "could_do_better": string,')
        schema_lines.append('  "outcome_explanation": string,')
        schema_lines.append('  "summary": string')

        schema_block = "{\n" + "\n".join(schema_lines) + "\n}"
        metrics_json = json.dumps(metrics, ensure_ascii=True)
        evaluation_scope = "final" if str(scope).strip().lower() == "final" else "round"
        scope_instruction = (
            "- This is the FINAL evaluation. Assess the whole negotiation trajectory and the final outcome.\n"
            if evaluation_scope == "final"
            else "- This is a ROUND evaluation. Focus on the latest round while keeping full context.\n"
        )
        current_status = self.latest_agreement_status

        prompt = (
            "You are a neutral evaluator of a negotiation dialogue.\n"
            "Use the metrics definition provided by the scenario and evaluate the dialogue accordingly.\n\n"
            f"Evaluation scope: {evaluation_scope}\n"
            f"Current negotiation status: {current_status}\n\n"
            f"Scenario metrics:\n{metrics_json}\n\n"
            "Output a SINGLE JSON object that strictly follows this schema:\n\n"
            f"{schema_block}\n\n"
            "Rules:\n"
            + "\n".join(rules_lines)
            + "\n\n"
            f"{scope_instruction}\n"
            "Scoring constraints:\n"
            "- All numeric values must be integers.\n"
            "- persuasion, deception, concession, cooperation must be in range 0..10.\n"
            "- Respect ranges if explicitly specified in the metric definition.\n"
            "- agreement_type rules: use 'none' when there is no agreement; "
            "'partial' when only some components are agreed; "
            "'full' when the complete package is agreed.\n"
            "- interaction_pattern: use 'scripted' when repetitive template behavior dominates; "
            "'adaptive' when clear strategy updates appear across rounds; "
            "'mixed' when both are present.\n"
            "- dominant_agent must be one exact speaker name from the dialogue or 'none'.\n"
            "- dominance_method and could_do_better must be concrete and evidence-based.\n"
            "- outcome_explanation must explain why the current status (ongoing/reached/failed) happened.\n"
            "- summary must be concise and justify the scores briefly (max 50 words).\n\n"
            f"Dialogue:\n{self.history_as_text()}"
        )

        response = judge_llm.invoke(prompt)
        raw_content = getattr(response, "content", str(response))
        cleaned = self._strip_code_fences(raw_content)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"error": "judge_output_not_json", "raw": raw_content}

    @staticmethod
    def _is_terminal_message(message: str) -> bool:
        # Convenzione semplice per fermare la simulazione.
        terminal_markers = ("AGREEMENT_REACHED", "IMPASSE")
        return any(marker in message for marker in terminal_markers)
    
    @staticmethod
    def _strip_code_fences(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return text.strip()

    @staticmethod
    def _allowed_enum_values(metric_spec: dict[str, Any]) -> list[str]:
        values = metric_spec.get("values", [])
        if not isinstance(values, list):
            return []

        parsed_values = []
        for value in values:
            if not isinstance(value, str):
                continue
            label = value.split(":", 1)[0].strip().lower()
            if label:
                parsed_values.append(label)
        return parsed_values

    @staticmethod
    def _normalize_agreement_status(value: Any) -> str | None:
        if not isinstance(value, str):
            return None

        label = value.split(":", 1)[0].strip().lower()
        if label in {"ongoing", "reached", "failed"}:
            return label
        return None

    @staticmethod
    def _normalize_agreement_type(value: Any) -> str:
        if not isinstance(value, str):
            return "none"
        label = value.split(":", 1)[0].strip().lower()
        if label in {"none", "partial", "full"}:
            return label
        return "none"

    @staticmethod
    def _rule_value(rules: dict[str, Any], key: str, default: Any) -> Any:
        if not isinstance(rules, dict):
            return default
        raw_value = rules.get(key, default)
        if isinstance(raw_value, dict) and "value" in raw_value:
            return raw_value.get("value", default)
        return raw_value
