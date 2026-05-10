"""
Multi-format document ingestion.

Supported input formats:
  - Plain text (one requirement per sentence or per line)
  - Markdown (headings as section labels, bullet points / numbered lists as requirements)
  - Acceptance criteria (Given/When/Then / Gherkin)
  - Flat JSON / YAML list of requirement strings
  - OpenAPI-style summaries (operationId + summary extraction)
"""

import re
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class DocumentFormat(Enum):
    PLAIN_TEXT = "plain_text"
    MARKDOWN = "markdown"
    GHERKIN = "gherkin"            # Given/When/Then acceptance criteria
    JSON_LIST = "json_list"
    OPENAPI = "openapi"
    UNKNOWN = "unknown"


@dataclass
class ParsedRequirement:
    """Single normalised requirement extracted from a document."""
    req_id: str
    text: str
    document_type: str
    context: str = ""              # parent heading / section
    raw_fragment: str = ""         # original text before cleaning


@dataclass
class IngestionResult:
    requirements: List[ParsedRequirement] = field(default_factory=list)
    document_format: DocumentFormat = DocumentFormat.UNKNOWN
    sanitization_warnings: List[str] = field(default_factory=list)
    # Legacy compatibility — first chunk as plain text
    chunks: List[str] = field(default_factory=list)


# ── Format detection ─────────────────────────────────────────────────────────

def _detect_format(text: str) -> DocumentFormat:
    stripped = text.strip()
    # JSON
    if stripped.startswith(('[', '{')):
        try:
            json.loads(stripped)
            return DocumentFormat.JSON_LIST
        except json.JSONDecodeError:
            pass
    # Gherkin
    if re.search(r'^\s*(Given|When|Then|And|But)\b', text, re.MULTILINE | re.IGNORECASE):
        return DocumentFormat.GHERKIN
    # OpenAPI-ish (has operationId or 'summary:' keys)
    if re.search(r'operationId|"summary"\s*:', text):
        return DocumentFormat.OPENAPI
    # Markdown (headings or bullet lists)
    if re.search(r'^#{1,4}\s', text, re.MULTILINE) or re.search(r'^\s*[-*]\s', text, re.MULTILINE):
        return DocumentFormat.MARKDOWN
    return DocumentFormat.PLAIN_TEXT


# ── Per-format parsers ────────────────────────────────────────────────────────

def _parse_plain_text(text: str) -> List[ParsedRequirement]:
    """
    Split on newlines; for single-paragraph input, split on sentence boundaries.
    A "sentence boundary" is end-of-sentence punctuation followed by whitespace
    and an uppercase letter — safe against decimals and abbreviations.
    """
    _SENT_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')

    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 10]

    # Expand any long "line" that is actually multiple sentences
    expanded: List[str] = []
    for line in lines:
        if _SENT_SPLIT.search(line):
            parts = [p.strip() for p in _SENT_SPLIT.split(line) if p.strip()]
            expanded.extend(parts)
        else:
            expanded.append(line)

    # Fallback: whole text is one blob with no newlines
    if not expanded:
        expanded = [s.strip() for s in _SENT_SPLIT.split(text) if len(s.strip()) > 10]

    if not expanded:
        expanded = [text.strip()]

    results = []
    for i, line in enumerate(expanded, 1):
        results.append(ParsedRequirement(
            req_id=f"REQ-{i:03d}",
            text=line,
            document_type="plain_text",
            raw_fragment=line,
        ))
    return results


def _parse_markdown(text: str) -> List[ParsedRequirement]:
    """Extract requirements from markdown bullet/numbered lists under headings."""
    results = []
    current_section = ""
    req_counter = 0
    for line in text.splitlines():
        # Heading → becomes context for following items
        heading = re.match(r'^#{1,4}\s+(.+)', line)
        if heading:
            current_section = heading.group(1).strip()
            continue
        # Bullet or numbered list item
        item = re.match(r'^\s*(?:[-*+]|\d+\.)\s+(.+)', line)
        if item:
            content = item.group(1).strip()
            if len(content) > 10:
                req_counter += 1
                results.append(ParsedRequirement(
                    req_id=f"REQ-{req_counter:03d}",
                    text=content,
                    document_type="markdown",
                    context=current_section,
                    raw_fragment=line.strip(),
                ))
    if not results:
        # Fall back to plain text if no list items found
        results = _parse_plain_text(text)
    return results


