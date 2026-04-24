"""Atomic behavior extraction service."""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class AtomicBehaviorData:
    behavior_id: str
    requirement_id: str
    actor: str
    action: str
    object_name: str
    condition: Optional[str]
    description: str


@dataclass
class BehaviorExtractionResult:
    behaviors: List[AtomicBehaviorData] = field(default_factory=list)
    confidence: float = 1.0
    issues: List[str] = field(default_factory=list)


_COMPOUND_SPLIT = re.compile(r'\s+and\s+(?=\w)', re.IGNORECASE)

# Patterns to detect malformed / non-action text
_MALFORMED_RE = re.compile(r'\b(overview|product|name|section|\d+\s+\w+\s+overview)\b', re.IGNORECASE)


def _extract_object(action: str) -> str:
    """Heuristic: last noun phrase (last 1–3 words) is the object."""
    # Remove leading verb
    tokens = action.strip().split()
    if len(tokens) <= 1:
        return ""
    # Object = everything after the first verb word
    obj_tokens = tokens[1:]
    return ' '.join(obj_tokens[:3])


def _split_compound_action(action: str) -> List[str]:
    parts = _COMPOUND_SPLIT.split(action)
    return [p.strip() for p in parts if p.strip()]


def _make_behavior_id(requirement_id: str, index: int) -> str:
    safe_id = re.sub(r'[^A-Za-z0-9]', '', requirement_id)
    return f"{safe_id}-B{index:02d}"


def _is_malformed(action: str) -> bool:
    if not action:
        return True
    if _MALFORMED_RE.search(action):
        return True
    words = action.split()
    # Too many digits / uppercase tokens suggest copy-paste noise
    noise = sum(1 for w in words if re.match(r'^\d+$', w) or (w.isupper() and len(w) > 2))
    return noise >= 2


class BehaviorExtractionService:
    def extract(
        self,
        requirement_id: str,
        normalized_data: Dict[str, Any],
        requirement_type: str,
    ) -> BehaviorExtractionResult:
        actor = normalized_data.get('actor', '')
        action = normalized_data.get('action', '')
        conditions: List[str] = normalized_data.get('conditions', [])
        outcome = normalized_data.get('expected_outcome', '')

        issues: List[str] = []
        confidence = 1.0

        if _is_malformed(action):
            issues.append(f"Malformed or missing action text: '{action[:50]}'")
            confidence = max(0.3, confidence - 0.5)

        # Split compound actions
        sub_actions = _split_compound_action(action) if not _is_malformed(action) else [action or "unknown action"]

        condition_str = conditions[0] if conditions else None

        behaviors: List[AtomicBehaviorData] = []
        for idx, sub_action in enumerate(sub_actions, start=1):
            obj_name = _extract_object(sub_action)
            desc = f"{actor} {sub_action}".strip()
            if condition_str:
                desc += f" ({condition_str})"

            behaviors.append(AtomicBehaviorData(
                behavior_id=_make_behavior_id(requirement_id, idx),
                requirement_id=requirement_id,
                actor=actor,
                action=sub_action,
                object_name=obj_name,
                condition=condition_str,
                description=desc,
            ))

        return BehaviorExtractionResult(
            behaviors=behaviors,
            confidence=round(confidence, 2),
            issues=issues,
        )
