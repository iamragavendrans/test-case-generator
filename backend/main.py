"""
FastAPI application for the Test Case Generator API.

Endpoints:
  GET  /health           — liveness check
  POST /generate         — generate test cases from a single requirement
  POST /batch            — generate test cases from multiple requirements
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone

from services.ingestion import IngestionService
from services.normalization import NormalizationService
from services.classification import ClassificationService
from services.generation import TestCaseGenerationService

app = FastAPI(
    title="Test Case Generator API",
    description="Rule-based test case generation from natural-language requirements",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_ingestion = IngestionService()
_normalization = NormalizationService()
_classification = ClassificationService()
_generation = TestCaseGenerationService()


# ── Request / Response models ────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    requirement: str = Field(..., min_length=5, description="Requirement text to process")


class BatchRequest(BaseModel):
    requirements: List[str] = Field(..., min_items=1, description="List of requirement strings")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _process_single(text: str) -> dict:
    """Full pipeline for one requirement text; returns structured output dict."""
    ingest_result = _ingestion.ingest(text)
    norm_results = _normalization.normalize(text)

    all_test_cases = []
    all_normalized = []

    for norm in norm_results:
        norm_dict = norm.normalized.__dict__ if hasattr(norm.normalized, '__dict__') else norm.normalized
        classification = _classification.classify(norm.original_text, norm_dict)

        generated = _generation.generate(
            normalized_req=norm_dict,
            classification={
                'types': [c.value for c in [classification.primary_class] + classification.secondary_classes],
                'priority_hint': classification.priority_hint,
            },
            ambiguity={
                'is_ambiguous': norm.is_ambiguous,
                'issues': [i.description for i in norm.ambiguity_issues] if norm.ambiguity_issues else [],
                'clarifying_questions': norm.clarifying_questions,
            } if norm.is_ambiguous else None,
        )

        all_test_cases.extend((tc, classification, norm) for tc in generated)
        all_normalized.append({
            'requirement_id': norm.provenance.get('requirement_id', 'REQ-UNKNOWN'),
            'source_text': norm.original_text,
            'normalized': norm_dict,
            'classification': [classification.primary_class.value] + [c.value for c in classification.secondary_classes],
            'priority_hint': classification.priority_hint,
            'ambiguity': {
                'is_ambiguous': norm.is_ambiguous,
                'issues': [i.description for i in norm.ambiguity_issues] if norm.ambiguity_issues else [],
                'clarifying_questions': norm.clarifying_questions,
            },
            'provenance': norm.provenance,
        })

    return {
        'normalized_requirements': all_normalized,
        'test_cases': [
            {
                'test_case_id': _generation.generate_test_case_id(tc.requirement_id, tc.test_type[:3].upper()),
                'title': tc.title,
                'mapped_requirement_id': tc.requirement_id,
                'test_type': tc.test_type,
                'preconditions': tc.preconditions,
                'steps': tc.steps,
                'test_data': tc.test_data,
                'expected_result': tc.expected_result,
                'priority': _generation._map_priority(cls.priority_hint, tc.test_type[:3].upper()),
                'automation_feasibility': {
                    'feasible': True,
                    'notes': 'Standard test case',
                    'estimated_effort': 'Medium',
                },
                'determinism_seed': _generation.config.determinism_seed,
                'explainability': {
                    'generation_template_id': tc.template_id,
                    'rules_applied': tc.rules_applied,
                    'confidence': norm_item.confidence * 0.9,
                },
            }
            for tc, cls, norm_item in all_test_cases
        ],
        'audit_log': {
            'generation_timestamp': datetime.now(timezone.utc).isoformat(),
            'generator_version': '1.0.0',
            'model_reference': 'rule-based-v1',
            'sanitization_warnings': ingest_result.sanitization_warnings,
        },
    }


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/generate")
def generate(req: GenerateRequest):
    """Generate test cases from a single requirement."""
    try:
        return _process_single(req.requirement)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/batch")
def batch(req: BatchRequest):
    """Generate test cases for multiple requirements."""
    results = []
    errors = []
    for i, requirement in enumerate(req.requirements):
        try:
            results.append(_process_single(requirement))
        except Exception as exc:
            errors.append({"index": i, "requirement": requirement, "error": str(exc)})

    all_normalized = [r for result in results for r in result["normalized_requirements"]]
    all_test_cases = [tc for result in results for tc in result["test_cases"]]

    return {
        "normalized_requirements": all_normalized,
        "test_cases": all_test_cases,
        "audit_log": {
            "generation_timestamp": datetime.now(timezone.utc).isoformat(),
            "generator_version": "1.0.0",
            "model_reference": "rule-based-v1",
            "errors": errors,
        },
    }