def _parse_gherkin(text: str) -> List[ParsedRequirement]:
    """Parse Given/When/Then blocks into coherent requirement statements."""
    scenarios: List[ParsedRequirement] = []
    current_scenario: Optional[str] = None
    current_steps: List[str] = []
    scenario_counter = 0

    for line in text.splitlines():
        stripped = line.strip()
        scenario_match = re.match(r'^(Scenario|Scenario Outline|Feature|Rule)\s*:\s*(.+)', stripped, re.IGNORECASE)
        step_match = re.match(r'^(Given|When|Then|And|But)\s+(.+)', stripped, re.IGNORECASE)

        if scenario_match:
            # Flush previous scenario
            if current_steps:
                scenario_counter += 1
                full_text = " ".join(current_steps)
                scenarios.append(ParsedRequirement(
                    req_id=f"REQ-{scenario_counter:03d}",
                    text=full_text,
                    document_type="gherkin",
                    context=current_scenario or "",
                    raw_fragment=full_text,
                ))
            current_scenario = scenario_match.group(2).strip()
            current_steps = []
        elif step_match:
            keyword = step_match.group(1).capitalize()
            step_text = step_match.group(2).strip()
            current_steps.append(f"{keyword} {step_text}")

    # Flush last scenario
    if current_steps:
        scenario_counter += 1
        full_text = " ".join(current_steps)
        scenarios.append(ParsedRequirement(
            req_id=f"REQ-{scenario_counter:03d}",
            text=full_text,
            document_type="gherkin",
            context=current_scenario or "",
            raw_fragment=full_text,
        ))
    return scenarios


def _parse_json_list(text: str) -> List[ParsedRequirement]:
    """Parse a JSON array of strings or objects."""
    data = json.loads(text.strip())
    results = []
    items = data if isinstance(data, list) else data.get('requirements', [])
    for i, item in enumerate(items, 1):
        if isinstance(item, str):
            req_text = item
            req_id = f"REQ-{i:03d}"
        elif isinstance(item, dict):
            req_text = item.get('text') or item.get('description') or item.get('requirement', '')
            req_id = item.get('id') or item.get('req_id') or f"REQ-{i:03d}"
        else:
            continue
        if len(req_text.strip()) > 5:
            results.append(ParsedRequirement(
                req_id=str(req_id),
                text=req_text.strip(),
                document_type="json",
                raw_fragment=str(item),
            ))
    return results


def _parse_openapi(text: str) -> List[ParsedRequirement]:
    """Extract operation summaries/descriptions from OpenAPI-like JSON."""
    try:
        spec = json.loads(text)
    except json.JSONDecodeError:
        return _parse_plain_text(text)

    results = []
    counter = 0
    paths = spec.get('paths', {})
    for path, methods in paths.items():
        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue
            summary = operation.get('summary', '')
            description = operation.get('description', '')
            op_id = operation.get('operationId', f"{method.upper()}_{path}")
            req_text = summary or description
            if req_text:
                counter += 1
                results.append(ParsedRequirement(
                    req_id=f"REQ-{counter:03d}",
                    text=f"{method.upper()} {path} — {req_text}",
                    document_type="openapi",
                    context=op_id,
                    raw_fragment=req_text,
                ))
    return results or _parse_plain_text(text)


# ── Public service ────────────────────────────────────────────────────────────

_PARSERS = {
    DocumentFormat.PLAIN_TEXT: _parse_plain_text,
    DocumentFormat.MARKDOWN: _parse_markdown,
    DocumentFormat.GHERKIN: _parse_gherkin,
    DocumentFormat.JSON_LIST: _parse_json_list,
    DocumentFormat.OPENAPI: _parse_openapi,
}


class IngestionService:
    def ingest(self, text: str, format_hint: Optional[str] = None) -> IngestionResult:
        """
        Ingest a document and return structured parsed requirements.

        Args:
            text: Raw document content.
            format_hint: Optional override ('markdown', 'gherkin', 'json', 'openapi').
        """
        warnings: List[str] = []

        # Sanitize
        cleaned = text.strip()
        if len(cleaned) != len(text):
            warnings.append("Leading/trailing whitespace removed")
        cleaned = ''.join(c for c in cleaned if c.isprintable() or c in '\n\t')
        if cleaned != text.strip():
            warnings.append("Non-printable characters removed")

        if not cleaned:
            return IngestionResult(
                sanitization_warnings=["Empty input after sanitization"],
                chunks=[],
            )

        # Detect format
        fmt = DocumentFormat.UNKNOWN
        if format_hint:
            try:
                fmt = DocumentFormat(format_hint.lower())
            except ValueError:
                warnings.append(f"Unknown format hint '{format_hint}', auto-detecting")
        if fmt == DocumentFormat.UNKNOWN:
            fmt = _detect_format(cleaned)

        # Parse
        parser = _PARSERS.get(fmt, _parse_plain_text)
        try:
            requirements = parser(cleaned)
        except Exception as exc:
            warnings.append(f"Parser error ({fmt.value}): {exc}; falling back to plain text")
            requirements = _parse_plain_text(cleaned)

        if not requirements:
            warnings.append("No requirements extracted; treating entire input as single requirement")
            requirements = [ParsedRequirement(
                req_id="REQ-001",
                text=cleaned[:2000],
                document_type="plain_text",
                raw_fragment=cleaned[:2000],
            )]

        return IngestionResult(
            requirements=requirements,
            document_format=fmt,
            sanitization_warnings=warnings,
            chunks=[r.text for r in requirements],  # legacy compatibility
        )
