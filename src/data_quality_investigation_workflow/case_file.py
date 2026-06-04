"""Investigation case artifact builders and writers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from data_quality_investigation_workflow.issue_classifier import classify_issue
from data_quality_investigation_workflow.planning import PLAN_FILENAME
from data_quality_investigation_workflow.trace import DATASET_PROFILE_FILENAME, TRACE_FILENAME
from data_quality_investigation_workflow.workflow_scope import IMPLEMENTED_SCOPE, NOT_YET_IMPLEMENTED

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
    if loaded_dataset is not None and dataset_profile_path is None:
        dataset_profile_path = output_path / DATASET_PROFILE_FILENAME

    artifacts = {
        "investigation_case": case_path.as_posix(),
        "dataset_profile": dataset_profile_path.as_posix() if dataset_profile_path else None,
        "investigation_plan": investigation_plan_path.as_posix(),
        "evidence_ledger": evidence_ledger_path.as_posix() if evidence_ledger_path else None,
        "investigation_trace": trace_path.as_posix(),
    }

    input_provided = loaded_dataset is not None
    classification = classify_issue(issue_statement)
    issue_missing = classification["issue_type"] == "missing_issue_statement"
    if issue_missing:
        workflow_status = "plan_not_ready"
        workflow_stage = "missing_issue_statement"
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
    )
    case_path.write_text(json.dumps(case, indent=2, sort_keys=False) + "\n", encoding="utf-8")
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
