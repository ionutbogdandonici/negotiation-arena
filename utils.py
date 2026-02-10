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

    prompt += """

INSTRUCTIONS:
1. Negotiate to maximize YOUR utility (use the weights above)
2. Be strategic: do not immediately reveal your minimum acceptable outcomes
3. When making a proposal, use this format:

   PROPOSAL:
   - Equity: X% for me, Y% for the other party
   - Budget: EUR A for salaries, EUR B for marketing, EUR C for development
   - Decision rights: I control [areas], the other party controls [areas]
   - Vesting: [chosen option]

4. You may also make partial proposals on one resource at a time
5. Respond naturally and professionally
6. Always respond in English.
7. Your reply should be approximately 10% of the length of a typical full explanation, prioritizing - conclusions, concrete proposals, and trade-offs.


Now begin the negotiation.
"""

    return prompt
