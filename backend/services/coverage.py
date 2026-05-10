from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Dimension(Enum):
    FUNCTIONAL = "Functional"
    NEGATIVE = "Negative"
    PERFORMANCE = "Performance"
    SECURITY = "Security"
    CONCURRENCY = "Concurrency"
    BOUNDARY = "Boundary"
    EDGE = "Edge"
    FAILURE = "Failure"
    INTEGRATION = "Integration"


@dataclass
class CoverageResult:
    requirement_coverage: Dict[str, int] = field(default_factory=dict)
    overall_coverage: int = 0
    gaps_detected: List[str] = field(default_factory=list)
    dimension_coverage: Dict[str, int] = field(default_factory=dict)


class DimensionApplicabilityChecker:
    def get_required_dimensions(
        self,
        requirement_text: str,
        requirement_types: List[str],
        behavior_data: dict,
    ) -> List[Dimension]:
        required = {Dimension.FUNCTIONAL, Dimension.NEGATIVE}
        text_lower = requirement_text.lower()
        types_lower = [t.lower() for t in requirement_types]

        # Performance
        if 'performance' in types_lower or 'nfr' in types_lower or any(
            w in text_lower for w in [
                'millisecond', 'milliseconds', 'seconds', 'response time',
                'within', 'uptime', 'latency', 'throughput', '99.9%',
            ]
        ):
            required.add(Dimension.PERFORMANCE)

        # Security
        if 'security' in types_lower or any(
            w in text_lower for w in [
                'encrypt', 'decrypt', 'auth', 'password', 'unauthorized',
                'sensitive', 'secure', 'payment', 'credit card', 'transaction',
                'certificate', 'token', 'aes',
            ]
        ):
            required.add(Dimension.SECURITY)

        # Concurrency
        if any(
            w in text_lower for w in [
                'concurrent', 'concurrently', 'parallel', 'thread',
                'slot', 'reserve', 'shared resource', 'multiple users',
            ]
        ):
            required.add(Dimension.CONCURRENCY)

        # Boundary
        if any(
            w in text_lower for w in [
                'between', 'range', 'minimum', 'maximum', 'limit',
                'threshold', 'value between', 'from', 'to',
            ]
        ):
            required.add(Dimension.BOUNDARY)

        # Edge
        if behavior_data and behavior_data.get('conditions'):
            required.add(Dimension.EDGE)
        if any(
            re.search(rf'\b{w}\b', text_lower)
            for w in ['if', 'when', 'unless', 'only if', 'provided that']
        ):
            required.add(Dimension.EDGE)

        # Failure
        if 'nfr' in types_lower or any(
            w in text_lower for w in [
                'payment', 'credit card', 'uptime', 'availability',
                'fail', 'error', 'recover', 'downtime',
            ]
        ):
            required.add(Dimension.FAILURE)

        return list(required)


# Lazy import to avoid circular at module level
import re


class CoverageService:
    def __init__(self):
        self._checker = DimensionApplicabilityChecker()

    def calculate(
        self,
        test_cases: List[dict],
        requirements: List[dict],
        behaviors: List[dict],
    ) -> CoverageResult:
        # Build map: requirement_id -> set of test types covered
        req_test_types: Dict[str, set] = {
            req['requirement_id']: set() for req in requirements
        }
        for tc in test_cases:
            req_id = tc.get('mapped_requirement_id', '')
            if req_id in req_test_types:
                req_test_types[req_id].add(tc.get('test_type', ''))

        req_coverage: Dict[str, int] = {}
        gaps_detected: List[str] = []
        dimension_coverage: Dict[str, int] = {}

        for req in requirements:
            req_id = req['requirement_id']
            covered_types: set = req_test_types.get(req_id, set())

            required_dims = self._checker.get_required_dimensions(
                req.get('source_text', ''),
                req.get('classification', []),
                req.get('normalized', {}),
            )
            required_names = {d.value for d in required_dims}
            covered_dims = covered_types.intersection(required_names)

            if required_names:
                pct = min(100, int(len(covered_dims) / len(required_names) * 100))
            else:
                pct = 100 if covered_types else 0

            req_coverage[req_id] = pct

            # Detect gaps
            for dim_name in sorted(required_names - covered_dims):
                gaps_detected.append(f"{req_id}: Missing {dim_name} tests")

            # Accumulate dimension coverage counts
            for dim_name in covered_types:
                dimension_coverage[dim_name] = dimension_coverage.get(dim_name, 0) + 1

        overall = (
            int(sum(req_coverage.values()) / len(req_coverage))
            if req_coverage else 0
        )

        return CoverageResult(
            requirement_coverage=req_coverage,
            overall_coverage=overall,
            gaps_detected=gaps_detected,
            dimension_coverage=dimension_coverage,
        )
