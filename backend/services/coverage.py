"""Coverage calculation service."""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Set, Any


class Dimension(Enum):
    FUNCTIONAL = "Functional"
    NEGATIVE = "Negative"
    BOUNDARY = "Boundary"
    EDGE = "Edge"
    SECURITY = "Security"
    PERFORMANCE = "Performance"
    CONCURRENCY = "Concurrency"
    FAILURE = "Failure"
    INTEGRATION = "Integration"


@dataclass
class CoverageResult:
    requirement_coverage: Dict[str, float] = field(default_factory=dict)
    overall_coverage: float = 0.0
    gaps_detected: List[str] = field(default_factory=list)
    dimension_coverage: Dict[str, int] = field(default_factory=dict)


_TYPE_TO_DIMENSION = {
    "Functional": Dimension.FUNCTIONAL,
    "Positive": Dimension.FUNCTIONAL,
    "Negative": Dimension.NEGATIVE,
    "Boundary": Dimension.BOUNDARY,
    "Edge": Dimension.EDGE,
    "Security": Dimension.SECURITY,
    "Performance": Dimension.PERFORMANCE,
    "Concurrency": Dimension.CONCURRENCY,
    "Failure": Dimension.FAILURE,
    "Integration": Dimension.INTEGRATION,
}


class DimensionApplicabilityChecker:
    def get_required_dimensions(
        self,
        requirement_text: str,
        requirement_types: List[str],
        behavior_data: Dict[str, Any],
    ) -> Set[Dimension]:
        required: Set[Dimension] = {Dimension.FUNCTIONAL, Dimension.NEGATIVE}
        text = requirement_text.lower()

        if any(t in ('Performance', 'NFR') for t in requirement_types) or \
                re.search(r'\b(millisecond|ms\b|second|latency|throughput|uptime|sla)\b', text):
            required.add(Dimension.PERFORMANCE)

        if any(t == 'Security' for t in requirement_types) or \
                re.search(r'\b(encrypt|authenticat|authoriz|secur|password|token|sql|xss|csrf)\b', text):
            required.add(Dimension.SECURITY)

        if re.search(r'\b(concurrent|parallel|thread|async|race|mutex|reserve|slot|booking)\b', text):
            required.add(Dimension.CONCURRENCY)

        if re.search(r'\b(payment|credit\s*card|transaction|billing|invoice|checkout)\b', text):
            required.add(Dimension.SECURITY)
            required.add(Dimension.FAILURE)

        if any(t == 'NFR' for t in requirement_types) or \
                re.search(r'\b(uptime|availabilit|99\.\d+)\b', text):
            required.add(Dimension.PERFORMANCE)
            required.add(Dimension.FAILURE)

        if re.search(r'\b(between|range|minimum|maximum|min|max|limit|threshold|\d+\s+and\s+\d+)\b', text) or \
                any(t == 'Validation' for t in requirement_types):
            required.add(Dimension.BOUNDARY)

        conditions = behavior_data.get('conditions', [])
        if conditions or re.search(r'\b(when|if|unless|given|provided)\b', text):
            required.add(Dimension.EDGE)

        return required


class CoverageService:
    def __init__(self):
        self._checker = DimensionApplicabilityChecker()

    def calculate(
        self,
        test_cases: List[Dict[str, Any]],
        requirements: List[Dict[str, Any]],
        behaviors: List[Dict[str, Any]],
    ) -> CoverageResult:
        dimension_coverage: Dict[str, int] = {}
        for tc in test_cases:
            tc_type = tc.get('test_type', '')
            dim = _TYPE_TO_DIMENSION.get(tc_type)
            if dim:
                dimension_coverage[dim.value] = dimension_coverage.get(dim.value, 0) + 1

        req_coverage: Dict[str, float] = {}
        gaps: List[str] = []

        for req in requirements:
            req_id = req.get('requirement_id', 'UNKNOWN')
            req_text = req.get('source_text', '')
            req_types = req.get('classification', ['Functional'])
            normalized = req.get('normalized', {})

            required_dims = self._checker.get_required_dimensions(req_text, req_types, normalized)

            # Test cases mapped to this requirement
            mapped_types = {
                tc.get('test_type', '')
                for tc in test_cases
                if tc.get('mapped_requirement_id') == req_id or
                   tc.get('behavior_id', '').startswith(req_id.replace('-', '').replace(' ', ''))
            }

            covered_dims = {
                _TYPE_TO_DIMENSION[t]
                for t in mapped_types
                if t in _TYPE_TO_DIMENSION
            }

            if not required_dims:
                req_coverage[req_id] = 0.0
                continue

            pct = min(100.0, round(len(covered_dims & required_dims) / len(required_dims) * 100, 1))
            req_coverage[req_id] = pct

            missing = required_dims - covered_dims
            for dim in missing:
                gaps.append(f"{req_id}: Missing {dim.value} test coverage")

        overall = round(sum(req_coverage.values()) / len(req_coverage), 1) if req_coverage else 0.0

        return CoverageResult(
            requirement_coverage=req_coverage,
            overall_coverage=overall,
            gaps_detected=gaps,
            dimension_coverage=dimension_coverage,
        )
