import re
from dataclasses import dataclass, field
from typing import List, Optional


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


# Verbs that signal a compound action: "verb1 X and verb2 Y"
_CONJUNCTIONS = re.compile(r'\s+and\s+', re.IGNORECASE)

# Patterns that suggest a malformed / non-action string
_MALFORMED_PATTERNS = [
    re.compile(r'\d+\s+[A-Z][a-z]+'),         # "1 Product"
    re.compile(r'\([^)]+\)'),                    # parenthetical in action
    re.compile(r'(?:[A-Z][a-z]+\s+){3,}'),      # 3+ consecutive Title Case words
]

_COMMON_VERBS = {
    'reserve', 'book', 'create', 'delete', 'update', 'retrieve', 'fetch',
    'process', 'generate', 'validate', 'authenticate', 'authorize', 'login',
    'logout', 'register', 'submit', 'send', 'receive', 'block', 'allow',
    'enable', 'disable', 'redirect', 'notify', 'confirm', 'cancel', 'approve',
    'reject', 'assign', 'upload', 'download', 'search', 'filter', 'sort',
    'encrypt', 'decrypt', 'hash', 'verify',
}


def _is_malformed(action: str) -> bool:
    for pattern in _MALFORMED_PATTERNS:
        if pattern.search(action):
            return True
    words = action.split()
    # If no recognizable verb in first 3 words, likely malformed
    if words:
        first_words = {w.lower() for w in words[:3]}
        if not first_words.intersection(_COMMON_VERBS):
            return True
    return False


def _split_verb_object(action: str):
    """Return (verb, object_noun_phrase) from an action string."""
    words = action.strip().split()
    if not words:
        return '', ''
    verb = words[0]
    obj = ' '.join(words[1:]) if len(words) > 1 else ''
    return verb, obj


def _split_compound_action(action: str) -> List[str]:
    """Split 'verb1 obj1 and verb2 obj2' into ['verb1 obj1', 'verb2 obj2']."""
    parts = _CONJUNCTIONS.split(action)
    if len(parts) <= 1:
        return parts

    # Only split if next part also starts with a verb-like word
    result = []
    for part in parts:
        words = part.strip().split()
        if words and words[0].lower() in _COMMON_VERBS:
            result.append(part.strip())
        elif result:
            # Append to last part if not verb-starting (e.g. continuation)
            result[-1] += f" and {part.strip()}"
        else:
            result.append(part.strip())
    return result if result else [action]


class BehaviorExtractionService:
    def extract(
        self,
        requirement_id: str,
        normalized_data: dict,
        requirement_type: str,
    ) -> BehaviorExtractionResult:
        actor = normalized_data.get('actor', '')
        action = normalized_data.get('action', '')
        conditions = normalized_data.get('conditions', []) or []
        expected_outcome = normalized_data.get('expected_outcome', '')

        issues: List[str] = []
        confidence = 1.0

        # Detect malformed action
        if _is_malformed(action):
            issues.append(f"Malformed action detected: '{action[:50]}' - missing clear verb-object structure")
            confidence = max(0.3, confidence - 0.4)

        # Split compound actions
        action_parts = _split_compound_action(action)

        behaviors: List[AtomicBehaviorData] = []
        condition_str: Optional[str] = conditions[0] if conditions else None

        for idx, part in enumerate(action_parts, start=1):
            verb, obj = _split_verb_object(part)
            behavior_id = f"{requirement_id}-B{idx:02d}"

            description = f"{actor} {part}"
            if condition_str:
                description += f" ({condition_str})"

            behaviors.append(AtomicBehaviorData(
                behavior_id=behavior_id,
                requirement_id=requirement_id,
                actor=actor,
                action=verb if verb else part,
                object_name=obj,
                condition=condition_str,
                description=description,
            ))

        # If no behaviors produced, create a fallback
        if not behaviors:
            behaviors.append(AtomicBehaviorData(
                behavior_id=f"{requirement_id}-B01",
                requirement_id=requirement_id,
                actor=actor,
                action=action,
                object_name='',
                condition=condition_str,
                description=f"{actor} {action}",
            ))
            issues.append("Missing valid verb-object structure; fallback behavior created")
            confidence = min(confidence, 0.5)

        return BehaviorExtractionResult(
            behaviors=behaviors,
            confidence=confidence,
            issues=issues,
        )
