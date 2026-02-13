def build_system_prompt(agent_config, scenario_context):
    """
    Convert the input dictionaries into a readable system prompt for the LLM.
    """

    prompt = f"""You are {agent_config['name']}, the {agent_config['role']}.

{agent_config['public_description']}

--- YOUR PRIVATE OBJECTIVE (do not reveal it completely to others) ---
{agent_config['objective']}

--- RESOURCES YOU OWN ---
{agent_config['resources']['description']}

--- CONSTRAINTS ---
"""

    # Add constraints.
    for constraint in agent_config["constraints"]:
        prompt += f"- {constraint}\n"

    prompt += """
--- HOW MUCH THINGS MATTER TO YOU (Utility Function) ---
"""

    # Add utility weights.
    for item, weight in agent_config["utility_function"].items():
        prompt += f"- {item}: {int(weight * 100)}%\n"

    prompt += f"""
--- NUMERIC GOALS (use these to evaluate proposals) ---
- Minimum acceptable equity: {agent_config['private_goals']['min_equity_percent']}%
- Preferred equity: {agent_config['private_goals']['preferred_equity_percent']}%
"""

    if "must_control_areas" in agent_config["private_goals"]:
        areas = ", ".join(agent_config["private_goals"]["must_control_areas"])
        prompt += f"- You must keep control of: {areas}\n"

    if "budget_needed" in agent_config["private_goals"]:
        prompt += f"- Budget you need: EUR {agent_config['private_goals']['budget_needed']}\n"

    prompt += f"""

====================================================
NEGOTIATION CONTEXT
====================================================

{scenario_context['description']}

RESOURCES TO NEGOTIATE:
"""

    # Add negotiable resources.
    for _, resource_data in scenario_context["resources_to_negotiate"].items():
        prompt += f"- {resource_data['description']}\n"

    rules = scenario_context.get("negotiation_rules", {})

    def _rule_value(key, default):
        if not isinstance(rules, dict):
            return default
        value = rules.get(key, default)
        if isinstance(value, dict) and "value" in value:
            return value.get("value", default)
        return value

    mode = str(_rule_value("mode", "competitive")).strip().lower()
    if mode not in {"cooperative", "competitive", "mixed"}:
        mode = "competitive"
    allow_partial = bool(_rule_value("allow_partial_agreements", True))
    require_unanimous = bool(_rule_value("require_unanimous_agreement", True))

    mode_policy_lines = {
        "cooperative": [
            "- Prioritize mutually beneficial agreements over maximizing only your side.",
            "- Make constructive concessions when they unlock progress.",
        ],
        "competitive": [
            "- Prioritize maximizing your own utility while still seeking a valid agreement.",
            "- Make limited concessions and protect your minimum acceptable outcomes.",
        ],
        "mixed": [
            "- Balance individual utility and joint outcomes.",
            "- Start collaborative, then become firmer if reciprocal progress is absent.",
        ],
    }

    prompt += f"""

====================================================
NEGOTIATION RULES
====================================================

- Mode: {mode}
- Allow partial agreements: {allow_partial}
- Require unanimous agreement: {require_unanimous}
"""
    for line in mode_policy_lines[mode]:
        prompt += f"{line}\n"

    prompt += """

INSTRUCTIONS:
1. Follow the negotiation mode policy above and maximize your utility within that policy
2. Be strategic: do not immediately reveal your minimum acceptable outcomes
3. When making a proposal, use this format:

   PROPOSAL:
   - Equity: X% for me, Y% for the other party
   - Budget: EUR A for salaries, EUR B for marketing, EUR C for development
   - Decision rights: I control [areas], the other party controls [areas]
   - Vesting: [chosen option]

4. Respect agreement constraints from NEGOTIATION RULES:
"""
    if allow_partial:
        prompt += "- You may make partial proposals on one resource at a time.\n"
    else:
        prompt += "- Do not propose or accept partial agreements; only complete packages are valid.\n"

    if require_unanimous:
        prompt += "- Do not declare agreement reached unless all parties explicitly confirm it.\n"
    else:
        prompt += "- Agreement can be considered reached without explicit unanimous confirmation.\n"

    prompt += """
5. Respond naturally and professionally
6. Always respond in English.
7. Your reply should be approximately 10% of the length of a typical full explanation, prioritizing - conclusions, concrete proposals, and trade-offs.


Now begin the negotiation.
"""

    return prompt
