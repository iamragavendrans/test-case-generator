"""Test case generation service: rule-based generator."""
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class GenerationConfig:
    determinism_seed: int = 42
    max_test_cases_per_req: int = 6
    include_boundary: bool = True
    include_security: bool = True


@dataclass
class GeneratedTestCase:
    requirement_id: str
    test_type: str
    title: str
    preconditions: List[str]
    steps: List[Dict[str, Any]]
    test_data: Dict[str, Any]
    expected_result: str
    template_id: str
    rules_applied: List[str]


def _tc_title(action: str, actor: str, test_type: str, outcome: str) -> str:
    action_short = action[:60] if action else "perform action"
    if test_type == "Positive":
        return f"Verify {actor} can {action_short} when valid input provided, expecting {outcome}"
    if test_type == "Negative":
        return f"Verify error when {actor} attempts {action_short} with invalid input, expecting rejection"
    if test_type == "Boundary":
        return f"Verify boundary conditions when {actor} performs {action_short}, expecting correct boundary handling"
    if test_type == "Security":
        return f"Verify unauthorized {actor} cannot {action_short} when lacking permissions, expecting access denied"
    if test_type == "Performance":
        return f"Verify {actor} {action_short} completes within SLA threshold, expecting timely response"
    if test_type == "Concurrency":
        return f"Verify concurrent {actor} requests for {action_short}, expecting consistent state"
    if test_type == "Edge":
        return f"Verify edge case when {actor} {action_short} with empty or null input, expecting graceful handling"
    return f"Verify {actor} {action_short} when executed, expecting {outcome}"


def _positive_steps(actor: str, action: str, conditions: List[str]) -> List[Dict]:
    steps = [{"step_number": 1, "action": f"Set up test environment and preconditions", "expected_intermediate": "Environment ready"}]
    for i, cond in enumerate(conditions, start=2):
        steps.append({"step_number": i, "action": f"Ensure condition: {cond}", "expected_intermediate": "Condition satisfied"})
    steps.append({"step_number": len(steps) + 1, "action": f"As {actor}, perform: {action}", "expected_intermediate": None})
    steps.append({"step_number": len(steps) + 1, "action": "Verify the system response and state", "expected_intermediate": None})
    return steps


def _negative_steps(actor: str, action: str) -> List[Dict]:
    return [
        {"step_number": 1, "action": "Set up test environment", "expected_intermediate": "Ready"},
        {"step_number": 2, "action": f"As {actor}, attempt: {action} with invalid or missing input", "expected_intermediate": None},
        {"step_number": 3, "action": "Capture the system response", "expected_intermediate": None},
        {"step_number": 4, "action": "Verify error message and system state unchanged", "expected_intermediate": None},
    ]


def _boundary_steps(actor: str, action: str) -> List[Dict]:
    return [
        {"step_number": 1, "action": "Identify boundary values (min, max, just-outside)", "expected_intermediate": None},
        {"step_number": 2, "action": f"As {actor}, execute: {action} with minimum boundary value", "expected_intermediate": "Accepted"},
        {"step_number": 3, "action": f"As {actor}, execute: {action} with maximum boundary value", "expected_intermediate": "Accepted"},
        {"step_number": 4, "action": f"As {actor}, execute: {action} with value exceeding maximum", "expected_intermediate": "Rejected"},
    ]


_PRIORITY_MAP = {
    "High": {"POS": "P1", "NEG": "P1", "SEC": "P1", "PER": "P1", "CON": "P1", "BND": "P2", "EDG": "P2"},
    "Medium": {"POS": "P2", "NEG": "P2", "SEC": "P1", "PER": "P2", "CON": "P2", "BND": "P3", "EDG": "P3"},
    "Low": {"POS": "P3", "NEG": "P3", "SEC": "P2", "PER": "P3", "CON": "P3", "BND": "P3", "EDG": "P3"},
}


