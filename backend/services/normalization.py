import re
import uuid
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

VAGUE_TERMS = [
    'fast', 'quick', 'efficient', 'secure', 'reliable', 'good', 'easy',
    'simple', 'robust', 'scalable', 'user-friendly', 'flexible', 'intuitive',
]


@dataclass
class TransformationStep:
    step_name: str
    description: str


@dataclass
class AmbiguityIssue:
    description: str
    location: str = ''


@dataclass
class NormalizedData:
    actor: str
    action: str
    conditions: List[str] = field(default_factory=list)
    expected_outcome: str = ''


@dataclass
class NormalizedRequirement:
    original_text: str
    normalized: NormalizedData
    is_ambiguous: bool = False
    clarifying_questions: List[str] = field(default_factory=list)
    ambiguity_issues: List[AmbiguityIssue] = field(default_factory=list)
    confidence: float = 1.0
    provenance: dict = field(default_factory=dict)


class NormalizationService:
    def normalize(self, text: str) -> List[NormalizedRequirement]:
        parts = self._split_compound(text)
        results = []
        for part in parts:
            result = self._normalize_single(part.strip(), text)
            results.append(result)
        return results

    def _split_compound(self, text: str) -> List[str]:
        # Split on " and X shall" where X is 1-3 words immediately before "shall"
        pattern = r'\s+and\s+(?=\w+(?:\s+\w+){0,2}\s+shall\b)'
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        if len(parts) > 1:
            return parts
        return [text]

    def _normalize_single(self, text: str, original_text: str) -> NormalizedRequirement:
        actor = self._extract_actor(text)
        action = self._extract_action(text)
        conditions = self._extract_conditions(text)
        outcome = self._extract_outcome(text, action)

        issues: List[AmbiguityIssue] = []
        questions: List[str] = []

        for term in VAGUE_TERMS:
            if re.search(r'\b' + re.escape(term) + r'\b', text, re.IGNORECASE):
                issues.append(AmbiguityIssue(f"Vague term detected: '{term}'"))
                questions.append(
                    f"What does '{term}' mean specifically? Please provide measurable criteria."
                )

        if not actor:
            issues.append(AmbiguityIssue("Missing actor - no clear subject identified"))

        confidence = 1.0
        if issues:
            confidence = max(0.5, 1.0 - 0.1 * len(issues))
        if not actor:
            confidence = min(confidence, 0.8)

        req_id = f"REQ-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        steps = [
            {'step': 'parse', 'desc': 'Parsed requirement text structure'},
            {'step': 'extract_actor', 'desc': f'Extracted actor: {actor or "unknown"}'},
            {'step': 'extract_action', 'desc': f'Extracted action: {action}'},
        ]
        if conditions:
            steps.append({'step': 'extract_conditions', 'desc': f'Extracted {len(conditions)} condition(s)'})
        if issues:
            steps.append({'step': 'detect_ambiguity', 'desc': f'Detected {len(issues)} ambiguity issue(s)'})

        return NormalizedRequirement(
            original_text=text,
            normalized=NormalizedData(
                actor=actor,
                action=action,
                conditions=conditions,
                expected_outcome=outcome,
            ),
            is_ambiguous=bool(issues),
            clarifying_questions=questions,
            ambiguity_issues=issues,
            confidence=confidence,
            provenance={
                'original_text': original_text,
                'transformation_steps': steps,
                'confidence': confidence,
                'requirement_id': req_id,
            },
        )

    # Words that begin a conditional clause, not the actor
    _CONDITIONAL_STARTERS = re.compile(
        r'^(if|when|unless|provided that|given that|after|before|once)\b',
        re.IGNORECASE,
    )

    def _extract_actor(self, text: str) -> str:
        for modal in ['shall', 'must', 'should', 'will']:
            # Find the modal anywhere in the text (not just at the start)
            m = re.search(rf'\b{modal}\b', text, re.IGNORECASE)
            if not m:
                continue
            # Everything before the modal is a candidate for the actor phrase
            before = text[:m.start()].strip().rstrip(',')
            if not before:
                continue
            # If there's a comma, take the part AFTER the comma (conditional clause pattern:
            # "If X, the system shall…" → actor is "the system")
            if ',' in before:
                before = before.split(',')[-1].strip()
            # Skip if what remains starts with a conditional word
            if self._CONDITIONAL_STARTERS.match(before):
                continue
            # Strip leading articles for cleanliness
            actor = re.sub(r'^(the|a|an)\s+', '', before, flags=re.IGNORECASE).strip()
            if actor:
                return actor[0].upper() + actor[1:]
        return ''

    def _extract_action(self, text: str) -> str:
        match = re.search(
            r'\b(?:shall|must|should|will)\s+(.+?)(?:\s+when\b|\s+if\b|\s*$)',
            text,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
        return text.strip()

    def _extract_conditions(self, text: str) -> List[str]:
        conditions = []
        when_match = re.search(r'\bwhen\b\s+(.+?)(?:\s+and\s+\w+\s+shall\b|$)', text, re.IGNORECASE)
        if when_match:
            conditions.append(when_match.group(1).strip())
        if_match = re.search(r'\bif\b\s+(.+?)(?:\s+then\b|\s+and\s+\w+\s+shall\b|$)', text, re.IGNORECASE)
        if if_match:
            conditions.append(if_match.group(1).strip())
        return conditions

    def _extract_outcome(self, text: str, action: str) -> str:
        outcome_match = re.search(r'(?:result(?:ing)?|outcome|then)\s+(.+)$', text, re.IGNORECASE)
        if outcome_match:
            return outcome_match.group(1).strip()
        return action
