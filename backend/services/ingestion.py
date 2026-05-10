from dataclasses import dataclass, field
from typing import List


@dataclass
class IngestionResult:
    chunks: List[str] = field(default_factory=list)
    sanitization_warnings: List[str] = field(default_factory=list)


class IngestionService:
    def ingest(self, text: str) -> IngestionResult:
        warnings = []
        sanitized = text.strip()
        if len(sanitized) != len(text):
            warnings.append("Leading/trailing whitespace removed")

        # Remove null bytes or non-printable characters
        cleaned = ''.join(c for c in sanitized if c.isprintable() or c in '\n\t')
        if cleaned != sanitized:
            warnings.append("Non-printable characters removed")

        chunks = [cleaned] if cleaned else []
        return IngestionResult(chunks=chunks, sanitization_warnings=warnings)