class TestCaseGenerationService:
    def __init__(self, config: Optional[GenerationConfig] = None):
        self.config = config or GenerationConfig()

    def generate(
        self,
        normalized_req: Dict[str, Any],
        classification: Dict[str, Any],
        ambiguity: Optional[Dict[str, Any]] = None,
    ) -> List[GeneratedTestCase]:
        actor = normalized_req.get('actor', 'User')
        action = normalized_req.get('action', 'perform action')
        conditions = normalized_req.get('conditions', [])
        outcome = normalized_req.get('expected_outcome', 'success')
        req_id = normalized_req.get('requirement_id', f"REQ-{uuid.uuid4().hex[:8].upper()}")
        types = classification.get('types', ['Functional'])
        priority_hint = classification.get('priority_hint', 'Medium')

        test_cases: List[GeneratedTestCase] = []

        # Always generate Positive + Negative
        test_cases.append(GeneratedTestCase(
            requirement_id=req_id,
            test_type="Positive",
            title=_tc_title(action, actor, "Positive", outcome),
            preconditions=conditions if conditions else [f"{actor} is on the relevant page/state"],
            steps=_positive_steps(actor, action, conditions),
            test_data={"inputs": {"actor": actor, "scenario": "valid"}, "expected_state": "success"},
            expected_result=f"{outcome} — system responds with success status",
            template_id="TMPL-POSITIVE-001",
            rules_applied=["template:positive_happy_path", "rule:actor_action_mapping"],
        ))

        test_cases.append(GeneratedTestCase(
            requirement_id=req_id,
            test_type="Negative",
            title=_tc_title(action, actor, "Negative", outcome),
            preconditions=["System is in valid initial state"],
            steps=_negative_steps(actor, action),
            test_data={"inputs": {"actor": actor, "scenario": "invalid"}, "expected_state": "error"},
            expected_result="System returns appropriate error response; state is unchanged",
            template_id="TMPL-NEGATIVE-001",
            rules_applied=["template:negative_invalid_input", "rule:error_handling"],
        ))

        # Type-specific extras
        type_str = ' '.join(types).lower()

        if any(t in type_str for t in ['performance', 'api', 'nfr']):
            test_cases.append(GeneratedTestCase(
                requirement_id=req_id,
                test_type="Boundary",
                title=_tc_title(action, actor, "Boundary", outcome),
                preconditions=["Performance baseline established"],
                steps=_boundary_steps(actor, action),
                test_data={"api_request": {"method": "POST", "payload": {}}, "sla_ms": 500},
                expected_result="Response within SLA threshold; boundary values accepted/rejected correctly",
                template_id="TMPL-BOUNDARY-001",
                rules_applied=["template:boundary_value_analysis", "rule:sla_threshold"],
            ))

        if any(t in type_str for t in ['security']):
            test_cases.append(GeneratedTestCase(
                requirement_id=req_id,
                test_type="Security",
                title=_tc_title(action, actor, "Security", outcome),
                preconditions=["Attacker/unauthorized user context established"],
                steps=[
                    {"step_number": 1, "action": "Set up unauthorized user session", "expected_intermediate": None},
                    {"step_number": 2, "action": f"Attempt: {action} without required permissions", "expected_intermediate": None},
                    {"step_number": 3, "action": "Verify access denied and audit log entry", "expected_intermediate": None},
                ],
                test_data={"inputs": {"actor": "unauthorized_user"}, "attack_vector": "privilege_escalation"},
                expected_result="Access denied (403/401); no data exposed; audit log updated",
                template_id="TMPL-SECURITY-001",
                rules_applied=["template:security_unauthorized_access", "rule:least_privilege"],
            ))

        if any(t in type_str for t in ['concurrency']):
            test_cases.append(GeneratedTestCase(
                requirement_id=req_id,
                test_type="Concurrency",
                title=_tc_title(action, actor, "Concurrency", outcome),
                preconditions=["Multiple concurrent sessions available"],
                steps=[
                    {"step_number": 1, "action": f"Initiate {action} from 10 concurrent {actor} sessions simultaneously", "expected_intermediate": None},
                    {"step_number": 2, "action": "Wait for all requests to complete", "expected_intermediate": None},
                    {"step_number": 3, "action": "Verify data consistency and no race conditions", "expected_intermediate": None},
                ],
                test_data={"inputs": {"concurrent_users": 10}, "expected_state": "consistent"},
                expected_result="All requests handled correctly; no data corruption; consistent final state",
                template_id="TMPL-CONCURRENCY-001",
                rules_applied=["template:concurrency_stress", "rule:data_consistency"],
            ))

        if conditions:
            test_cases.append(GeneratedTestCase(
                requirement_id=req_id,
                test_type="Edge",
                title=_tc_title(action, actor, "Edge", outcome),
                preconditions=["Edge conditions set up"],
                steps=[
                    {"step_number": 1, "action": f"As {actor}, perform: {action} with empty/null values", "expected_intermediate": None},
                    {"step_number": 2, "action": "Verify graceful error handling", "expected_intermediate": None},
                ],
                test_data={"inputs": {"actor": actor, "scenario": "edge_empty"}},
                expected_result="Graceful handling — no crash, informative error returned",
                template_id="TMPL-EDGE-001",
                rules_applied=["template:edge_null_empty", "rule:graceful_degradation"],
            ))

        return test_cases

    def generate_test_case_id(self, req_id: str, type_code: str) -> str:
        ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        return f"TTC-{req_id}-{type_code}-{ts}"

    def _map_priority(self, priority_hint: str, type_code: str) -> str:
        hint = priority_hint if priority_hint in _PRIORITY_MAP else "Medium"
        return _PRIORITY_MAP[hint].get(type_code, "P2")
