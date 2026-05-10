"""
Prompt templates for LLM-based test case generation.

Each template embeds the exact JSON schema in the prompt so the model
returns structured output that can be parsed and validated deterministically.
"""

# ── Output JSON schema (embedded into every prompt) ───────────────────────────

OUTPUT_SCHEMA = """
{
  "test_cases": [
    {
      "test_type": "Positive | Negative | Edge | Boundary | Security | Performance | Concurrency | Failure | Integration",
      "title": "string — must contain 'when' and 'expecting', e.g. 'User logs in when valid credentials provided, expecting authenticated session'",
      "preconditions": ["string", "..."],
      "steps": [
        {"step_number": 1, "action": "string", "expected_intermediate": "string (optional)"}
      ],
      "expected_result": "string",
      "test_data": {
        "inputs": {"key": "value"},
        "expected_outputs": {"key": "value"}
      },
      "priority": "High | Medium | Low",
      "automation_feasibility": "High | Medium | Low"
    }
  ],
  "coverage_notes": "string — brief explanation of coverage approach and any gaps"
}
"""

# ── System instruction (constant across all calls) ────────────────────────────

SYSTEM_INSTRUCTION = """You are an expert QA engineer and test case generator.

Your task is to generate comprehensive, structured test cases for software requirements.

Rules:
1. Return ONLY valid JSON matching the schema below. No explanation, no markdown, no preamble.
2. Every title MUST contain the words "when" and "expecting".
3. Cover at minimum: one Positive, one Negative test case per requirement.
4. Add Edge, Boundary, Security, Performance, or Concurrency cases only when the requirement explicitly implies them.
5. Test steps must be concrete and actionable — no placeholders like "do the thing".
6. Do not invent scenarios not implied by the requirement.
7. test_data.inputs must contain realistic sample values, not empty objects.

Output schema:
""" + OUTPUT_SCHEMA

# ── Per-requirement prompt template ───────────────────────────────────────────

def build_generation_prompt(
    requirement_text: str,
    requirement_type: str,
    classification: list,
    actor: str = "",
    action: str = "",
    conditions: list = None,
    expected_outcome: str = "",
    document_type: str = "plain_text",
) -> str:
    """
    Build the user-turn prompt for test case generation.

    All contextual fields from the normalization layer are included so the
    model has structured signal in addition to the raw requirement text.
    """
    conditions = conditions or []
    condition_str = "; ".join(conditions) if conditions else "none specified"

    return f"""Generate test cases for the following software requirement.

REQUIREMENT TEXT:
{requirement_text}

STRUCTURED ANALYSIS:
- Document Type: {document_type}
- Requirement Type: {requirement_type}
- Classification: {', '.join(classification) if classification else 'Functional'}
- Actor: {actor or 'not specified'}
- Action: {action or 'not specified'}
- Pre-conditions: {condition_str}
- Expected Outcome: {expected_outcome or 'not specified'}

Generate all applicable test cases. Return ONLY the JSON object — no explanation."""


def build_batch_prompt(requirements: list) -> str:
    """
    Build a prompt for generating test cases for multiple requirements at once.
    Each element of `requirements` is a dict with the same keys as build_generation_prompt.
    """
    req_blocks = []
    for i, r in enumerate(requirements, 1):
        req_blocks.append(
            f"REQUIREMENT {i}:\n"
            f"  Text: {r.get('text', '')}\n"
            f"  Type: {r.get('requirement_type', 'Functional')}\n"
            f"  Actor: {r.get('actor', '')}\n"
            f"  Action: {r.get('action', '')}\n"
            f"  Outcome: {r.get('expected_outcome', '')}"
        )

    return (
        "Generate test cases for ALL of the following requirements.\n"
        "Return a JSON object where each key is the requirement number "
        "(e.g. '1', '2') and the value matches the schema above.\n\n"
        + "\n\n".join(req_blocks)
        + "\n\nReturn ONLY the JSON object."
    )
