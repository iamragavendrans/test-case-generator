"""Normalization service: Actor-Action-Conditions-Outcome extraction."""
import re
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class TransformationStep:
    step: str
    description: str


@dataclass
class NormalizedRequirement:
    actor: str = ""
    action: str = ""
    conditions: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    feature_area: str = ""



@dataclass
class AmbiguityIssue:
    description: str
    severity: str = "medium"


@dataclass
class NormalizationResult:
    original_text: str
    normalized: NormalizedRequirement
    is_ambiguous: bool
    ambiguity_issues: List[AmbiguityIssue]
    clarifying_questions: List[str]
    confidence: float
    provenance: Dict[str, Any]


_VAGUE_TERMS = [
    'fast', 'quick', 'slow', 'secure', 'safe', 'reliable',
    'efficient', 'good', 'nice', 'proper', 'appropriate', 'reasonable',
    'user-friendly', 'easy', 'simple',
]

_CONDITION_MARKERS = ['when', 'if', 'unless', 'provided that', 'given that', 'in case']

_ACTOR_PATTERNS = [
    r'^(user|system|admin|administrator|administrator|client|server|api|customer|'
    r'payment gateway|database|browser|application|app)\b',
]

# Splits on "and <actor> shall" patterns to decompose compound requirements
_COMPOUND_SPLIT_RE = re.compile(
    r'\s+and\s+(user|system|admin|client|server|api|customer|payment gateway|database|browser|application|app)\s+shall\s+',
    re.IGNORECASE,
)


def _extract_actor(text: str) -> str:
    m = re.match(r'^([\w\s]+?)\s+shall\b', text, re.IGNORECASE)
    if m:
        return m.group(1).strip().title()
    # fallback: first capitalized word that isn't a modal verb
    m2 = re.match(r'^([A-Z]\w+)', text)
    if m2 and m2.group(1).lower() not in ('shall', 'should', 'must', 'will', 'may', 'can'):
        return m2.group(1)
    return ""


def _extract_action_and_conditions(text: str, actor: str):
    # Remove leading "<Actor> shall " prefix
    body = re.sub(r'^.*?\bshall\b\s*', '', text, count=1, flags=re.IGNORECASE).strip()

    conditions: List[str] = []
    action = body

    # Pull out condition clauses
    for marker in _CONDITION_MARKERS:
        pattern = re.compile(
            rf'(?:,?\s*{re.escape(marker)}\s+)(.+?)(?:$|,|\s+and\s+)', re.IGNORECASE
        )
        for m in pattern.finditer(body):
            conditions.append(f"{marker} {m.group(1).strip()}")
        # Remove the condition clause from the action text
        action = re.sub(
            rf',?\s*{re.escape(marker)}\s+.+?(?:$|,(?:\s+and\s+)?)', '', action, flags=re.IGNORECASE
        ).strip()

    action = re.sub(r'\s+', ' ', action).strip()
    return action, conditions


def _extract_outcome(text: str, actor: str, action: str) -> str:
    if 'login' in action.lower() or 'authenticate' in action.lower():
        return f"{actor} is authenticated successfully"
    if 'logout' in action.lower():
        return f"{actor} session is terminated"
    if 'create' in action.lower() or 'add' in action.lower():
        return "Resource is created successfully"
    if 'delete' in action.lower() or 'remove' in action.lower():
        return "Resource is removed successfully"
    if 'update' in action.lower() or 'edit' in action.lower():
        return "Resource is updated successfully"
    if 'validate' in action.lower() or 'check' in action.lower():
        return "Input is validated and result is returned"
    if 'encrypt' in action.lower():
        return "Data is encrypted"
    if 'process' in action.lower():
        return "Operation is processed successfully"
    if 'respond' in action.lower() or 'response' in action.lower():
        return "Response is returned within specified time"
    return f"{action.capitalize()} is completed successfully"


def _detect_ambiguities(text: str, actor: str, action: str):
    issues: List[AmbiguityIssue] = []
    questions: List[str] = []

    for term in _VAGUE_TERMS:
        if re.search(rf'\b{re.escape(term)}\b', text, re.IGNORECASE):
            issues.append(AmbiguityIssue(f"Vague term '{term}' detected — needs quantification"))
            questions.append(f"What specific, measurable definition applies to '{term}'?")

    if not actor:
        issues.append(AmbiguityIssue("Missing actor — who performs this action?"))
        questions.append("Who is the actor performing this action?")

    if not action or len(action.split()) < 2:
        issues.append(AmbiguityIssue("Action is too vague or missing"))
        questions.append("What specific action should be taken?")

    return issues, questions


def _make_req_id() -> str:
    from datetime import datetime
    return f"REQ-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"


def _normalize_single(text: str) -> NormalizationResult:
    steps: List[str] = []
    text = text.strip()

    actor = _extract_actor(text)
    steps.append("actor_extraction")

    action, conditions = _extract_action_and_conditions(text, actor)
    steps.append("action_extraction")
    if conditions:
        steps.append("condition_extraction")

    outcome = _extract_outcome(text, actor, action)
    steps.append("outcome_inference")

    issues, questions = _detect_ambiguities(text, actor, action)
    steps.append("ambiguity_detection")

    confidence = 1.0
    if not actor:
        confidence -= 0.2
    if any(t in text.lower() for t in _VAGUE_TERMS):
        confidence -= 0.15
    confidence = max(0.3, round(confidence, 2))

    req_id = _make_req_id()
    normalized = NormalizedRequirement(
        actor=actor,
        action=action,
        conditions=conditions,
        expected_outcome=outcome,
    )

    return NormalizationResult(
        original_text=text,
        normalized=normalized,
        is_ambiguous=bool(issues),
        ambiguity_issues=issues,
        clarifying_questions=questions,
        confidence=confidence,
        provenance={
            'original_text': text,
            'transformation_steps': steps,
            'confidence': confidence,
            'requirement_id': req_id,
        },
    )


class NormalizationService:
    def normalize(self, text: str) -> List[NormalizationResult]:
        text = text.strip()

        # Split compound requirements of form "<A> shall X and <B> shall Y"
        parts = _COMPOUND_SPLIT_RE.split(text)
        if len(parts) > 1:
            # Rebuild each sub-requirement with its actor prefix
            actors_found = _COMPOUND_SPLIT_RE.findall(text)
            reconstructed = [parts[0].strip()]
            for actor_word, part in zip(actors_found, parts[1:]):
                reconstructed.append(f"{actor_word} shall {part}".strip())
            return [_normalize_single(p) for p in reconstructed if p]

        return [_normalize_single(text)]
