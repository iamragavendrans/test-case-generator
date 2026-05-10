"""
Automation skeleton generator.

Converts validated test case dicts into executable Python/pytest stubs so
engineers start with method signatures, docstrings, setup comments, action
steps, and failing assertions — not a blank file.
"""

import re
import textwrap
from dataclasses import dataclass, field
from typing import List


@dataclass
class SkeletonFile:
    filename: str
    language: str
    content: str
    requirement_id: str
    test_count: int


def _slugify(text: str) -> str:
    """Convert arbitrary text to a snake_case Python identifier."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s_]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text[:60] or "test_case"


def _class_name(requirement_id: str, actor: str) -> str:
    """Generate a PascalCase class name from requirement metadata."""
    parts = re.sub(r"[^a-zA-Z0-9]", " ", f"{requirement_id} {actor}").split()
    return "Test" + "".join(p.capitalize() for p in parts if p)


def _method_name(tc: dict) -> str:
    """Derive a descriptive snake_case method name from the test case title."""
    title = tc.get("title", "")
    # Strip "when ... expecting ..." down to the core action
    core = re.sub(r"\bexpecting\b.*", "", title, flags=re.IGNORECASE)
    core = re.sub(r"\bwhen\b", "when", core, flags=re.IGNORECASE)
    slug = _slugify(core)
    test_type = _slugify(tc.get("test_type", ""))
    return f"test_{slug}_{test_type}"[:79]


def _format_steps_as_comments(steps: list) -> str:
    """Render steps list as AAA-commented Python lines."""
    if not steps:
        return "        # TODO: implement test steps\n"
    lines = []
    for i, step in enumerate(steps):
        action = step.get("action", "")
        inter = step.get("expected_intermediate", "")
        # Categorise step position for AAA grouping
        if i == 0:
            lines.append("        # ARRANGE / SETUP")
        elif i == 1:
            lines.append("        # ACT")
        if i == len(steps) - 1 and len(steps) > 2:
            lines.append("        # ASSERT")
        lines.append(f"        # Step {step.get('step_number', i + 1)}: {action}")
        if inter:
            lines.append(f"        #   → Expected: {inter}")
        lines.append(f"        # TODO: implement step {step.get('step_number', i + 1)}")
    return "\n".join(lines)


def _format_test_data(test_data: dict) -> str:
    """Render test_data as an inline dict assignment."""
    inputs = test_data.get("inputs", {}) if isinstance(test_data, dict) else {}
    if not inputs:
        return "        test_data = {}  # TODO: populate with realistic values"
    lines = ["        test_data = {"]
    for k, v in inputs.items():
        lines.append(f'            "{k}": {repr(v)},')
    lines.append("        }")
    return "\n".join(lines)


def generate_pytest_skeleton(
    requirement_id: str,
    requirement_text: str,
    test_cases: list,
    actor: str = "",
    classification: list = None,
) -> SkeletonFile:
    """
    Generate a complete pytest file for one requirement's test cases.

    Args:
        requirement_id: e.g. "REQ-001"
        requirement_text: The original requirement string.
        test_cases: List of validated test case dicts.
        actor: The identified actor from normalization.
        classification: List of classification labels.

    Returns:
        A SkeletonFile with filename, content, and metadata.
    """
    classification = classification or []
    class_nm = _class_name(requirement_id, actor)
    filename = f"test_{_slugify(requirement_id)}.py"

    # Build header
    header = textwrap.dedent(f"""\
        \"\"\"
        Auto-generated test skeleton for {requirement_id}.
        Requirement: {requirement_text[:120]}
        Classification: {', '.join(classification) or 'Functional'}

        IMPORTANT: This file was generated automatically.
        Each test method contains TODO comments for implementation.
        Replace every `assert False` with real assertions.
        \"\"\"

        import pytest


    """)

    # Build class
    class_body_lines = [
        f"class {class_nm}:",
        f'    """',
        f"    Requirement ID : {requirement_id}",
        f"    Source         : {requirement_text[:120]}",
        f'    """',
        "",
    ]

    for tc in test_cases:
        method = _method_name(tc)
        tc_type = tc.get("test_type", "")
        priority = tc.get("priority", "Medium")
        title = tc.get("title", "")
        preconditions = tc.get("preconditions", [])
        steps = tc.get("steps", [])
        expected_result = tc.get("expected_result", "")
        td = tc.get("test_data", {})
        automation = tc.get("automation_feasibility", "Medium")

        # Pytest marker based on type
        markers = []
        if tc_type == "Security":
            markers.append("@pytest.mark.security")
        if tc_type == "Performance":
            markers.append("@pytest.mark.performance")
        if tc_type in ("Edge", "Boundary"):
            markers.append("@pytest.mark.edge_case")
        if tc_type == "Negative":
            markers.append("@pytest.mark.negative")
        if automation == "Low":
            markers.append("@pytest.mark.manual")

        precondition_comments = (
            "\n".join(f"        # Precondition: {p}" for p in preconditions)
            if preconditions else "        # No specific preconditions"
        )

        method_lines = []
        for m in markers:
            method_lines.append(f"    {m}")
        method_lines += [
            f"    def {method}(self):",
            f'        """',
            f"        Type     : {tc_type}",
            f"        Priority : {priority}",
            f"        Title    : {title}",
            f"        Expected : {expected_result[:120]}",
            f'        """',
            precondition_comments,
            _format_test_data(td),
            "",
            _format_steps_as_comments(steps),
            "",
            "        # ASSERT",
            f'        # Expected: {expected_result[:120]}',
            '        assert False, "Test not yet implemented"',
            "",
        ]
        class_body_lines.extend("    " + line if line and not line.startswith("    ") else line
                                 for line in method_lines)
        class_body_lines.append("")

    content = header + "\n".join(class_body_lines)
    return SkeletonFile(
        filename=filename,
        language="python",
        content=content,
        requirement_id=requirement_id,
        test_count=len(test_cases),
    )


def generate_skeletons_for_output(output: dict) -> List[SkeletonFile]:
    """
    Generate one skeleton file per requirement from a pipeline output dict.

    Args:
        output: The dict returned by _process_single() in main.py.

    Returns:
        List of SkeletonFile objects ready to write to disk or return via API.
    """
    skeletons = []
    req_map = {r["requirement_id"]: r for r in output.get("normalized_requirements", [])}
    tc_by_req: dict = {}

    for tc in output.get("test_cases", []):
        rid = tc.get("mapped_requirement_id", "REQ-UNKNOWN")
        tc_by_req.setdefault(rid, []).append(tc)

    for req_id, req in req_map.items():
        tcs = tc_by_req.get(req_id, [])
        if not tcs:
            continue
        norm = req.get("normalized", {})
        skeleton = generate_pytest_skeleton(
            requirement_id=req_id,
            requirement_text=req.get("source_text", ""),
            test_cases=tcs,
            actor=norm.get("actor", "") if isinstance(norm, dict) else "",
            classification=req.get("classification", []),
        )
        skeletons.append(skeleton)

    return skeletons
