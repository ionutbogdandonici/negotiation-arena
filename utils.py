def build_system_prompt(agent_config, scenario_context):
    """
    Convert scenario dictionaries into a readable system prompt for agent turns.
    Improved version: more flexible and compatible with diverse scenarios.
    """
    # === AGENT IDENTITY ===
    name = str(agent_config.get("name", "Agent")).strip()
    role = str(agent_config.get("role", "Negotiator")).strip()
    public_description = str(agent_config.get("public_description", "")).strip()
    objective = str(agent_config.get("objective", "")).strip()

    prompt = f"""You are {name}, the {role}.

{public_description}

--- YOUR PRIVATE OBJECTIVE (do not reveal it completely to others) ---
{objective}
"""

    # === RESOURCES (FLEXIBLE) ===
    prompt += "\n--- RESOURCES YOU OWN ---\n"
    resources = agent_config.get("resources", {})
    
    if isinstance(resources, dict):
        # Check for explicit description first
        resource_description = str(resources.get("description", "")).strip()
        if resource_description:
            prompt += f"{resource_description}\n"
        
        # List owned items
        owns = resources.get("owns", [])
        if isinstance(owns, list) and owns:
            prompt += f"\nOwned assets: {', '.join(str(item) for item in owns)}\n"
        
        # Add any other resource attributes dynamically
        excluded_keys = {"description", "owns"}
        for key, value in resources.items():
            if key not in excluded_keys:
                label = str(key).replace("_", " ").strip().title()
                prompt += f"- {label}: {value}\n"
        
        # If no resources at all
        if not resource_description and not owns and len(resources) <= 2:
            prompt += "No explicit resource description provided.\n"
    else:
        prompt += "No explicit resource description provided.\n"

    # === CONSTRAINTS (FLEXIBLE) ===
    prompt += "\n--- CONSTRAINTS ---\n"
    constraints = agent_config.get("constraints", [])
    
    if isinstance(constraints, list) and constraints:
        for constraint in constraints:
            prompt += f"- {constraint}\n"
    else:
        prompt += "- None specified.\n"

    # === PRIVATE GOALS (FULLY DYNAMIC) ===
    prompt += "\n--- PRIVATE GOALS ---\n"
    private_goals = agent_config.get("private_goals", {})
    
    if isinstance(private_goals, dict) and private_goals:
        # Define known goal types with custom formatting
        goal_formatters = {
            "min_equity_percent": lambda v: f"- Minimum acceptable equity: {v}%",
            "preferred_equity_percent": lambda v: f"- Preferred equity: {v}%",
            "max_equity_percent": lambda v: f"- Maximum equity target: {v}%",
            "must_control_areas": lambda v: f"- Must control areas: {', '.join(str(area) for area in v)}" if isinstance(v, list) else f"- Must control areas: {v}",
            "preferred_control_areas": lambda v: f"- Preferred control areas: {', '.join(str(area) for area in v)}" if isinstance(v, list) else f"- Preferred control areas: {v}",
            "budget_needed": lambda v: f"- Budget needed: {_format_currency(v, scenario_context)}",
            "min_budget": lambda v: f"- Minimum budget: {_format_currency(v, scenario_context)}",
            "max_budget": lambda v: f"- Maximum budget: {_format_currency(v, scenario_context)}",
            "investment_to_protect": lambda v: f"- Investment to protect: {_format_currency(v, scenario_context)}",
        }
        
        # Format known goals
        for key, formatter in goal_formatters.items():
            if key in private_goals:
                value = private_goals[key]
                if value is not None:
                    prompt += f"{formatter(value)}\n"
        
        # Format any additional custom goals
        for key, value in private_goals.items():
            if key not in goal_formatters and value is not None:
                label = str(key).replace("_", " ").strip().title()
                if isinstance(value, (list, tuple)):
                    prompt += f"- {label}: {', '.join(str(item) for item in value)}\n"
                else:
                    prompt += f"- {label}: {value}\n"
    else:
        prompt += "- None specified.\n"

    # === NEGOTIATION CONTEXT ===
    scenario_description = str(scenario_context.get("description", "")).strip()
    if not scenario_description:
        scenario_description = "No scenario description provided."

    prompt += f"""

====================================================
NEGOTIATION CONTEXT
====================================================

{scenario_description}

RESOURCES TO NEGOTIATE:
"""

    # === NEGOTIABLE RESOURCES (FLEXIBLE) ===
    negotiable_resources = scenario_context.get("resources_to_negotiate", {})
    if isinstance(negotiable_resources, dict) and negotiable_resources:
        for resource_name, resource_data in negotiable_resources.items():
            if isinstance(resource_data, dict):
                description = str(resource_data.get("description", "")).strip()
                if description:
                    prompt += f"- {description}\n"
                else:
                    # Build description from available fields
                    parts = [resource_name]
                    if "total" in resource_data:
                        total = resource_data["total"]
                        unit = resource_data.get("unit", "")
                        currency = resource_data.get("currency", "")
                        if currency:
                            parts.append(f"Total: {currency} {total}")
                        elif unit:
                            parts.append(f"Total: {total} {unit}")
                        else:
                            parts.append(f"Total: {total}")
                    
                    if "options" in resource_data:
                        options = resource_data["options"]
                        if isinstance(options, list):
                            parts.append(f"Options: {', '.join(str(opt) for opt in options)}")
                    
                    if "areas" in resource_data:
                        areas = resource_data["areas"]
                        if isinstance(areas, list):
                            parts.append(f"Areas: {', '.join(str(area) for area in areas)}")
                    
                    prompt += f"- {': '.join(parts)}\n"
            else:
                prompt += f"- {resource_name}: {resource_data}\n"
    else:
        prompt += "- Not specified.\n"

    # === NEGOTIATION RULES ===
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
            "- Prioritize your own strategic outcomes while still seeking a valid agreement.",
            "- Make limited concessions and protect your minimum acceptable outcomes.",
        ],
        "mixed": [
            "- Balance your own interests and joint outcomes.",
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

    # === INSTRUCTIONS (DYNAMIC) ===
    prompt += """

INSTRUCTIONS:
1. Follow the negotiation mode policy above and maximize your objective within that policy
2. Be strategic: do not immediately reveal your minimum acceptable outcomes
3. When making a proposal, use this format:

   PROPOSAL:
"""

    # Generate proposal format dynamically based on resources
    if isinstance(negotiable_resources, dict):
        for resource_name, resource_data in negotiable_resources.items():
            if isinstance(resource_data, dict):
                resource_label = resource_name.replace("_", " ").title()
                
                # Handle different resource types
                if resource_data.get("total") and resource_data.get("divisible", True):
                    prompt += f"   - {resource_label}: X% for me, Y% for other party\n"
                elif "categories" in resource_data:
                    categories = resource_data["categories"]
                    if isinstance(categories, dict):
                        cat_names = ", ".join(categories.keys())
                        prompt += f"   - {resource_label}: Specify amounts for {cat_names}\n"
                elif "areas" in resource_data:
                    prompt += f"   - {resource_label}: I control [areas], other party controls [areas]\n"
                elif "options" in resource_data:
                    options = resource_data["options"]
                    if isinstance(options, list):
                        opt_str = "/".join(str(opt) for opt in options[:3])
                        prompt += f"   - {resource_label}: [{opt_str}]\n"
                else:
                    prompt += f"   - {resource_label}: [your proposal]\n"

    prompt += """
4. Respect agreement constraints from NEGOTIATION RULES:
"""
    if allow_partial:
        prompt += "   - You may make partial proposals on one resource at a time.\n"
    else:
        prompt += "   - Do not propose or accept partial agreements; only complete packages are valid.\n"

    if require_unanimous:
        prompt += "   - Do not declare agreement reached unless all parties explicitly confirm it.\n"
    else:
        prompt += "   - Agreement can be considered reached without explicit unanimous confirmation.\n"

    prompt += """
5. Respond naturally and professionally
6. Always respond in English.
7. Your reply should be approximately 10% of the length of a typical full explanation, prioritizing conclusions, concrete proposals, and trade-offs.


Now begin the negotiation.
"""

    return prompt


def _format_currency(value, scenario_context):
    """Helper to format currency values based on scenario context."""
    # Try to detect currency from resources_to_negotiate
    resources = scenario_context.get("resources_to_negotiate", {})
    
    for resource_data in resources.values():
        if isinstance(resource_data, dict) and "currency" in resource_data:
            currency = resource_data["currency"]
            return f"{currency} {value:,}"
    
    # Default formatting
    if isinstance(value, (int, float)):
        return f"EUR {value:,}"
    return str(value)
