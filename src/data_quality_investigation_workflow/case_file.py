"""Investigation case artifact builders.

The case file is the anchor for a run. It records the reported issue, local
input references, artifact paths, workflow status, and authority boundaries. It
does not record conclusions: a report or suspicion is useful context, but it is
not evidence that the issue is confirmed or that root cause is known.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from data_quality_investigation_workflow.issue_classifier import classify_issue
from data_quality_investigation_workflow.planning import PLAN_FILENAME
from data_quality_investigation_workflow.reporting import REPORT_FILENAME
from data_quality_investigation_workflow.baseline import (
    BASELINE_COMPARISON_FILENAME,
    BASELINE_PROFILE_FILENAME,
)
from data_quality_investigation_workflow.trace import (
    DATASET_PROFILE_FILENAME,
    TRACE_FILENAME,
)
from data_quality_investigation_workflow.workflow_scope import (
    IMPLEMENTED_SCOPE,
    NOT_YET_IMPLEMENTED,
)

if TYPE_CHECKING:
    from data_quality_investigation_workflow.intake import LoadedDataset

CASE_FILENAME = "investigation_case.json"
CASE_VERSION = "0.1"

CASE_AUTHORITY_BOUNDARY = [
    "The investigation case records the reported issue and available run context.",
    "Issue classification is deterministic and used only for planning.",
    "The investigation case does not confirm the reported issue.",
    "The investigation case does not identify root cause.",
    "This tool does not approve, fix, certify, or trust a dataset.",
    "Human review remains the final authority.",
]

MISSING_ISSUE_NOTE = (
    "No issue statement was provided. Later investigation steps will be more useful "
    "when an issue statement is supplied."
)

NO_INPUT_NOTE = "No input dataset was supplied, loaded, or profiled for this case."


def build_investigation_case(
    *,
    issue_statement: str | None,
    output_dir: str | Path,
    loaded_dataset: "LoadedDataset" | None = None,
    profile_path: Path | None = None,
    plan_path: Path | None = None,
    ledger_path: Path | None = None,
    baseline_dataset: "LoadedDataset" | None = None,
    baseline_profile_path: Path | None = None,
    baseline_comparison_path: Path | None = None,
    hypothesis_tracker_path: Path | None = None,
    findings_path: Path | None = None,
    report_path: Path | None = None,
    llm_safe_input_summary_path: Path | None = None,
    llm_notes_path: Path | None = None,
    llm_notes_markdown_path: Path | None = None,
    case_id: str | None = None,
    created_at_utc: str | None = None,
) -> dict[str, Any]:
    """Build an investigation case payload without raw dataset values."""
    output_path = Path(output_dir)
    case_path = output_path / CASE_FILENAME
    trace_path = output_path / TRACE_FILENAME
    investigation_plan_path = plan_path or output_path / PLAN_FILENAME
    evidence_ledger_path = ledger_path
    dataset_profile_path = profile_path
    # The case names expected artifacts even before every downstream stage has
    # finished, so reviewers can see the intended chain for the run.
    if loaded_dataset is not None and dataset_profile_path is None:
        dataset_profile_path = output_path / DATASET_PROFILE_FILENAME
    baseline_profile_path = baseline_profile_path or (
        output_path / BASELINE_PROFILE_FILENAME
        if baseline_dataset is not None
        else None
    )
    baseline_comparison_path = baseline_comparison_path or (
        output_path / BASELINE_COMPARISON_FILENAME
        if baseline_dataset is not None
        else None
    )
    if report_path is None and findings_path is not None:
        report_path = output_path / REPORT_FILENAME

    artifacts = {
        "investigation_case": case_path.as_posix(),
        "dataset_profile": dataset_profile_path.as_posix()
        if dataset_profile_path
        else None,
        "investigation_plan": investigation_plan_path.as_posix(),
        "evidence_ledger": evidence_ledger_path.as_posix()
        if evidence_ledger_path
        else None,
        "investigation_trace": trace_path.as_posix(),
    }
    # Baseline references are included only when a baseline was supplied; current
    # and baseline files are separate review inputs, not interchangeable evidence.
    if baseline_profile_path is not None:
        artifacts["baseline_profile"] = baseline_profile_path.as_posix()
    if baseline_comparison_path is not None:
        artifacts["baseline_comparison"] = baseline_comparison_path.as_posix()
    if hypothesis_tracker_path is not None:
        artifacts["hypothesis_tracker"] = hypothesis_tracker_path.as_posix()
    if findings_path is not None:
        artifacts["investigation_findings"] = findings_path.as_posix()
    if report_path is not None:
        artifacts["investigation_report"] = report_path.as_posix()
    # Optional LLM artifacts are named after the deterministic run exists. Their
    # presence says notes were requested, not that the notes are authoritative.
    if llm_safe_input_summary_path is not None:
        artifacts["llm_safe_input_summary"] = llm_safe_input_summary_path.as_posix()
    if llm_notes_path is not None:
        artifacts["llm_investigation_notes"] = llm_notes_path.as_posix()
    if llm_notes_markdown_path is not None:
        artifacts["llm_investigation_notes_markdown"] = (
            llm_notes_markdown_path.as_posix()
        )

    input_provided = loaded_dataset is not None
    classification = classify_issue(issue_statement)
    issue_missing = classification["issue_type"] == "missing_issue_statement"
    # A missing issue keeps the run in planning mode because the workflow is
    # issue-led; without a concern, route-specific evidence would be misleading.
    if issue_missing:
        workflow_status = "plan_not_ready"
        workflow_stage = "missing_issue_statement"
    elif llm_safe_input_summary_path is not None and llm_notes_path is not None:
        workflow_status = "llm_notes_written"
        workflow_stage = "optional_llm_notes_created"
    elif (
        input_provided
        and evidence_ledger_path is not None
        and hypothesis_tracker_path is not None
        and findings_path is not None
        and report_path is not None
    ):
        workflow_status = "report_written"
        workflow_stage = "markdown_report_created"
    elif (
        input_provided
        and evidence_ledger_path is not None
        and hypothesis_tracker_path is not None
        and findings_path is not None
    ):
        workflow_status = "findings_summarized"
        workflow_stage = "hypotheses_and_findings_created"
    elif input_provided and evidence_ledger_path is not None:
        workflow_status = "evidence_recorded"
        workflow_stage = "deterministic_checks_recorded"
    elif input_provided:
        workflow_status = "profiled_planned"
        workflow_stage = "dataset_profiled_plan_created"
    else:
        workflow_status = "planned"
        workflow_stage = "investigation_plan_created"

    return {
        "artifact_type": "investigation_case",
        "case_version": CASE_VERSION,
        "case_id": case_id or f"case-{uuid4()}",
        "created_at_utc": created_at_utc or datetime.now(UTC).isoformat(),
        "issue": _issue_payload(issue_statement),
        "workflow": {
            "status": workflow_status,
            "stage": workflow_stage,
            "implemented_scope": IMPLEMENTED_SCOPE,
            "not_yet_implemented": NOT_YET_IMPLEMENTED,
        },
        "dataset_reference": _dataset_reference(
            loaded_dataset=loaded_dataset,
            profile_path=dataset_profile_path,
        ),
        "baseline_reference": _baseline_reference(
            baseline_dataset=baseline_dataset,
            baseline_profile_path=baseline_profile_path,
            baseline_comparison_path=baseline_comparison_path,
        ),
        "artifacts": artifacts,
        "authority_boundary": CASE_AUTHORITY_BOUNDARY,
    }


def write_investigation_case(
    *,
    output_dir: str | Path,
    issue_statement: str | None,
    loaded_dataset: "LoadedDataset" | None = None,
    profile_path: Path | None = None,
    plan_path: Path | None = None,
    ledger_path: Path | None = None,
    baseline_dataset: "LoadedDataset" | None = None,
    baseline_profile_path: Path | None = None,
    baseline_comparison_path: Path | None = None,
    hypothesis_tracker_path: Path | None = None,
    findings_path: Path | None = None,
    report_path: Path | None = None,
    llm_safe_input_summary_path: Path | None = None,
    llm_notes_path: Path | None = None,
    llm_notes_markdown_path: Path | None = None,
) -> Path:
    """Create the output directory and write the investigation case artifact."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    case_path = output_path / CASE_FILENAME
    case = build_investigation_case(
        issue_statement=issue_statement,
        output_dir=output_path,
        loaded_dataset=loaded_dataset,
        profile_path=profile_path,
        plan_path=plan_path,
        ledger_path=ledger_path,
        baseline_dataset=baseline_dataset,
        baseline_profile_path=baseline_profile_path,
        baseline_comparison_path=baseline_comparison_path,
        hypothesis_tracker_path=hypothesis_tracker_path,
        findings_path=findings_path,
        report_path=report_path,
        llm_safe_input_summary_path=llm_safe_input_summary_path,
        llm_notes_path=llm_notes_path,
        llm_notes_markdown_path=llm_notes_markdown_path,
    )
    case_path.write_text(
        json.dumps(case, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    return case_path


def _issue_payload(issue_statement: str | None) -> dict[str, Any]:
    classification = classify_issue(issue_statement)
    payload: dict[str, Any] = {
        "statement": issue_statement,
        "provided": classification["provided"],
        "classification_status": classification["classification_status"],
        "issue_type": classification["issue_type"],
        "selected_route": classification["selected_route"],
        "classification_note": "Issue classification is deterministic and used only for planning.",
    }
    if not classification["provided"]:
        # The missing-issue note explains why the case exists but cannot yet
        # become a full investigation.
        payload["missing_issue_note"] = MISSING_ISSUE_NOTE
    return payload


def _dataset_reference(
    *,
    loaded_dataset: "LoadedDataset" | None,
    profile_path: Path | None,
) -> dict[str, Any]:
    if loaded_dataset is None:
        return {
            "input_provided": False,
            "file_name": None,
            "file_extension": None,
            "sheet_name": None,
            "row_count": None,
            "column_count": None,
            "profile_artifact": None,
            "note": NO_INPUT_NOTE,
        }

    return {
        "input_provided": True,
        "file_name": loaded_dataset.file_name,
        "file_extension": loaded_dataset.file_extension,
        "sheet_name": loaded_dataset.sheet_name,
        "row_count": loaded_dataset.row_count,
        "column_count": loaded_dataset.column_count,
        "profile_artifact": profile_path.as_posix() if profile_path else None,
    }


def _baseline_reference(
    *,
    baseline_dataset: "LoadedDataset" | None,
    baseline_profile_path: Path | None,
    baseline_comparison_path: Path | None,
) -> dict[str, Any]:
    if baseline_dataset is None:
        return {
            "input_provided": False,
            "file_name": None,
            "file_extension": None,
            "sheet_name": None,
            "row_count": None,
            "column_count": None,
            "baseline_profile_artifact": None,
            "baseline_comparison_artifact": None,
        }

    return {
        "input_provided": True,
        "file_name": baseline_dataset.file_name,
        "file_extension": baseline_dataset.file_extension,
        "sheet_name": baseline_dataset.sheet_name,
        "row_count": baseline_dataset.row_count,
        "column_count": baseline_dataset.column_count,
        "baseline_profile_artifact": (
            baseline_profile_path.as_posix() if baseline_profile_path else None
        ),
        "baseline_comparison_artifact": (
            baseline_comparison_path.as_posix() if baseline_comparison_path else None
        ),
    }
