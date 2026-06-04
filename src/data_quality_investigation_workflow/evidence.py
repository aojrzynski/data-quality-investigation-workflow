"""Evidence ledger artifact builders and writers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from data_quality_investigation_workflow.checks import run_route_checks
from data_quality_investigation_workflow.intake import LoadedDataset

LEDGER_FILENAME = "evidence_ledger.json"
LEDGER_VERSION = "0.1"

SAFETY_NOTES = [
    "Evidence is aggregate-only.",
    "Raw rows, sampled records, example values, top values, and distinct value lists are not included.",
    "Duplicated values, category labels, row numbers, and raw failing records are not included.",
]

LEDGER_LIMITATIONS = [
    "This ledger records deterministic evidence only.",
    "The ledger does not create final findings.",
    "The ledger does not confirm root cause.",
    "Baseline comparison evidence records aggregate signals only and remains subject to human review.",
]

LEDGER_AUTHORITY_BOUNDARY = [
    "Evidence items are deterministic aggregate signals.",
    "Evidence items are not final findings.",
    "The ledger does not identify root cause.",
    "Human review remains the final authority.",
]


def build_evidence_ledger(
    *,
    issue_statement: str | None,
    classification: dict[str, Any],
    route_name: str,
    loaded_dataset: LoadedDataset,
    dataset_profile: dict[str, Any],
    investigation_plan: dict[str, Any],
    evidence_items: list[dict[str, Any]],
    checks_not_run: list[dict[str, str]],
    checks_executed_count: int,
    case_path: Path,
    profile_path: Path,
    plan_path: Path,
    ledger_path: Path,
    trace_path: Path,
    reason: str | None = None,
    baseline_comparison: dict[str, Any] | None = None,
    baseline_profile_path: Path | None = None,
    baseline_comparison_path: Path | None = None,
) -> dict[str, Any]:
    """Build an aggregate-only evidence ledger payload."""
    issue_provided = bool(classification.get("provided"))
    status = "checks_executed" if issue_provided else "not_executed"
    execution: dict[str, Any] = {
        "status": status,
        "dataset_available": True,
        "checks_executed_count": checks_executed_count,
        "evidence_item_count": len(evidence_items),
        "checks_not_run_count": len(checks_not_run),
        "baseline_available": baseline_comparison is not None,
        "baseline_note": (
            "Aggregate baseline comparison signals were available for route-aware evidence."
            if baseline_comparison is not None
            else "No baseline comparison was available for this run."
        ),
    }
    if reason:
        execution["reason"] = reason

    return {
        "artifact_type": "evidence_ledger",
        "ledger_version": LEDGER_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "issue": {
            "statement": issue_statement,
            "issue_type": classification["issue_type"],
            "selected_route": route_name,
            "classification_method": classification["classification_method"],
            "classification_note": "Classification is used to select checks. It is not evidence that the issue exists.",
        },
        "execution": execution,
        "dataset_reference": {
            "file_name": loaded_dataset.file_name,
            "file_extension": loaded_dataset.file_extension,
            "sheet_name": loaded_dataset.sheet_name,
            "row_count": loaded_dataset.row_count,
            "column_count": loaded_dataset.column_count,
        },
        "evidence_items": evidence_items,
        "checks_not_run": checks_not_run,
        "safety_notes": SAFETY_NOTES,
        "limitations": LEDGER_LIMITATIONS,
        "artifacts": _artifacts(
            case_path=case_path,
            profile_path=profile_path,
            plan_path=plan_path,
            ledger_path=ledger_path,
            trace_path=trace_path,
            baseline_profile_path=baseline_profile_path,
            baseline_comparison_path=baseline_comparison_path,
        ),
        "authority_boundary": LEDGER_AUTHORITY_BOUNDARY,
    }


def write_evidence_ledger(
    *,
    output_dir: str | Path,
    issue_statement: str | None,
    classification: dict[str, Any],
    route_name: str,
    loaded_dataset: LoadedDataset,
    dataset_profile: dict[str, Any],
    investigation_plan: dict[str, Any],
    case_path: Path,
    profile_path: Path,
    plan_path: Path,
    trace_path: Path,
    baseline_comparison: dict[str, Any] | None = None,
    baseline_profile_path: Path | None = None,
    baseline_comparison_path: Path | None = None,
) -> Path:
    """Run route checks and write the aggregate-only evidence ledger artifact."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    ledger_path = output_path / LEDGER_FILENAME

    result = run_route_checks(
        loaded_dataset,
        dataset_profile,
        investigation_plan,
        baseline_comparison=baseline_comparison,
    )
    ledger = build_evidence_ledger(
        issue_statement=issue_statement,
        classification=classification,
        route_name=route_name,
        loaded_dataset=loaded_dataset,
        dataset_profile=dataset_profile,
        investigation_plan=investigation_plan,
        evidence_items=result["evidence_items"],
        checks_not_run=result["checks_not_run"],
        checks_executed_count=int(result["checks_executed_count"]),
        case_path=case_path,
        profile_path=profile_path,
        plan_path=plan_path,
        ledger_path=ledger_path,
        trace_path=trace_path,
        reason=result.get("reason"),
        baseline_comparison=baseline_comparison,
        baseline_profile_path=baseline_profile_path,
        baseline_comparison_path=baseline_comparison_path,
    )
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return ledger_path


def _artifacts(
    *,
    case_path: Path,
    profile_path: Path,
    plan_path: Path,
    ledger_path: Path,
    trace_path: Path,
    baseline_profile_path: Path | None,
    baseline_comparison_path: Path | None,
) -> dict[str, str]:
    artifacts = {
        "investigation_case": case_path.as_posix(),
        "dataset_profile": profile_path.as_posix(),
        "investigation_plan": plan_path.as_posix(),
        "evidence_ledger": ledger_path.as_posix(),
        "investigation_trace": trace_path.as_posix(),
    }
    if baseline_profile_path is not None:
        artifacts["baseline_profile"] = baseline_profile_path.as_posix()
    if baseline_comparison_path is not None:
        artifacts["baseline_comparison"] = baseline_comparison_path.as_posix()
    return artifacts
