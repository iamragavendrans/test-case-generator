"""Classification service: categorize requirements by type."""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional


class RequirementClass(Enum):
    FUNCTIONAL = "Functional"
    SECURITY = "Security"
    PERFORMANCE = "Performance"
    VALIDATION = "Validation"
    API_BEHAVIOR = "API behavior"
    NFR = "NFR"
    CONCURRENCY = "Concurrency"
    USABILITY = "Usability"
    INTEGRATION = "Integration"


_RULES: List[tuple] = [
    # (RequirementClass, keyword pattern, priority)
    # Patterns use \b only at word start; prefix-style stems omit trailing \b
    (RequirementClass.SECURITY,
     r'\b(encrypt|decrypt|authenticat|authoriz|secur|password|token|hash|ssl|tls|xss|inject|sanitiz|csrf|rbac|permission|unauthori)',
     "High"),
    (RequirementClass.PERFORMANCE,
     r'\b(response\s*time|latency|throughput|milliseconds?|tps|rps|load\s+test|benchmark|uptime|availabilit|99\.\d)',
     "High"),
    (RequirementClass.VALIDATION,
     r'\b(validat|verif|constrain|format|length|range|regex|pattern|mandatory)',
     "Medium"),
    (RequirementClass.API_BEHAVIOR,
     r'\b(endpoint|api\b|rest\b|http|post\s*/|put\s*/|patch\s*/|payload|status\s*code|graphql|grpc)',
     "Medium"),
    (RequirementClass.CONCURRENCY,
     r'\b(concurrent|parallel|race\s*condition|mutex|lock|thread|async|semaphore|atomic)',
     "High"),
    (RequirementClass.NFR,
     r'\b(maintainabilit|scalab|portab|compliance|iso\b|gdpr|hipaa|pci\b)',
     "Medium"),
    (RequirementClass.USABILITY,
     r'\b(ui\b|ux\b|user\s*interface|accessible|aria\b|screen\s*reader|i18n|l10n)',
     "Low"),
    (RequirementClass.INTEGRATION,
     r'\b(integrat|third.party|external\s+system|webhook|kafka|rabbitmq|sqs\b|ldap|saml|oauth)',
     "Medium"),
    (RequirementClass.FUNCTIONAL,
     r'\b(shall|must|login|logout|create|update|delete|read|list|search|filter|sort|submit|upload|download|reserve|process|pay|register)',
     "Medium"),
]


@dataclass
class ClassificationResult:
    primary_class: RequirementClass
    secondary_classes: List[RequirementClass] = field(default_factory=list)
    priority_hint: str = "Medium"
    confidence_scores: Dict[RequirementClass, float] = field(default_factory=dict)
    reasoning: str = ""


class ClassificationService:
    def classify(self, text: str, normalized_data: Optional[dict] = None) -> ClassificationResult:
        text_lower = text.lower()
        scores: Dict[RequirementClass, float] = {}

        for req_class, pattern, _ in _RULES:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                # Score = number of distinct matching keywords, normalized
                score = min(1.0, len(set(matches)) * 0.25 + 0.5)
                scores[req_class] = max(scores.get(req_class, 0.0), score)

        if not scores:
            scores[RequirementClass.FUNCTIONAL] = 0.5

        sorted_classes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_classes[0][0]
        secondary = [c for c, _ in sorted_classes[1:] if scores[c] >= 0.5]

        # Priority: use highest-priority rule that matched
        priority = "Medium"
        for req_class, _, prio in _RULES:
            if req_class == primary:
                priority = prio
                break
        # Security/Performance always High
        if primary in (RequirementClass.SECURITY, RequirementClass.PERFORMANCE, RequirementClass.CONCURRENCY):
            priority = "High"

        reasoning = (
            f"Primary classification: {primary.value} "
            f"(score={scores[primary]:.2f}). "
        )
        if secondary:
            reasoning += f"Secondary: {', '.join(c.value for c in secondary)}."

        return ClassificationResult(
            primary_class=primary,
            secondary_classes=secondary,
            priority_hint=priority,
            confidence_scores={c: round(s, 2) for c, s in scores.items()},
            reasoning=reasoning,
        )
