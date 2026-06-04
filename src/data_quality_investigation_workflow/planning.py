"""Investigation plan artifact builders.

The plan records what the workflow intends to check for the selected route and
what inputs those checks need. Some planned checks are executable now; others are
human-review-led or require a future input such as a baseline. Candidate columns
are selected from names and profile metadata only, not from raw values.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from data_quality_investigation_workflow.issue_classifier import (
    ROUTE_NAMES,
    ROUTE_REASONS,
    classify_issue,
)
from data_quality_investigation_workflow.workflow_scope import AUTHORITY_BOUNDARY

if TYPE_CHECKING:
    from data_quality_investigation_workflow.intake import LoadedDataset

PLAN_FILENAME = "investigation_plan.json"
PLAN_VERSION = "0.1"

PLAN_LIMITATIONS = [
    "This plan does not run checks.",
    "This plan does not confirm the reported issue.",
    "This plan does not identify root cause.",
    "This plan does not create evidence findings.",
]

_CHECKS = {
    "duplicate_key": [
        (
            "planned_duplicate_key_summary",
            "Duplicate key summary",
            "Check whether candidate key columns contain duplicate non-null values.",
            ["duplicate count", "affected column names", "aggregate severity signal"],
            False,
        ),
        (
            "planned_key_null_summary",
            "Key null summary",
            "Check whether candidate key columns contain null values.",
            ["null count", "affected key column names"],
            False,
        ),
        (
            "planned_duplicate_pattern_review",
            "Duplicate pattern review",
            "Review aggregate duplicate signals for likely duplicate-key patterns.",
            ["aggregate duplicate pattern notes"],
            False,
        ),
    ],
    "null_increase": [
        (
            "planned_current_null_summary",
            "Current null summary",
            "Summarize current null counts and percentages for candidate columns.",
            ["null count", "null percentage", "affected column names"],
            False,
        ),
        (
            "planned_baseline_null_comparison",
            "Baseline null comparison",
            "Compare current null rates against a baseline when available.",
            ["baseline delta", "changed columns"],
            True,
        ),
        (
            "planned_null_by_candidate_group_review",
            "Null by candidate group review",
            "Review whether null changes cluster by safe candidate grouping columns.",
            ["aggregate group-level null signal"],
            False,
        ),
    ],
    "date_gap": [
        (
            "planned_date_range_summary",
            "Date range summary",
            "Summarize date ranges for candidate date columns.",
            ["minimum date", "maximum date", "date coverage signal"],
            False,
        ),
        (
            "planned_missing_period_detection",
            "Missing period detection",
            "Detect missing expected periods in candidate date columns.",
            ["missing period count", "affected date columns"],
            False,
        ),
        (
            "planned_date_frequency_review",
            "Date frequency review",
            "Review whether date frequency matches the expected cadence.",
            ["cadence signal", "frequency notes"],
            False,
        ),
    ],
    "category_shift": [
        (
            "planned_category_distribution_summary",
            "Category distribution summary",
            "Summarize current category distributions for candidate categorical columns.",
            ["category counts", "category percentages"],
            False,
        ),
        (
            "planned_baseline_category_comparison",
            "Baseline category comparison",
            "Compare category distributions against a baseline when available.",
            ["distribution delta", "changed categories"],
            True,
        ),
        (
            "planned_unexpected_category_review",
            "Unexpected category review",
            "Review whether unexpected categories appear in candidate columns.",
            ["unexpected category signal"],
            False,
        ),
    ],
    "total_change": [
        (
            "planned_numeric_total_summary",
            "Numeric total summary",
            "Summarize totals for candidate numeric columns.",
            ["numeric totals", "affected numeric columns"],
            False,
        ),
        (
            "planned_baseline_total_comparison",
            "Baseline total comparison",
            "Compare totals against a baseline when available.",
            ["total delta", "baseline comparison signal"],
            True,
        ),
        (
            "planned_row_count_change_review",
            "Row count change review",
            "Review whether row count changes may explain total or volume changes.",
            ["row count delta", "volume signal"],
            True,
        ),
    ],
    "schema_change": [
        (
            "planned_current_schema_summary",
            "Current schema summary",
            "Summarize current column names, order, and inferred types.",
            ["column count", "column names", "inferred column kinds"],
            False,
        ),
        (
            "planned_baseline_schema_comparison",
            "Baseline schema comparison",
            "Compare current schema against a baseline when available.",
            ["added columns", "removed columns", "type changes"],
            True,
        ),
        (
            "planned_required_column_review",
            "Required column review",
            "Review whether expected business-required columns are present.",
            ["required column status"],
            False,
        ),
    ],
    "general_suspected_issue": [
        (
            "planned_general_profile_review",
            "General profile review",
            "Review safe aggregate profile metrics for human-directed investigation.",
            ["profile review prompts"],
            False,
        ),
        (
            "planned_reviewer_question_capture",
            "Reviewer question capture",
            "Capture clarifying questions needed before selecting a more specific route.",
            ["reviewer questions"],
            False,
        ),
    ],
}

_PROMPTS = {
    "duplicate_key": [
        "Confirm which column or columns should be treated as the business key.",
        "Confirm whether duplicate identifiers are always invalid or sometimes expected.",
    ],
    "null_increase": [
        "Confirm which field or fields are expected to be populated.",
        "Confirm the comparison period or threshold that made the null increase suspicious.",
    ],
    "date_gap": [
        "Confirm the expected date grain and business calendar.",
        "Confirm whether weekends, holidays, or late-arriving data should be excluded.",
    ],
    "category_shift": [
        "Confirm which categorical fields and values are business-critical.",
        "Confirm the expected distribution, comparison period, or known operational changes.",
    ],
    "total_change": [
        "Confirm which total, count, or volume metric changed.",
        "Confirm the baseline period and acceptable tolerance.",
    ],
    "schema_change": [
        "Confirm the expected schema and required columns.",
        "Confirm whether upstream schema changes were planned.",
    ],
    "general_suspected_issue": [
        "Clarify the suspected issue in concrete terms.",
        "Identify the business impact and the dataset fields most likely to be relevant.",
    ],
    "missing_issue_statement": [
        "Provide a known or suspected data quality issue statement before route selection is meaningful.",
    ],
}

_ROUTE_COLUMN_TERMS = {
    "duplicate_key": ["id", "key", "code", "number", "reference", "ref"],
    "date_gap": ["date", "time", "timestamp", "period", "day", "month", "year"],
    "category_shift": ["status", "category", "type", "segment", "region"],
    "total_change": ["total", "amount", "value", "count", "quantity", "qty", "volume"],
}


def build_investigation_plan(
    *,
    issue_statement: str | None,
    loaded_dataset: "LoadedDataset" | None,
    dataset_profile: dict[str, Any] | None,
    case_path: Path,
    profile_path: Path | None,
    plan_path: Path,
    trace_path: Path,
    ledger_path: Path | None = None,
    baseline_dataset: "LoadedDataset" | None = None,
    baseline_profile_path: Path | None = None,
    baseline_comparison_path: Path | None = None,
    hypothesis_tracker_path: Path | None = None,
    findings_path: Path | None = None,
) -> dict[str, Any]:
    """Build an investigation plan without executing planned checks."""
    classification = classify_issue(issue_statement)
    # The plan makes the route visible before any checks run. That lets a human
    # see why a suspected duplicate issue, null issue, or schema issue followed a
    # particular path.
    issue_type = classification["issue_type"]
    route_name = classification["selected_route"]
    return {
        "artifact_type": "investigation_plan",
        "plan_version": PLAN_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "issue": {
            "statement": issue_statement,
            "provided": classification["provided"],
            "classification_status": classification["classification_status"],
            "issue_type": issue_type,
            "matched_terms": classification["matched_terms"],
            "classification_method": classification["classification_method"],
            "classification_limitations": classification["classification_limitations"],
        },
        "route": {
            "route_name": route_name,
            "route_status": "planned" if classification["provided"] else "not_ready",
            "route_reason": ROUTE_REASONS[issue_type],
        },
        "inputs": _inputs(
            profile_path,
            issue_provided=classification["provided"],
            baseline_dataset=baseline_dataset,
            baseline_profile_path=baseline_profile_path,
            baseline_comparison_path=baseline_comparison_path,
        ),
        "dataset_context": _dataset_context(
            loaded_dataset=loaded_dataset,
            dataset_profile=dataset_profile,
            issue_statement=issue_statement,
            issue_type=issue_type,
        ),
        "planned_checks": _planned_checks(
            issue_type, baseline_available=baseline_dataset is not None
        ),
        "human_review_prompts": _PROMPTS[issue_type],
        "limitations": PLAN_LIMITATIONS,
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


def write_investigation_plan(
    *,
    output_dir: str | Path,
    issue_statement: str | None,
    loaded_dataset: "LoadedDataset" | None = None,
    dataset_profile: dict[str, Any] | None = None,
    case_path: Path,
    profile_path: Path | None = None,
    ledger_path: Path | None = None,
    baseline_dataset: "LoadedDataset" | None = None,
    baseline_profile_path: Path | None = None,
    baseline_comparison_path: Path | None = None,
    hypothesis_tracker_path: Path | None = None,
    findings_path: Path | None = None,
) -> Path:
    """Create the output directory and write the investigation plan artifact."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    plan_path = output_path / PLAN_FILENAME
    trace_path = output_path / "investigation_trace.json"
    plan = build_investigation_plan(
        issue_statement=issue_statement,
        loaded_dataset=loaded_dataset,
        dataset_profile=dataset_profile,
        case_path=case_path,
        profile_path=profile_path,
        plan_path=plan_path,
        trace_path=trace_path,
        ledger_path=ledger_path,
        baseline_dataset=baseline_dataset,
        baseline_profile_path=baseline_profile_path,
        baseline_comparison_path=baseline_comparison_path,
        hypothesis_tracker_path=hypothesis_tracker_path,
        findings_path=findings_path,
    )
    plan_path.write_text(
        json.dumps(plan, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    return plan_path


def _inputs(
    profile_path: Path | None,
    *,
    issue_provided: bool,
    baseline_dataset: "LoadedDataset" | None,
    baseline_profile_path: Path | None,
    baseline_comparison_path: Path | None,
) -> dict[str, Any]:
    baseline_available = baseline_dataset is not None
    missing_inputs = []
    if not issue_provided:
        missing_inputs.append("issue statement")
    if not baseline_available:
        missing_inputs.append("baseline dataset or prior-run artifact")
    return {
        "dataset_profile_available": profile_path is not None,
        "dataset_profile_artifact": profile_path.as_posix() if profile_path else None,
        "baseline_available": baseline_available,
        "baseline_profile_artifact": (
            baseline_profile_path.as_posix() if baseline_profile_path else None
        ),
        "baseline_comparison_artifact": (
            baseline_comparison_path.as_posix() if baseline_comparison_path else None
        ),
        "baseline_note": (
            "Baseline comparison aggregate evidence is executable when a baseline is supplied."
            if baseline_available
            else "No baseline was supplied for this run."
        ),
        "required_inputs": [
            "issue statement",
            "current dataset profile",
            "current raw dataset for executable deterministic checks",
            "baseline dataset for executable baseline comparisons",
        ],
        "available_inputs": [
            input_name
            for input_name, available in [
                ("issue statement", issue_provided),
                ("current dataset profile", profile_path is not None),
                ("baseline dataset", baseline_available),
            ]
            if available
        ],
        "missing_inputs": missing_inputs,
    }


def _dataset_context(
    *,
    loaded_dataset: "LoadedDataset" | None,
    dataset_profile: dict[str, Any] | None,
    issue_statement: str | None,
    issue_type: str,
) -> dict[str, Any]:
    if loaded_dataset is None:
        return {
            "input_file_name": None,
            "file_extension": None,
            "sheet_name": None,
            "row_count": None,
            "column_count": None,
            "candidate_columns": [],
        }
    return {
        "input_file_name": loaded_dataset.file_name,
        "file_extension": loaded_dataset.file_extension,
        "sheet_name": loaded_dataset.sheet_name,
        "row_count": loaded_dataset.row_count,
        "column_count": loaded_dataset.column_count,
        "candidate_columns": _candidate_columns(
            dataset_profile, issue_statement, issue_type
        ),
    }


def _planned_checks(
    issue_type: str, *, baseline_available: bool
) -> list[dict[str, Any]]:
    # Planned checks document intent. Some are executable in the current run;
    # others remain human-review-led or need a baseline to become comparison evidence.
    if issue_type == "missing_issue_statement":
        return []
    return [
        {
            "check_id": check_id,
            "check_name": check_name,
            "status": "planned_not_run",
            "purpose": purpose,
            "requires_dataset_profile": _requires_dataset_profile(check_id),
            "requires_raw_dataset": _requires_raw_dataset(check_id, requires_baseline),
            "requires_baseline": requires_baseline,
            "planned_outputs": planned_outputs,
            "executable_in_current_run": (not requires_baseline or baseline_available),
            "execution_stage": (
                "baseline_comparison" if requires_baseline else "current_dataset_checks"
            ),
            "requires_later_interpretation": True,
            "not_run_reason": (
                "The plan records intended checks. Baseline comparison can record aggregate signals when baseline is supplied, but interpretation remains human-review-led."
            ),
        }
        for check_id, check_name, purpose, planned_outputs, requires_baseline in _CHECKS[
            issue_type
        ]
    ]


def _candidate_columns(
    dataset_profile: dict[str, Any] | None, issue_statement: str | None, issue_type: str
) -> list[dict[str, str]]:
    if not dataset_profile:
        return []
    columns = dataset_profile.get("columns", [])
    issue_tokens = _issue_tokens(issue_statement)
    candidates: list[dict[str, str]] = []
    for column in columns:
        # Candidate selection uses names and broad profile metadata only. Raw
        # values are not inspected for planning hints.
        name = str(column.get("name", ""))
        normalized = name.casefold()
        kind = str(column.get("inferred_kind", ""))
        if _column_matches(issue_type, normalized, kind, issue_tokens):
            candidates.append(
                {
                    "name": name,
                    "reason": "Column name or safe profile metadata appears related to the issue statement or selected route.",
                }
            )
    return candidates


def _column_matches(
    issue_type: str, normalized_name: str, kind: str, issue_tokens: set[str]
) -> bool:
    if issue_type in {"null_increase", "schema_change"} and _mentions_column(
        normalized_name, issue_tokens
    ):
        return True
    if issue_type == "duplicate_key":
        return any(
            term in normalized_name for term in _ROUTE_COLUMN_TERMS["duplicate_key"]
        )
    if issue_type == "date_gap":
        return kind == "datetime" or any(
            term in normalized_name for term in _ROUTE_COLUMN_TERMS["date_gap"]
        )
    if issue_type == "category_shift":
        return any(
            term in normalized_name for term in _ROUTE_COLUMN_TERMS["category_shift"]
        )
    if issue_type == "total_change":
        return kind in {"integer", "decimal"} or any(
            term in normalized_name for term in _ROUTE_COLUMN_TERMS["total_change"]
        )
    return False


def _mentions_column(normalized_name: str, issue_tokens: set[str]) -> bool:
    if not normalized_name:
        return False
    name_tokens = set(re.findall(r"[a-z0-9]+", normalized_name))
    return bool(name_tokens & issue_tokens) or normalized_name.replace(
        "_", " "
    ) in " ".join(sorted(issue_tokens))


def _issue_tokens(issue_statement: str | None) -> set[str]:
    if not issue_statement:
        return set()
    stop_words = {
        "a",
        "an",
        "and",
        "are",
        "field",
        "fields",
        "has",
        "have",
        "in",
        "the",
        "to",
        "with",
        "started",
        "increased",
        "decreased",
        "missing",
        "null",
        "nulls",
        "blank",
        "empty",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", issue_statement.casefold())
        if token not in stop_words
    }


def route_name_for_issue_type(issue_type: str) -> str:
    """Return the deterministic route name for an issue type."""
    return ROUTE_NAMES[issue_type]


def _requires_dataset_profile(check_id: str) -> bool:
    return check_id in {
        "planned_current_schema_summary",
        "planned_general_profile_review",
    } or not check_id.startswith("planned_reviewer_question")


def _requires_raw_dataset(check_id: str, requires_baseline: bool) -> bool:
    if requires_baseline:
        return False
    return check_id in {
        "planned_duplicate_key_summary",
        "planned_key_null_summary",
        "planned_current_null_summary",
        "planned_date_range_summary",
        "planned_missing_period_detection",
        "planned_date_frequency_review",
        "planned_category_distribution_summary",
        "planned_numeric_total_summary",
    }


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
