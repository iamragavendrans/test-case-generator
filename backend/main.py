"""
FastAPI application for the Test Case Generator API.

End-to-end pipeline:
  Document → Ingestion (multi-format) → Normalization → Classification
  → LLM Generation (Ollama/OpenAI-compat, with rule-based fallback)
  → Output Validation → Coverage Calculation → Automation Skeleton

Endpoints:
  GET  /health           — liveness + LLM availability check
  POST /generate         — full pipeline for a single document/requirement
  POST /batch            — full pipeline for a list of requirements
  POST /skeleton         — generate pytest stubs from a prior /generate response
"""

import sys
import os
import logging

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
from services.coverage import CoverageService
from services.llm_client import LLMClient
from services.skeleton_generator import generate_skeletons_for_output

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Test Case Generator API",
    description=(
        "Multi-layer pipeline: document ingestion → normalization → classification "
        "→ LLM-based generation (with rule-based fallback) → validation → coverage "
        "→ automation skeleton"
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Service singletons ────────────────────────────────────────────────────────

_ingestion = IngestionService()
_normalization = NormalizationService()
_classification = ClassificationService()
_generation = TestCaseGenerationService()
_coverage = CoverageService()
_llm = LLMClient()


# ── Request / Response models ─────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    requirement: str = Field(..., min_length=5, description="Requirement text or document content")
    format_hint: Optional[str] = Field(
        None,
        description="Document format: 'markdown', 'gherkin', 'json', 'openapi', or 'plain_text'",
    )
    use_llm: bool = Field(True, description="Attempt LLM generation before rule-based fallback")


class BatchRequest(BaseModel):
    requirements: List[str] = Field(..., min_items=1)
    format_hint: Optional[str] = None
    use_llm: bool = True


class SkeletonRequest(BaseModel):
    pipeline_output: dict = Field(..., description="The JSON returned by /generate or /batch")


# ── Core pipeline ─────────────────────────────────────────────────────────────

def _tc_to_dict(tc, cls, norm_item) -> dict:
    """Convert a rule-based TestCase object to the standard output dict."""
    return {
        "test_case_id": _generation.generate_test_case_id(tc.requirement_id, tc.test_type[:3].upper()),
        "title": tc.title,
        "mapped_requirement_id": tc.requirement_id,
        "test_type": tc.test_type,
        "preconditions": tc.preconditions,
        "steps": tc.steps,
        "test_data": tc.test_data,
        "expected_result": tc.expected_result,
        "priority": _generation._map_priority(cls.priority_hint, tc.test_type[:3].upper()),
        "automation_feasibility": {"feasible": True, "notes": "Standard test case", "estimated_effort": "Medium"},
        "determinism_seed": _generation.config.determinism_seed,
        "explainability": {
            "generation_template_id": tc.template_id,
            "rules_applied": tc.rules_applied,
            "confidence": norm_item.confidence * 0.9,
            "generated_by": "rule-based",
        },
    }


def _llm_tc_to_dict(tc: dict, req_id: str, classification, norm_item) -> dict:
    """Normalise an LLM-generated test case dict into the standard output format."""
    return {
        "test_case_id": _generation.generate_test_case_id(req_id, tc.get("test_type", "POS")[:3].upper()),
        "title": tc.get("title", ""),
        "mapped_requirement_id": req_id,
        "test_type": tc.get("test_type", "Positive"),
        "preconditions": tc.get("preconditions", []),
        "steps": tc.get("steps", []),
        "test_data": tc.get("test_data", {"inputs": {}}),
        "expected_result": tc.get("expected_result", ""),
        "priority": tc.get("priority", "Medium"),
        "automation_feasibility": {
            "feasible": tc.get("automation_feasibility", "Medium") != "Low",
            "notes": f"Automation feasibility: {tc.get('automation_feasibility', 'Medium')}",
            "estimated_effort": tc.get("automation_feasibility", "Medium"),
        },
        "determinism_seed": "llm-generated",
        "explainability": {
            "generation_template_id": "llm-prompt-v1",
            "rules_applied": ["llm:structured-prompt", "validation:schema-check"],
            "confidence": norm_item.confidence * 0.95,
            "generated_by": "llm",
        },
    }


def _process_single(text: str, format_hint: Optional[str] = None, use_llm: bool = True) -> dict:
    """Full pipeline for one document/requirement text."""
    # Layer 1 — Ingestion
    ingest_result = _ingestion.ingest(text, format_hint=format_hint)
    clean_text = ingest_result.chunks[0] if ingest_result.chunks else text

    # Layer 2 — Normalization
    norm_results = _normalization.normalize(clean_text)

    all_tc_dicts: List[dict] = []
    all_normalized: List[dict] = []
    llm_used = False

    for norm in norm_results:
        norm_dict = norm.normalized.__dict__ if hasattr(norm.normalized, "__dict__") else norm.normalized
        req_id = norm.provenance.get("requirement_id", "REQ-UNKNOWN")

        # Layer 3 — Classification
        classification = _classification.classify(norm.original_text, norm_dict)
        cls_types = [c.value for c in [classification.primary_class] + classification.secondary_classes]

        # Layer 4 — Generation (LLM first, rule-based fallback)
        if use_llm:
            llm_tcs, used = _llm.generate_test_cases(
                requirement_text=norm.original_text,
                requirement_type=classification.primary_class.value,
                classification=cls_types,
                actor=norm_dict.get("actor", ""),
                action=norm_dict.get("action", ""),
                conditions=norm_dict.get("conditions", []),
                expected_outcome=norm_dict.get("expected_outcome", ""),
                document_type=ingest_result.document_format.value,
            )
            if used:
                llm_used = True
                tc_dicts = [_llm_tc_to_dict(tc, req_id, classification, norm) for tc in llm_tcs]
                all_tc_dicts.extend(tc_dicts)
                all_normalized.append(_build_normalized_entry(norm, norm_dict, classification, req_id))
                continue  # skip rule-based for this requirement

        # Rule-based generation (fallback or LLM disabled)
        generated = _generation.generate(
            normalized_req=norm_dict,
            classification={"types": cls_types, "priority_hint": classification.priority_hint},
            ambiguity={
                "is_ambiguous": norm.is_ambiguous,
                "issues": [i.description for i in norm.ambiguity_issues] if norm.ambiguity_issues else [],
                "clarifying_questions": norm.clarifying_questions,
            } if norm.is_ambiguous else None,
        )
        all_tc_dicts.extend(_tc_to_dict(tc, classification, norm) for tc in generated)
        all_normalized.append(_build_normalized_entry(norm, norm_dict, classification, req_id))

    # Layer 5 — Coverage
    behaviors = [
        {"behavior_id": f"{r['requirement_id']}-B01", "requirement_id": r["requirement_id"]}
        for r in all_normalized
    ]
    coverage_result = _coverage.calculate(all_tc_dicts, all_normalized, behaviors)

    return {
        "normalized_requirements": all_normalized,
        "test_cases": all_tc_dicts,
        "coverage_summary": {
            "overall_coverage": coverage_result.overall_coverage,
            "requirement_coverage": coverage_result.requirement_coverage,
            "gaps_detected": coverage_result.gaps_detected,
            "dimension_coverage": coverage_result.dimension_coverage,
        },
        "audit_log": {
            "generation_timestamp": datetime.now(timezone.utc).isoformat(),
            "generator_version": "2.0.0",
            "model_reference": "llm" if llm_used else "rule-based-v1",
            "llm_used": llm_used,
            "document_format": ingest_result.document_format.value,
            "sanitization_warnings": ingest_result.sanitization_warnings,
        },
    }


def _build_normalized_entry(norm, norm_dict, classification, req_id) -> dict:
    return {
        "requirement_id": req_id,
        "source_text": norm.original_text,
        "normalized": norm_dict,
        "classification": [classification.primary_class.value] + [c.value for c in classification.secondary_classes],
        "priority_hint": classification.priority_hint,
        "ambiguity": {
            "is_ambiguous": norm.is_ambiguous,
            "issues": [i.description for i in norm.ambiguity_issues] if norm.ambiguity_issues else [],
            "clarifying_questions": norm.clarifying_questions,
        },
        "provenance": norm.provenance,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "llm_available": _llm.is_available(),
        "llm_model": os.getenv("LLM_MODEL", "llama3"),
        "llm_base": os.getenv("LLM_API_BASE", "http://localhost:11434"),
    }


@app.post("/generate")
def generate(req: GenerateRequest):
    """Full pipeline: document → normalized requirements + test cases + coverage."""
    try:
        return _process_single(req.requirement, format_hint=req.format_hint, use_llm=req.use_llm)
    except Exception as exc:
        logger.exception("Pipeline error")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/batch")
def batch(req: BatchRequest):
    """Run the pipeline for each requirement; combine results."""
    results = []
    errors = []
    for i, requirement in enumerate(req.requirements):
        try:
            results.append(_process_single(requirement, format_hint=req.format_hint, use_llm=req.use_llm))
        except Exception as exc:
            errors.append({"index": i, "requirement": requirement[:120], "error": str(exc)})

    all_normalized = [r for res in results for r in res["normalized_requirements"]]
    all_tcs = [tc for res in results for tc in res["test_cases"]]
    llm_used_any = any(res["audit_log"].get("llm_used") for res in results)

    return {
        "normalized_requirements": all_normalized,
        "test_cases": all_tcs,
        "audit_log": {
            "generation_timestamp": datetime.now(timezone.utc).isoformat(),
            "generator_version": "2.0.0",
            "model_reference": "llm" if llm_used_any else "rule-based-v1",
            "errors": errors,
        },
    }


@app.post("/skeleton")
def skeleton(req: SkeletonRequest):
    """Generate executable pytest stubs from a prior /generate or /batch response."""
    try:
        files = generate_skeletons_for_output(req.pipeline_output)
        return {
            "files": [
                {
                    "filename": f.filename,
                    "language": f.language,
                    "requirement_id": f.requirement_id,
                    "test_count": f.test_count,
                    "content": f.content,
                }
                for f in files
            ],
            "total_files": len(files),
            "total_tests": sum(f.test_count for f in files),
        }
    except Exception as exc:
        logger.exception("Skeleton generation error")
        raise HTTPException(status_code=500, detail=str(exc))
