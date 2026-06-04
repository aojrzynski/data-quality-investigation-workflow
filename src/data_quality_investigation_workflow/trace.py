"""Investigation trace artifact builders and writers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from data_quality_investigation_workflow import __version__
from data_quality_investigation_workflow.issue_classifier import classify_issue
from data_quality_investigation_workflow.workflow_scope import (
    AUTHORITY_BOUNDARY,
    IMPLEMENTED_SCOPE,
    NOT_YET_IMPLEMENTED,
)

if TYPE_CHECKING:
    from data_quality_investigation_workflow.intake import LoadedDataset

TOOL_NAME = "Data Quality Investigation Workflow"
TRACE_FILENAME = "investigation_trace.json"
DATASET_PROFILE_FILENAME = "dataset_profile.json"


def build_investigation_trace(
    *,
    issue_statement: str | None,
    trace_path: Path,
    case_path: Path,
    plan_path: Path,
    loaded_dataset: "LoadedDataset" | None = None,
    profile_path: Path | None = None,
    ledger_path: Path | None = None,
    baseline_dataset: "LoadedDataset" | None = None,
    baseline_profile_path: Path | None = None,
    baseline_comparison_path: Path | None = None,
    baseline_comparison_metadata: dict[str, Any] | None = None,
    evidence_metadata: dict[str, Any] | None = None,
    hypothesis_tracker_path: Path | None = None,
    findings_path: Path | None = None,
    hypothesis_metadata: dict[str, Any] | None = None,
    findings_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an investigation trace payload with concise route and evidence metadata."""
    classification = classify_issue(issue_statement)
    input_provided = loaded_dataset is not None
    issue_missing = classification["issue_type"] == "missing_issue_statement"
    if hypothesis_metadata is not None and findings_metadata is not None and not issue_missing:
        status = "findings_summarized"
        stage = "hypotheses_and_findings_created"
    elif evidence_metadata is not None and ledger_path is not None and not issue_missing:
        status = "evidence_recorded"
        stage = "deterministic_checks_recorded"
    elif issue_missing:
        status = "plan_not_ready"
        stage = "missing_issue_statement"
    elif input_provided:
        status = "profiled_planned"
        stage = "dataset_profiled_plan_created"
    else:
        status = "planned"
        stage = "investigation_plan_created"

    payload: dict[str, Any] = {
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": status,
        "stage": stage,
        "run_timestamp_utc": datetime.now(UTC).isoformat(),
        "issue_statement": issue_statement,
        "planning": {
            "classification_status": classification["classification_status"],
            "issue_type": classification["issue_type"],
            "route_name": classification["selected_route"],
            "plan_artifact": plan_path.as_posix(),
        },
        "implemented_scope": IMPLEMENTED_SCOPE,
        "not_yet_implemented": NOT_YET_IMPLEMENTED,
        "artifacts": _artifacts(
            case_path=case_path,
            profile_path=profile_path,
            plan_path=plan_path,
            ledger_path=ledger_path,
            trace_path=trace_path,
            baseline_profile_path=baseline_profile_path,
            baseline_comparison_path=baseline_comparison_path,
            hypothesis_tracker_path=hypothesis_tracker_path,
            findings_path=findings_path,
        ),
        "authority_boundary": AUTHORITY_BOUNDARY,
    }
    if loaded_dataset is not None:
        payload["dataset"] = {
            "input_file_name": loaded_dataset.file_name,
            "file_extension": loaded_dataset.file_extension,
            "sheet_name": loaded_dataset.sheet_name,
            "row_count": loaded_dataset.row_count,
            "column_count": loaded_dataset.column_count,
        }
    if baseline_dataset is not None:
        payload["baseline"] = {
            "available": True,
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
    else:
        payload["baseline"] = {
            "available": False,
            "baseline_profile_artifact": None,
            "baseline_comparison_artifact": None,
        }
    if baseline_comparison_metadata is not None:
        payload["baseline_comparison"] = {
            "available": True,
            "comparison_signal_count": int(
                baseline_comparison_metadata.get("comparison_signal_count", 0)
            ),
            "compared_column_count": int(
                baseline_comparison_metadata.get("compared_column_count", 0)
            ),
        }
    if evidence_metadata is not None:
        payload["evidence"] = {
            "checks_executed_count": int(evidence_metadata.get("checks_executed_count", 0)),
            "evidence_item_count": int(evidence_metadata.get("evidence_item_count", 0)),
            "checks_not_run_count": int(evidence_metadata.get("checks_not_run_count", 0)),
            "route_name": classification["selected_route"],
            "issue_type": classification["issue_type"],
            "ledger_artifact": ledger_path.as_posix() if ledger_path else None,
        }
    if hypothesis_metadata is not None:
        payload["hypotheses"] = {
            "hypothesis_count": int(hypothesis_metadata.get("hypothesis_count", 0)),
            "supported_hypothesis_count": int(hypothesis_metadata.get("supported_hypothesis_count", 0)),
            "unclear_hypothesis_count": int(hypothesis_metadata.get("unclear_hypothesis_count", 0)),
            "not_supported_hypothesis_count": int(hypothesis_metadata.get("not_supported_hypothesis_count", 0)),
            "hypothesis_tracker_artifact": hypothesis_tracker_path.as_posix() if hypothesis_tracker_path else None,
        }
    if findings_metadata is not None:
        payload["findings"] = {
            "supported_signal_count": int(findings_metadata.get("supported_signal_count", 0)),
            "unclear_item_count": int(findings_metadata.get("unclear_item_count", 0)),
            "finding_status": findings_metadata.get("finding_status"),
            "investigation_findings_artifact": findings_path.as_posix() if findings_path else None,
        }
    return payload


def build_profiled_trace(
    *,
    issue_statement: str | None,
    loaded_dataset: "LoadedDataset",
    profile_path: Path,
    trace_path: Path,
    case_path: Path,
    plan_path: Path,
) -> dict[str, Any]:
    """Build a trace payload for a run that produced a dataset profile."""
    return build_investigation_trace(
        issue_statement=issue_statement,
        loaded_dataset=loaded_dataset,
        profile_path=profile_path,
        trace_path=trace_path,
        case_path=case_path,
        plan_path=plan_path,
    )


def write_investigation_trace(
    *,
    output_dir: str | Path,
    issue_statement: str | None,
    case_path: Path,
    plan_path: Path,
    loaded_dataset: "LoadedDataset" | None = None,
    profile_path: Path | None = None,
    ledger_path: Path | None = None,
    baseline_dataset: "LoadedDataset" | None = None,
    baseline_profile_path: Path | None = None,
    baseline_comparison_path: Path | None = None,
    baseline_comparison_metadata: dict[str, Any] | None = None,
    evidence_metadata: dict[str, Any] | None = None,
    hypothesis_tracker_path: Path | None = None,
    findings_path: Path | None = None,
    hypothesis_metadata: dict[str, Any] | None = None,
    findings_metadata: dict[str, Any] | None = None,
) -> Path:
    """Create the output directory and write the investigation trace JSON artifact."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    trace_path = output_path / TRACE_FILENAME
    trace = build_investigation_trace(
        issue_statement=issue_statement,
        trace_path=trace_path,
        case_path=case_path,
        plan_path=plan_path,
        loaded_dataset=loaded_dataset,
        profile_path=profile_path,
        ledger_path=ledger_path,
        evidence_metadata=evidence_metadata,
        baseline_dataset=baseline_dataset,
        baseline_profile_path=baseline_profile_path,
        baseline_comparison_path=baseline_comparison_path,
        baseline_comparison_metadata=baseline_comparison_metadata,
        hypothesis_tracker_path=hypothesis_tracker_path,
        findings_path=findings_path,
        hypothesis_metadata=hypothesis_metadata,
        findings_metadata=findings_metadata,
    )
    _write_json(trace_path, trace)
    return trace_path


def write_profiled_trace(
    *,
    output_dir: str | Path,
    issue_statement: str | None,
    loaded_dataset: "LoadedDataset",
    profile_path: Path,
    case_path: Path,
    plan_path: Path,
) -> Path:
    """Create the output directory and write a profiled-run trace artifact."""
    return write_investigation_trace(
        output_dir=output_dir,
        issue_statement=issue_statement,
        loaded_dataset=loaded_dataset,
        profile_path=profile_path,
        case_path=case_path,
        plan_path=plan_path,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _artifacts(
    *,
    case_path: Path,
    profile_path: Path | None,
    plan_path: Path,
    ledger_path: Path | None,
    trace_path: Path,
    baseline_profile_path: Path | None,
    baseline_comparison_path: Path | None,
    hypothesis_tracker_path: Path | None = None,
    findings_path: Path | None = None,
) -> dict[str, str | None]:
    artifacts = {
        "investigation_case": case_path.as_posix(),
        "dataset_profile": profile_path.as_posix() if profile_path else None,
        "investigation_plan": plan_path.as_posix(),
        "evidence_ledger": ledger_path.as_posix() if ledger_path else None,
        "investigation_trace": trace_path.as_posix(),
    }
    if baseline_profile_path is not None:
        artifacts["baseline_profile"] = baseline_profile_path.as_posix()
    if baseline_comparison_path is not None:
        artifacts["baseline_comparison"] = baseline_comparison_path.as_posix()
    if hypothesis_tracker_path is not None:
        artifacts["hypothesis_tracker"] = hypothesis_tracker_path.as_posix()
    if findings_path is not None:
        artifacts["investigation_findings"] = findings_path.as_posix()
    return artifacts
