"""Optional bounded LLM investigation notes artifacts."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from data_quality_investigation_workflow.errors import WorkflowUserError
from data_quality_investigation_workflow.llm_client import OpenAIResponsesNotesClient
from data_quality_investigation_workflow.llm_prompt import build_llm_notes_prompt

DEFAULT_LLM_MODEL = os.environ.get("DQIW_LLM_MODEL", "gpt-5.5")
LLM_SAFE_INPUT_SUMMARY_FILENAME = "llm_safe_input_summary.json"
LLM_NOTES_JSON_FILENAME = "llm_investigation_notes.json"
LLM_NOTES_MARKDOWN_FILENAME = "llm_investigation_notes.md"
SUMMARY_VERSION = "0.1"
NOTES_VERSION = "0.1"
MAX_LIST_ITEMS = 8
MAX_REVIEW_SUMMARY_CHARS = 1000
MAX_LIST_ITEM_CHARS = 300
REQUIRED_NOTE_KEYS = [
    "review_summary",
    "suggested_follow_up_questions",
    "suggested_human_checks",
    "communication_notes",
    "limitations_to_keep_visible",
]
FORBIDDEN_TERMS = [
    "raw_rows",
    "sample_rows",
    "sampled_rows",
    "first_rows",
    "last_rows",
    "example_values",
    "examples",
    "top_values",
    "distinct_values",
    "value_preview",
    "value_previews",
    "raw_failing_records",
    "row_numbers",
    "duplicated_values",
    "category_labels",
    "full_distribution",
    "raw_values",
    "generated_code",
    "avery@example.test",
    "CUST-001",
    "root cause identified",
    "issue confirmed",
    "proved",
    "approved",
    "certified",
    "production-ready",
    "compliant verdict",
]
SAFE_INPUT_SAFETY_BOUNDARY = [
    "This summary contains aggregate artifact summaries only.",
    "It does not include raw rows, sampled rows, example values, top values, distinct value lists, duplicated values, category labels, full distributions, row numbers, or raw failing records.",
]
LLM_INSTRUCTION_BOUNDARY = [
    "The LLM may suggest review notes and follow-up questions.",
    "The LLM must not identify root cause.",
    "The LLM must not approve, certify, trust, fix, or make compliance/privacy/legal verdicts.",
    "The LLM output is non-authoritative.",
]
LLM_AUTHORITY_BOUNDARY = [
    "These notes are optional and non-authoritative.",
    "These notes are generated from safe aggregate artifacts only.",
    "These notes do not identify root cause.",
    "These notes do not approve, certify, fix, trust, or make legal/compliance/privacy/governance verdicts.",
    "Human review remains the final authority.",
]


class NotesClient(Protocol):
    def create_notes(
        self,
        *,
        model: str,
        prompt: str,
        max_output_tokens: int | None = None,
    ) -> str: ...


def generate_llm_notes(
    *,
    output_dir: Path,
    model: str,
    artifacts: dict[str, str | None],
    investigation_case: dict[str, Any],
    dataset_profile: dict[str, Any],
    evidence_ledger: dict[str, Any],
    hypothesis_tracker: dict[str, Any],
    investigation_findings: dict[str, Any],
    baseline_profile: dict[str, Any] | None = None,
    baseline_comparison: dict[str, Any] | None = None,
    client: NotesClient | None = None,
    timeout: float | None = None,
    max_output_tokens: int | None = None,
) -> dict[str, Path | str | None]:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_summary_path = output_dir / LLM_SAFE_INPUT_SUMMARY_FILENAME
    notes_json_path = output_dir / LLM_NOTES_JSON_FILENAME
    notes_markdown_path = output_dir / LLM_NOTES_MARKDOWN_FILENAME
    source_artifacts = _source_artifacts(artifacts)
    safe_summary = build_safe_input_summary(
        source_artifacts=source_artifacts,
        investigation_case=investigation_case,
        dataset_profile=dataset_profile,
        evidence_ledger=evidence_ledger,
        hypothesis_tracker=hypothesis_tracker,
        investigation_findings=investigation_findings,
        baseline_profile=baseline_profile,
        baseline_comparison=baseline_comparison,
    )
    _write_json(safe_summary_path, safe_summary)
    prompt = build_llm_notes_prompt(safe_summary)
    notes_client = client or OpenAIResponsesNotesClient(timeout=timeout)
    try:
        raw_notes = notes_client.create_notes(
            model=model,
            prompt=prompt,
            max_output_tokens=max_output_tokens,
        )
    except WorkflowUserError:
        raise
    except Exception as error:
        raise WorkflowUserError(f"LLM notes request failed: {error}") from error

    notes, errors = parse_and_validate_notes(raw_notes)
    if errors:
        failure_artifact = build_notes_failure_artifact(
            model=model,
            input_summary_artifact=safe_summary_path,
            source_artifacts=source_artifacts,
            errors=errors,
        )
        _write_json(notes_json_path, failure_artifact)
        return {
            "status": "failed_validation",
            "safe_input_summary_path": safe_summary_path,
            "notes_json_path": notes_json_path,
            "notes_markdown_path": None,
        }

    notes_artifact = build_notes_success_artifact(
        model=model,
        input_summary_artifact=safe_summary_path,
        source_artifacts=source_artifacts,
        notes=notes,
    )
    _write_json(notes_json_path, notes_artifact)
    notes_markdown_path.write_text(render_notes_markdown(notes_artifact), encoding="utf-8")
    return {
        "status": "completed",
        "safe_input_summary_path": safe_summary_path,
        "notes_json_path": notes_json_path,
        "notes_markdown_path": notes_markdown_path,
    }


def build_safe_input_summary(
    *,
    source_artifacts: dict[str, str],
    investigation_case: dict[str, Any],
    dataset_profile: dict[str, Any],
    evidence_ledger: dict[str, Any],
    hypothesis_tracker: dict[str, Any],
    investigation_findings: dict[str, Any],
    baseline_profile: dict[str, Any] | None = None,
    baseline_comparison: dict[str, Any] | None = None,
) -> dict[str, Any]:
    issue = investigation_case.get("issue", {})
    dataset_ref = investigation_case.get("dataset_reference", {})
    baseline_ref = investigation_case.get("baseline_reference", {})
    summary = {
        "artifact_type": "llm_safe_input_summary",
        "summary_version": SUMMARY_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_artifacts": source_artifacts,
        "issue": {
            "statement": issue.get("statement"),
            "issue_type": issue.get("issue_type"),
            "selected_route": issue.get("selected_route"),
        },
        "run_context": {
            "current_file_name": dataset_ref.get("file_name"),
            "current_row_count": dataset_ref.get("row_count") or dataset_profile.get("row_count"),
            "current_column_count": dataset_ref.get("column_count") or dataset_profile.get("column_count"),
            "baseline_available": baseline_profile is not None or baseline_comparison is not None,
            "baseline_file_name": baseline_ref.get("file_name"),
            "baseline_row_count": baseline_ref.get("row_count") or (baseline_profile or {}).get("row_count"),
            "baseline_column_count": baseline_ref.get("column_count") or (baseline_profile or {}).get("column_count"),
        },
        "evidence_summary": _evidence_summary(evidence_ledger),
        "hypothesis_summary": _hypothesis_summary(hypothesis_tracker),
        "findings_summary": _findings_summary(investigation_findings),
        "safety_boundary": SAFE_INPUT_SAFETY_BOUNDARY,
        "llm_instruction_boundary": LLM_INSTRUCTION_BOUNDARY,
    }
    _assert_safe_serialized(summary)
    return summary


def parse_and_validate_notes(raw_notes: str) -> tuple[dict[str, Any], list[str]]:
    try:
        parsed = json.loads(raw_notes)
    except json.JSONDecodeError:
        return {}, ["LLM response was not valid JSON."]
    if not isinstance(parsed, dict):
        return {}, ["LLM response JSON must be an object."]

    errors: list[str] = []
    extra_keys = sorted(set(parsed) - set(REQUIRED_NOTE_KEYS))
    if extra_keys:
        errors.append("LLM response included keys outside the required schema.")
    missing_keys = [key for key in REQUIRED_NOTE_KEYS if key not in parsed]
    if missing_keys:
        errors.append("LLM response was missing required keys.")

    notes: dict[str, Any] = {}
    review_summary = parsed.get("review_summary")
    if not isinstance(review_summary, str):
        errors.append("review_summary must be a string.")
    elif len(review_summary) > MAX_REVIEW_SUMMARY_CHARS:
        errors.append("review_summary exceeded the length limit.")
    else:
        notes["review_summary"] = review_summary

    for key in REQUIRED_NOTE_KEYS[1:]:
        value = parsed.get(key)
        if not isinstance(value, list):
            errors.append(f"{key} must be a list of strings.")
            continue
        if len(value) > MAX_LIST_ITEMS:
            errors.append(f"{key} exceeded the item limit.")
            continue
        clean_items: list[str] = []
        for item in value:
            if not isinstance(item, str):
                errors.append(f"{key} must contain only strings.")
                break
            if len(item) > MAX_LIST_ITEM_CHARS:
                errors.append(f"{key} contained an item over the length limit.")
                break
            clean_items.append(item)
        else:
            notes[key] = clean_items

    if _contains_forbidden_terms(parsed):
        errors.append("LLM response included blocked raw-value or verdict language.")
    return (notes if not errors else {}, errors)


def build_notes_success_artifact(
    *,
    model: str,
    input_summary_artifact: Path,
    source_artifacts: dict[str, str],
    notes: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": "llm_investigation_notes",
        "notes_version": NOTES_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "model": model,
        "llm_status": "completed",
        "input_summary_artifact": input_summary_artifact.as_posix(),
        "source_artifacts": source_artifacts,
        "notes": notes,
        "validation": {
            "status": "passed",
            "checks": [
                "valid_json",
                "required_keys_present",
                "forbidden_terms_absent",
                "raw_value_markers_absent",
            ],
        },
        "authority_boundary": LLM_AUTHORITY_BOUNDARY,
    }


def build_notes_failure_artifact(
    *,
    model: str,
    input_summary_artifact: Path,
    source_artifacts: dict[str, str],
    errors: list[str],
) -> dict[str, Any]:
    return {
        "artifact_type": "llm_investigation_notes",
        "notes_version": NOTES_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "model": model,
        "llm_status": "failed_validation",
        "input_summary_artifact": input_summary_artifact.as_posix(),
        "source_artifacts": source_artifacts,
        "notes": None,
        "validation": {
            "status": "failed",
            "errors": list(errors),
        },
        "authority_boundary": LLM_AUTHORITY_BOUNDARY,
    }


def render_notes_markdown(notes_artifact: dict[str, Any]) -> str:
    notes = notes_artifact["notes"]
    lines = [
        "# Optional LLM Investigation Notes",
        "",
        "These notes are optional and non-authoritative.",
        "They are generated from safe aggregate artifacts only.",
        "They do not identify root cause and do not approve, certify, fix, trust, or make legal/compliance/privacy/governance verdicts.",
        "Human review remains the final authority.",
        "",
        "## Review summary",
        "",
        str(notes["review_summary"]),
        "",
    ]
    sections = [
        ("Suggested follow-up questions", "suggested_follow_up_questions"),
        ("Suggested human checks", "suggested_human_checks"),
        ("Communication notes", "communication_notes"),
        ("Limitations to keep visible", "limitations_to_keep_visible"),
    ]
    for title, key in sections:
        lines.extend([f"## {title}", ""])
        lines.extend(_markdown_list(notes[key]))
        lines.append("")
    lines.extend(["## Source artifacts", ""])
    for artifact_name, artifact_path in notes_artifact["source_artifacts"].items():
        lines.append(f"- `{artifact_name}`: `{artifact_path}`")
    lines.append("")
    return "\n".join(lines)


def _evidence_summary(evidence_ledger: dict[str, Any]) -> dict[str, Any]:
    execution = evidence_ledger.get("execution", {})
    items = []
    for item in evidence_ledger.get("evidence_items", []):
        items.append(
            {
                "evidence_id": item.get("evidence_id"),
                "check_id": item.get("check_id"),
                "signal": item.get("signal"),
                "signal_strength": item.get("signal_strength"),
                "related_columns": item.get("related_columns", []),
                "summary": item.get("summary"),
            }
        )
    return {
        "evidence_item_count": execution.get("evidence_item_count", len(items)),
        "checks_executed_count": execution.get("checks_executed_count"),
        "checks_not_run_count": execution.get("checks_not_run_count"),
        "evidence_items": items,
    }


def _hypothesis_summary(hypothesis_tracker: dict[str, Any]) -> dict[str, Any]:
    counts = hypothesis_tracker.get("hypothesis_summary", {})
    hypotheses = []
    for hypothesis in hypothesis_tracker.get("hypotheses", []):
        hypotheses.append(
            {
                "hypothesis_id": hypothesis.get("hypothesis_id"),
                "status": hypothesis.get("status"),
                "signal_level": hypothesis.get("signal_level"),
                "statement": hypothesis.get("statement"),
                "supporting_evidence_ids": hypothesis.get("supporting_evidence_ids", []),
                "contradicting_evidence_ids": hypothesis.get("contradicting_evidence_ids", []),
                "inconclusive_evidence_ids": hypothesis.get("inconclusive_evidence_ids", []),
            }
        )
    return {
        "supported_by_evidence": counts.get("supported_by_evidence", 0),
        "not_supported_by_evidence": counts.get("not_supported_by_evidence", 0),
        "unclear": counts.get("unclear", 0),
        "not_assessed": counts.get("not_assessed", 0),
        "hypotheses": hypotheses,
    }


def _findings_summary(investigation_findings: dict[str, Any]) -> dict[str, Any]:
    summary = investigation_findings.get("summary", {})
    return {
        "finding_status": investigation_findings.get("finding_status"),
        "supported_signal_count": summary.get("supported_signal_count", 0),
        "not_supported_signal_count": summary.get("not_supported_signal_count", 0),
        "unclear_item_count": len(investigation_findings.get("unclear_items", [])),
        "recommended_human_checks": investigation_findings.get("recommended_human_checks", []),
    }


def _source_artifacts(artifacts: dict[str, str | None]) -> dict[str, str]:
    return {key: value for key, value in artifacts.items() if value is not None}


def _markdown_list(items: list[str]) -> list[str]:
    if not items:
        return ["- None supplied."]
    return [f"- {item}" for item in items]


def _contains_forbidden_terms(value: Any) -> bool:
    serialized = json.dumps(value, sort_keys=True)
    lower_serialized = serialized.lower()
    return any(term.lower() in lower_serialized for term in FORBIDDEN_TERMS)


def _assert_safe_serialized(value: Any) -> None:
    if _contains_forbidden_terms(value):
        raise WorkflowUserError("LLM safe input summary contained blocked unsafe content.")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
