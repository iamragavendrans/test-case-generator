"""Ingestion service: sanitize and chunk raw requirement text."""
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class IngestionResult:
    chunks: List[str] = field(default_factory=list)
    sanitization_warnings: List[str] = field(default_factory=list)


class IngestionService:
    _CONTROL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
    _SCRIPT_RE = re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)
    _SQL_RE = re.compile(r'\b(DROP|DELETE|INSERT|UPDATE|SELECT)\b', re.IGNORECASE)
    _MULTI_SPACE = re.compile(r'[ \t]{2,}')

    def ingest(self, text: str) -> IngestionResult:
        warnings: List[str] = []
        sanitized = text

        if self._SCRIPT_RE.search(sanitized):
            warnings.append("Potential script injection removed")
            sanitized = self._SCRIPT_RE.sub('', sanitized)

        if self._SQL_RE.search(sanitized):
            warnings.append("SQL-like keywords detected")

        if self._CONTROL_RE.search(sanitized):
            warnings.append("Control characters stripped")
            sanitized = self._CONTROL_RE.sub(' ', sanitized)

        sanitized = self._MULTI_SPACE.sub(' ', sanitized).strip()

        # Split on sentence boundaries / semicolons for multi-requirement text
        raw_chunks = re.split(r'(?<=[.!?;])\s+|\n+', sanitized)
        chunks = [c.strip() for c in raw_chunks if c.strip()]
        if not chunks:
            chunks = [sanitized]

        return IngestionResult(chunks=chunks, sanitization_warnings=warnings)
