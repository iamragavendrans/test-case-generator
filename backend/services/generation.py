from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class GenerationConfig:
    determinism_seed: str = "v1-rule-based"


@dataclass
class TestCase:
    requirement_id: str
    test_type: str
    title: str
    steps: List[dict]
    test_data: dict
    expected_result: str
    preconditions: List[str]
    rules_applied: List[str]
    template_id: str


_PRIORITY_MAP = {
    'SEC': 'High',
    'NEG': 'High',
    'POS': 'Medium',
    'BND': 'Medium',
    'EDG': 'Medium',
    'CON': 'High',
    'FAI': 'High',
    'INT': 'Medium',
    'PER': 'High',
}


class TestCaseGenerationService:
    def __init__(self):
        self.config = GenerationConfig()
        self._id_counters: Dict[str, int] = {}

    def generate(
        self,
        normalized_req: dict,
        classification: dict,
        ambiguity: Optional[dict] = None,
    ) -> List[TestCase]:
        req_id = normalized_req.get('requirement_id', 'REQ-UNKNOWN')
        actor = normalized_req.get('actor', 'User') or 'User'
        action = normalized_req.get('action', 'perform action') or 'perform action'
        conditions = normalized_req.get('conditions', []) or []
        outcome = normalized_req.get('expected_outcome', 'success') or 'success'

        types = classification.get('types', ['Functional']) or ['Functional']

        test_cases: List[TestCase] = []

        # Always generate Positive
        condition_ctx = (
            f"when {conditions[0]}" if conditions else "when valid inputs are provided"
        )
        test_cases.append(TestCase(
            requirement_id=req_id,
            test_type='Positive',
            title=f"{actor} {action} {condition_ctx}, expecting {outcome}",
            steps=[
                {'step_number': 1, 'action': 'Set up valid preconditions for the test'},
                {'step_number': 2, 'action': f'{actor} performs: {action}'},
                {'step_number': 3, 'action': 'Verify the system returns the expected outcome'},
            ],
            test_data={'inputs': {'actor': actor, 'action': action, 'conditions': conditions}},
            expected_result=f"System should confirm: {outcome}",
            preconditions=['System is in a valid state', 'Valid test data is available'],
            rules_applied=[f'template:positive-functional-TC-001', 'rule:actor-action-outcome'],
            template_id='positive-functional-TC-001',
        ))

        # Always generate Negative
        test_cases.append(TestCase(
            requirement_id=req_id,
            test_type='Negative',
            title=f"{actor} attempts {action} when invalid inputs provided, expecting error response",
            steps=[
                {'step_number': 1, 'action': 'Prepare invalid or missing input data'},
                {'step_number': 2, 'action': f'{actor} performs: {action} with invalid data'},
                {'step_number': 3, 'action': 'Verify system returns appropriate error'},
            ],
            test_data={'inputs': {'actor': actor, 'action': action, 'invalid': True}},
            expected_result='System should return an appropriate error message and reject the request',
            preconditions=['System is in a valid state'],
            rules_applied=[f'template:negative-TC-002', 'rule:invalid-input'],
            template_id='negative-TC-002',
        ))

        # Generate type-specific tests
        types_lower = [t.lower() for t in types]

        if any(t in types_lower for t in ['performance', 'api behavior', 'api_behavior']):
            test_cases.append(TestCase(
                requirement_id=req_id,
                test_type='Boundary',
                title=f"{actor} {action} when boundary conditions are tested, expecting system to handle limits",
                steps=[
                    {'step_number': 1, 'action': 'Identify boundary values for inputs'},
                    {'step_number': 2, 'action': f'{actor} performs: {action} at boundary values'},
                    {'step_number': 3, 'action': 'Verify behaviour at boundary'},
                ],
                test_data={'inputs': {'actor': actor, 'boundary': True}},
                expected_result='System should handle boundary conditions correctly',
                preconditions=['System is in a valid state'],
                rules_applied=['template:boundary-TC-003', 'rule:boundary-analysis'],
                template_id='boundary-TC-003',
            ))

        if any(t in types_lower for t in ['security']):
            test_cases.append(TestCase(
                requirement_id=req_id,
                test_type='Security',
                title=f"{actor} {action} when unauthorized access is attempted, expecting access denied",
                steps=[
                    {'step_number': 1, 'action': 'Set up unauthorized access scenario'},
                    {'step_number': 2, 'action': f'Attempt {action} without proper permissions'},
                    {'step_number': 3, 'action': 'Verify access is denied and logged'},
                ],
                test_data={'inputs': {'actor': actor, 'unauthorized': True}},
                expected_result='System should deny access and return security error',
                preconditions=['System security controls are active'],
                rules_applied=['template:security-TC-004', 'rule:unauthorized-access'],
                template_id='security-TC-004',
            ))

        if conditions:
            test_cases.append(TestCase(
                requirement_id=req_id,
                test_type='Edge',
                title=f"{actor} {action} when edge case conditions apply, expecting graceful handling",
                steps=[
                    {'step_number': 1, 'action': 'Set up edge case scenario'},
                    {'step_number': 2, 'action': f'{actor} performs: {action} under edge conditions'},
                    {'step_number': 3, 'action': 'Verify system handles edge case gracefully'},
                ],
                test_data={'inputs': {'actor': actor, 'edge_case': True, 'conditions': conditions}},
                expected_result='System should handle edge case without failure',
                preconditions=['Edge case conditions are configured'],
                rules_applied=['template:edge-TC-005', 'rule:edge-conditions'],
                template_id='edge-TC-005',
            ))

        return test_cases

    def generate_test_case_id(self, req_id: str, test_type_prefix: str) -> str:
        key = f"{req_id}-{test_type_prefix}"
        self._id_counters[key] = self._id_counters.get(key, 0) + 1
        return f"TTC-{req_id}-{test_type_prefix}-{self._id_counters[key]:03d}"

    def _map_priority(self, priority_hint: Optional[str], test_type_prefix: str) -> str:
        mapped = _PRIORITY_MAP.get(test_type_prefix.upper()[:3], None)
        if mapped:
            return mapped
        return priority_hint or 'Medium'
