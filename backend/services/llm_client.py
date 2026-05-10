"""
LLM HTTP client with graceful rule-based fallback.

Supports:
  - Ollama  (http://ollama:11434 — default in docker-compose)
  - Any OpenAI-compatible API  (set LLM_API_BASE + LLM_API_KEY)

Environment variables:
  LLM_API_BASE    Base URL of the inference server  (default: http://localhost:11434)
  LLM_MODEL       Model name                         (default: llama3)
  LLM_API_KEY     Bearer token if required           (default: empty)
  LLM_TIMEOUT     Request timeout in seconds         (default: 60)
  LLM_MAX_RETRIES Max retries on bad JSON            (default: 2)
  LLM_ENABLED     Set to "false" to force fallback   (default: true)
"""

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Optional

from .prompts import SYSTEM_INSTRUCTION, build_generation_prompt

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

_BASE = os.getenv("LLM_API_BASE", "http://localhost:11434").rstrip("/")
_MODEL = os.getenv("LLM_MODEL", "llama3")
_API_KEY = os.getenv("LLM_API_KEY", "")
_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
_ENABLED = os.getenv("LLM_ENABLED", "true").lower() != "false"

# Ollama uses /api/chat; OpenAI-compatible servers use /v1/chat/completions.
# We auto-detect by probing /api/tags (Ollama) on startup.
_USE_OLLAMA_API: Optional[bool] = None   # resolved lazily


def _probe_ollama() -> bool:
    """Return True if the server looks like an Ollama instance."""
    try:
        req = urllib.request.Request(f"{_BASE}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3):
            return True
    except Exception:
        return False


def _resolve_api_style() -> bool:
    global _USE_OLLAMA_API
    if _USE_OLLAMA_API is None:
        _USE_OLLAMA_API = _probe_ollama()
    return _USE_OLLAMA_API


def _http_post(url: str, payload: dict) -> dict:
    """POST JSON payload, return parsed JSON response."""
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if _API_KEY:
        headers["Authorization"] = f"Bearer {_API_KEY}"

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def _call_ollama(system: str, user: str) -> str:
    """Call Ollama /api/chat endpoint."""
    url = f"{_BASE}/api/chat"
    payload = {
        "model": _MODEL,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    data = _http_post(url, payload)
    return data["message"]["content"]


def _call_openai_compat(system: str, user: str) -> str:
    """Call an OpenAI-compatible /v1/chat/completions endpoint."""
    url = f"{_BASE}/v1/chat/completions"
    payload = {
        "model": _MODEL,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    data = _http_post(url, payload)
    return data["choices"][0]["message"]["content"]


# ── Output validation ─────────────────────────────────────────────────────────

class LLMOutputError(Exception):
    """Raised when the LLM returns output that fails schema validation."""


_REQUIRED_TC_FIELDS = {"test_type", "title", "steps", "expected_result"}
_VALID_TEST_TYPES = {
    "Positive", "Negative", "Edge", "Boundary",
    "Security", "Performance", "Concurrency", "Failure", "Integration",
}
_VALID_PRIORITIES = {"High", "Medium", "Low"}


def _validate_and_clean(raw: str) -> list:
    """
    Parse and validate the LLM JSON output.

    Returns a list of cleaned test-case dicts.
    Raises LLMOutputError with a descriptive message on any failure.
    """
    # Strip markdown code fences if model ignored instructions
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = text.rstrip("`").strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMOutputError(f"Invalid JSON from LLM: {exc}") from exc

    test_cases = parsed.get("test_cases")
    if not isinstance(test_cases, list) or not test_cases:
        raise LLMOutputError("LLM response missing 'test_cases' list")

    cleaned = []
    for i, tc in enumerate(test_cases):
        missing = _REQUIRED_TC_FIELDS - set(tc.keys())
        if missing:
            raise LLMOutputError(f"test_cases[{i}] missing fields: {missing}")

        # Normalise test_type
        tt = tc.get("test_type", "Positive")
        if tt not in _VALID_TEST_TYPES:
            tt = "Positive"
        tc["test_type"] = tt

        # Ensure title contains required keywords
        title = tc.get("title", "")
        if "when" not in title.lower():
            title = f"{title} when applicable"
        if "expecting" not in title.lower():
            title = f"{title}, expecting success"
        tc["title"] = title

        # Normalise priority
        if tc.get("priority") not in _VALID_PRIORITIES:
            tc["priority"] = "Medium"

        # Ensure steps are well-formed
        steps = tc.get("steps", [])
        if not isinstance(steps, list) or not steps:
            steps = [{"step_number": 1, "action": "Execute the scenario"}]
        for j, step in enumerate(steps):
            if "step_number" not in step:
                step["step_number"] = j + 1
            if "action" not in step:
                raise LLMOutputError(f"test_cases[{i}].steps[{j}] missing 'action'")
        tc["steps"] = steps

        # Ensure test_data has inputs key
        td = tc.get("test_data")
        if not isinstance(td, dict) or "inputs" not in td:
            tc["test_data"] = {"inputs": {}, "expected_outputs": {}}

        # Ensure preconditions is a list
        if not isinstance(tc.get("preconditions"), list):
            tc["preconditions"] = []

        cleaned.append(tc)

    return cleaned


import re  # needed by _validate_and_clean


# ── Public interface ──────────────────────────────────────────────────────────

class LLMClient:
    """
    Calls the configured LLM to generate test cases.

    On any network, timeout, or validation failure, falls back to the
    rule-based generator transparently.
    """

    def __init__(self):
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        if self._available is None:
            self._available = _ENABLED and _probe_ollama()
            if not self._available:
                logger.info("LLM not available — will use rule-based fallback")
        return self._available

    def generate_test_cases(
        self,
        requirement_text: str,
        requirement_type: str,
        classification: list,
        actor: str = "",
        action: str = "",
        conditions: list = None,
        expected_outcome: str = "",
        document_type: str = "plain_text",
    ) -> tuple[list, bool]:
        """
        Generate test cases via LLM.

        Returns:
            (test_case_dicts, used_llm)
            used_llm is False when fallback was used.
        """
        if not self.is_available():
            return [], False

        user_prompt = build_generation_prompt(
            requirement_text=requirement_text,
            requirement_type=requirement_type,
            classification=classification,
            actor=actor,
            action=action,
            conditions=conditions or [],
            expected_outcome=expected_outcome,
            document_type=document_type,
        )

        use_ollama = _resolve_api_style()
        last_error: Optional[Exception] = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                if use_ollama:
                    raw = _call_ollama(SYSTEM_INSTRUCTION, user_prompt)
                else:
                    raw = _call_openai_compat(SYSTEM_INSTRUCTION, user_prompt)

                test_cases = _validate_and_clean(raw)
                logger.info("LLM generated %d test cases (attempt %d)", len(test_cases), attempt + 1)
                return test_cases, True

            except LLMOutputError as exc:
                last_error = exc
                logger.warning("LLM output validation failed (attempt %d): %s", attempt + 1, exc)
                if attempt < _MAX_RETRIES:
                    time.sleep(1)

            except Exception as exc:
                last_error = exc
                logger.warning("LLM call failed (attempt %d): %s", attempt + 1, exc)
                self._available = False   # Don't retry network errors next call
                break

        logger.warning("LLM generation failed after %d attempts: %s", _MAX_RETRIES + 1, last_error)
        return [], False
