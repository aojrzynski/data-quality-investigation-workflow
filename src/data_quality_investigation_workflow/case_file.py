"""Investigation case artifact builders and writers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from data_quality_investigation_workflow.trace import (
    DATASET_PROFILE_FILENAME,
    IMPLEMENTED_SCOPE,
    TRACE_FILENAME,
)

if TYPE_CHECKING:
    from data_quality_investigation_workflow.intake import LoadedDataset

CASE_FILENAME = "investigation_case.json"
CASE_VERSION = "0.1"

CASE_AUTHORITY_BOUNDARY = [
    "The investigation case records the reported issue and available run context.",
    "The investigation case does not classify the issue.",
    "The investigation case does not confirm the reported issue.",
    "The investigation case does not identify root cause.",
    "This tool does not approve, fix, certify, or trust a dataset.",
    "Human review remains the final authority.",
]

CASE_NOT_YET_IMPLEMENTED = [
    "issue classification",
    "investigation planning",
    "route selection",
    "deterministic issue checks",
    "evidence ledger",
    "hypothesis tracking",
    "baseline comparison",
    "Markdown investigation report",
    "optional LLM notes",
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
    case_id: str | None = None,
    created_at_utc: str | None = None,
) -> dict[str, Any]:
    """Build an investigation case payload without raw dataset values."""
    output_path = Path(output_dir)
    case_path = output_path / CASE_FILENAME
    trace_path = output_path / TRACE_FILENAME
    dataset_profile_path = profile_path
    if loaded_dataset is not None and dataset_profile_path is None:
        dataset_profile_path = output_path / DATASET_PROFILE_FILENAME

    artifacts = {
        "investigation_case": case_path.as_posix(),
        "dataset_profile": dataset_profile_path.as_posix() if dataset_profile_path else None,
        "investigation_trace": trace_path.as_posix(),
    }

    input_provided = loaded_dataset is not None
    workflow_status = "case_profiled" if input_provided else "case_created"
    workflow_stage = (
        "dataset_profiled_case_created"
        if input_provided
        else "investigation_case_created"
    )

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
            "not_yet_implemented": CASE_NOT_YET_IMPLEMENTED,
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
    )
    case_path.write_text(json.dumps(case, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return case_path


def _issue_payload(issue_statement: str | None) -> dict[str, Any]:
    issue_provided = issue_statement is not None
    payload: dict[str, Any] = {
        "statement": issue_statement,
        "provided": issue_provided,
        "classification_status": "not_classified",
        "classification_note": "Issue classification is not implemented in PR #3.",
    }
    if not issue_provided:
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
