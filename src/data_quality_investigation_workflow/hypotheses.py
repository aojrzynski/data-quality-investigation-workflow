"""Hypothesis tracker artifact builders and writers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HYPOTHESIS_TRACKER_FILENAME = "hypothesis_tracker.json"
HYPOTHESIS_TRACKER_VERSION = "0.1"

SUPPORTED = "supported_by_evidence"
NOT_SUPPORTED = "not_supported_by_evidence"
UNCLEAR = "unclear"
NOT_ASSESSED = "not_assessed"

SAFETY_NOTES = [
    "Hypotheses reference aggregate evidence IDs only.",
    "Raw rows, sampled records, example values, top values, distinct value lists, duplicated values, and category labels are not included.",
]

LIMITATIONS = [
    "Hypotheses are evidence-interpretation aids, not final conclusions.",
    "The tracker does not identify root cause.",
    "Human review remains required.",
]

AUTHORITY_BOUNDARY = [
    "Hypotheses are not final findings.",
    "Hypotheses do not identify root cause.",
    "Human review remains the final authority.",
]

_COMMON_LIMITATIONS = [
    "This is an aggregate evidence signal only.",
    "This does not explain why the signal appeared.",
    "Human review is required before treating this as an operational finding.",
]

_DAILY_CADENCE_LIMITATION = "Daily cadence is an assumption and should be checked by a human reviewer."


def build_hypothesis_tracker(
    *,
    issue_statement: str | None,
    classification: dict[str, Any],
    investigation_plan: dict[str, Any],
    evidence_ledger: dict[str, Any] | None,
    artifacts: dict[str, str | None],
    baseline_comparison_available: bool = False,
) -> dict[str, Any]:
    """Build a bounded hypothesis tracker from aggregate evidence IDs."""
    evidence_items = list(evidence_ledger.get("evidence_items", [])) if evidence_ledger else []
    evidence_by_check = {str(item.get("check_id")): item for item in evidence_items}
    issue_type = str(classification["issue_type"])
    route_name = str(classification["selected_route"])
    hypotheses = _route_hypotheses(
        issue_type=issue_type,
        route_name=route_name,
        evidence_by_check=evidence_by_check,
        baseline_available=baseline_comparison_available,
    )
    summary = _status_counts(hypotheses)
    return {
        "artifact_type": "hypothesis_tracker",
        "tracker_version": HYPOTHESIS_TRACKER_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "issue": {
            "statement": issue_statement,
            "issue_type": issue_type,
            "selected_route": route_name,
        },
        "input_state": {
            "evidence_ledger_available": evidence_ledger is not None,
            "baseline_comparison_available": baseline_comparison_available,
            "evidence_item_count": len(evidence_items),
        },
        "plan_reference": {
            "plan_artifact": artifacts.get("investigation_plan"),
            "planned_check_count": len(investigation_plan.get("planned_checks", [])),
        },
        "hypotheses": hypotheses,
        "hypothesis_summary": summary,
        "safety_notes": SAFETY_NOTES,
        "limitations": LIMITATIONS,
        "artifacts": artifacts,
        "authority_boundary": AUTHORITY_BOUNDARY,
    }


def write_hypothesis_tracker(
    *,
    output_dir: str | Path,
    issue_statement: str | None,
    classification: dict[str, Any],
    investigation_plan: dict[str, Any],
    evidence_ledger: dict[str, Any],
    artifacts: dict[str, str | None],
    baseline_comparison_available: bool,
) -> Path:
    """Write the hypothesis tracker JSON artifact."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    tracker_path = output_path / HYPOTHESIS_TRACKER_FILENAME
    tracker = build_hypothesis_tracker(
        issue_statement=issue_statement,
        classification=classification,
        investigation_plan=investigation_plan,
        evidence_ledger=evidence_ledger,
        artifacts=artifacts,
        baseline_comparison_available=baseline_comparison_available,
    )
    tracker_path.write_text(json.dumps(tracker, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return tracker_path


def _route_hypotheses(
    *,
    issue_type: str,
    route_name: str,
    evidence_by_check: dict[str, dict[str, Any]],
    baseline_available: bool,
) -> list[dict[str, Any]]:
    builders = {
        "duplicate_key": _duplicate_hypotheses,
        "null_increase": _null_hypotheses,
        "date_gap": _date_hypotheses,
        "total_change": _total_hypotheses,
        "schema_change": _schema_hypotheses,
        "category_shift": _category_hypotheses,
        "general_suspected_issue": _general_hypotheses,
        "missing_issue_statement": lambda **_: [],
    }
    hypotheses = builders.get(issue_type, _general_hypotheses)(
        route_name=route_name,
        issue_type=issue_type,
        evidence_by_check=evidence_by_check,
        baseline_available=baseline_available,
    )
    return [{"hypothesis_id": f"hyp-{index:03d}", **hyp} for index, hyp in enumerate(hypotheses, 1)]


def _duplicate_hypotheses(**kwargs: Any) -> list[dict[str, Any]]:
    e = kwargs["evidence_by_check"]
    return [
        _from_signal(
            statement="Candidate key columns contain duplicate non-null values in the current dataset.",
            evidence=e.get("duplicate_key_summary"),
            present_status=SUPPORTED,
            absent_status=NOT_SUPPORTED,
            rationale_present="The duplicate-key evidence item has a present aggregate duplicate signal.",
            rationale_absent="The duplicate-key evidence item did not detect duplicate non-null values in assessed candidate key columns.",
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            checks=[
                "Confirm which column or combination of columns is the business key.",
                "Confirm whether duplicate identifiers are always invalid or sometimes expected.",
            ],
        ),
        _baseline_signal_hypothesis(
            statement="Duplicate aggregate counts are higher in the current dataset than the baseline for one or more assessed columns.",
            evidence=e.get("baseline_duplicate_comparison"),
            baseline_available=kwargs["baseline_available"],
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            missing_rationale="No baseline duplicate comparison evidence was available for this run.",
            checks=["Review source, extract, or join changes if duplicate counts increased against baseline."],
        ),
        _from_signal(
            statement="Candidate key nulls may also contribute to identifier quality concerns.",
            evidence=e.get("key_null_summary"),
            present_status=SUPPORTED,
            absent_status=NOT_SUPPORTED,
            rationale_present="The key-null evidence item has a present aggregate null signal for candidate key columns.",
            rationale_absent="The key-null evidence item did not detect nulls in assessed candidate key columns.",
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            checks=["Review whether nullable key fields are expected for this dataset."],
        ),
    ]


def _null_hypotheses(**kwargs: Any) -> list[dict[str, Any]]:
    e = kwargs["evidence_by_check"]
    return [
        _from_signal(
            statement="The current dataset contains nulls in assessed columns.",
            evidence=e.get("current_null_summary"),
            present_status=SUPPORTED,
            absent_status=NOT_SUPPORTED,
            rationale_present="The current-null evidence item has a present aggregate null signal.",
            rationale_absent="The current-null evidence item did not detect nulls in assessed columns.",
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            checks=["Confirm the specific column or columns meant by the issue statement."],
        ),
        _baseline_signal_hypothesis(
            statement="The current dataset has a higher null percentage than the baseline in one or more assessed columns.",
            evidence=e.get("baseline_null_comparison"),
            baseline_available=kwargs["baseline_available"],
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            missing_rationale="No baseline null comparison evidence was available, so an increase cannot be assessed from current-only evidence.",
            checks=["Check whether upstream validation, extraction, or optionality rules changed."],
        ),
        _context_hypothesis(
            statement="The issue may be column-specific and should be reviewed against the intended business column.",
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            rationale="Aggregate null evidence does not decide whether the assessed columns match the reviewer intent.",
            checks=["Decide whether the observed null difference is operationally meaningful."],
        ),
    ]


def _date_hypotheses(**kwargs: Any) -> list[dict[str, Any]]:
    e = kwargs["evidence_by_check"]
    limitation = [*_COMMON_LIMITATIONS, _DAILY_CADENCE_LIMITATION]
    return [
        _from_signal(
            statement="Candidate date columns contain an aggregate daily-cadence gap signal.",
            evidence=e.get("date_gap_summary"),
            present_status=SUPPORTED,
            absent_status=NOT_SUPPORTED,
            rationale_present="The date-gap evidence item has a present missing-daily-period aggregate signal.",
            rationale_absent="The date-gap evidence item did not detect missing daily periods in assessed candidate date columns.",
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            checks=["Confirm the expected date cadence, especially whether daily cadence is valid."],
            limitations=limitation,
        ),
        _baseline_signal_hypothesis(
            statement="The current dataset has more missing daily periods than baseline for one or more assessed date columns.",
            evidence=e.get("baseline_date_comparison"),
            baseline_available=kwargs["baseline_available"],
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            missing_rationale="No baseline date comparison evidence was available for this run.",
            checks=["Check upstream scheduling, file delivery, or filter changes."],
            limitations=limitation,
        ),
        _context_hypothesis(
            statement="The daily cadence assumption may need confirmation.",
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            rationale="Date-gap evidence is based on daily-cadence aggregate checks and does not decide the correct business calendar.",
            checks=["Review whether missing periods are expected non-business days or true gaps."],
            limitations=limitation,
        ),
    ]


def _total_hypotheses(**kwargs: Any) -> list[dict[str, Any]]:
    e = kwargs["evidence_by_check"]
    current_ids = _ids([e.get("numeric_total_summary"), e.get("row_count_summary")])
    return [
        _manual_hypothesis(
            statement="Current numeric totals or row counts were recorded as aggregate signals.",
            status=SUPPORTED if current_ids else NOT_ASSESSED,
            signal_level="low" if current_ids else "not_applicable",
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            supporting=current_ids,
            rationale="Current numeric-total or row-count aggregate evidence items were recorded." if current_ids else "No current total evidence item was available.",
            checks=["Confirm the correct business metric for the reported total."],
        ),
        _baseline_signal_hypothesis(
            statement="Current numeric totals or row counts differ from baseline.",
            evidence=e.get("baseline_total_comparison"),
            baseline_available=kwargs["baseline_available"],
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            missing_rationale="No baseline total comparison evidence was available for this run.",
            checks=["Check whether row-count or numeric-total differences are expected."],
        ),
        _context_hypothesis(
            statement="The apparent total change may depend on the correct business measure.",
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            rationale="Aggregate totals do not decide which measure is the intended business metric.",
            checks=["Review filters, source scope, and aggregation logic between baseline and current datasets."],
        ),
    ]


def _schema_hypotheses(**kwargs: Any) -> list[dict[str, Any]]:
    e = kwargs["evidence_by_check"]
    return [
        _from_signal(
            statement="Current schema metadata was recorded.",
            evidence=e.get("current_schema_summary"),
            present_status=SUPPORTED,
            absent_status=NOT_ASSESSED,
            rationale_present="The current-schema evidence item was recorded using metadata only.",
            rationale_absent="No current schema evidence item was available.",
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            checks=["Confirm expected required columns and allowed optional columns."],
        ),
        _baseline_signal_hypothesis(
            statement="Current and baseline schemas differ by added columns, removed columns, or inferred-kind changes.",
            evidence=e.get("baseline_schema_comparison"),
            baseline_available=kwargs["baseline_available"],
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            missing_rationale="No baseline schema comparison evidence was available for this run.",
            checks=["Check whether added or removed columns are expected schema evolution."],
        ),
        _context_hypothesis(
            statement="The schema difference may need validation against expected contracts or required columns.",
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            rationale="Schema evidence does not decide whether a metadata difference is expected or operationally meaningful.",
            checks=["Review downstream dependencies before changing any contracts."],
        ),
    ]


def _category_hypotheses(**kwargs: Any) -> list[dict[str, Any]]:
    e = kwargs["evidence_by_check"]
    return [
        _from_signal(
            statement="Current categorical shape was summarized without category labels.",
            evidence=e.get("categorical_shape_summary"),
            present_status=SUPPORTED,
            absent_status=UNCLEAR,
            rationale_present="The categorical-shape evidence item was recorded without category labels.",
            rationale_absent="Categorical-shape evidence did not identify clear candidate categorical columns.",
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            checks=["Confirm which categorical column is relevant to the issue statement."],
        ),
        _baseline_signal_hypothesis(
            statement="Current category shape differs from baseline by unique-count or high-cardinality aggregate signals.",
            evidence=e.get("baseline_category_shape_comparison"),
            baseline_available=kwargs["baseline_available"],
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            missing_rationale="No baseline category-shape comparison evidence was available for this run.",
            checks=["Inspect source system changes or mapping rules if category shape changed."],
        ),
        _context_hypothesis(
            statement="The category shift cannot be interpreted without business context because category labels are not written.",
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            rationale="The artifact intentionally omits category labels and full distributions.",
            checks=["Review whether unique-count changes are meaningful without seeing category labels in this artifact."],
        ),
    ]


def _general_hypotheses(**kwargs: Any) -> list[dict[str, Any]]:
    e = kwargs["evidence_by_check"]
    return [
        _from_signal(
            statement="The current dataset has general aggregate profile signals worth review.",
            evidence=e.get("general_profile_signal_summary"),
            present_status=SUPPORTED,
            absent_status=NOT_ASSESSED,
            rationale_present="General aggregate profile evidence was recorded.",
            rationale_absent="No general profile evidence item was available.",
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            checks=["Review profile summaries to decide which route should be investigated next."],
        ),
        _baseline_signal_hypothesis(
            statement="Current and baseline datasets differ in general aggregate profile metrics.",
            evidence=e.get("baseline_general_summary"),
            baseline_available=kwargs["baseline_available"],
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            missing_rationale="No baseline general comparison evidence was available for this run.",
            checks=["Review baseline comparison summaries to decide which route should be investigated next."],
        ),
        _context_hypothesis(
            statement="The issue statement is too broad for route-specific interpretation.",
            route_name=kwargs["route_name"],
            issue_type=kwargs["issue_type"],
            rationale="A broad issue statement limits deterministic route-specific interpretation.",
            checks=["Add a more specific issue statement for a more useful follow-up run."],
        ),
    ]


def _from_signal(
    *,
    statement: str,
    evidence: dict[str, Any] | None,
    present_status: str,
    absent_status: str,
    rationale_present: str,
    rationale_absent: str,
    route_name: str,
    issue_type: str,
    checks: list[str],
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    if evidence is None:
        return _manual_hypothesis(
            statement=statement,
            status=NOT_ASSESSED,
            signal_level="not_applicable",
            route_name=route_name,
            issue_type=issue_type,
            inconclusive=[],
            rationale="No related evidence item was available for this hypothesis.",
            checks=checks,
            limitations=limitations,
        )
    signal = str(evidence.get("signal", "unclear"))
    evidence_id = str(evidence.get("evidence_id"))
    if signal == "present":
        return _manual_hypothesis(
            statement=statement,
            status=present_status,
            signal_level=_signal_level(evidence),
            route_name=route_name,
            issue_type=issue_type,
            supporting=[evidence_id],
            rationale=rationale_present,
            checks=checks,
            limitations=limitations,
        )
    if signal == "absent":
        return _manual_hypothesis(
            statement=statement,
            status=absent_status,
            signal_level="low" if absent_status == NOT_SUPPORTED else "not_applicable",
            route_name=route_name,
            issue_type=issue_type,
            contradicting=[evidence_id] if absent_status == NOT_SUPPORTED else [],
            inconclusive=[evidence_id] if absent_status != NOT_SUPPORTED else [],
            rationale=rationale_absent,
            checks=checks,
            limitations=limitations,
        )
    return _manual_hypothesis(
        statement=statement,
        status=UNCLEAR,
        signal_level="not_applicable",
        route_name=route_name,
        issue_type=issue_type,
        inconclusive=[evidence_id],
        rationale="The related aggregate evidence signal was unclear.",
        checks=checks,
        limitations=limitations,
    )


def _baseline_signal_hypothesis(
    *,
    statement: str,
    evidence: dict[str, Any] | None,
    baseline_available: bool,
    route_name: str,
    issue_type: str,
    missing_rationale: str,
    checks: list[str],
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    if evidence is None:
        return _manual_hypothesis(
            statement=statement,
            status=UNCLEAR if not baseline_available else NOT_ASSESSED,
            signal_level="not_applicable",
            route_name=route_name,
            issue_type=issue_type,
            rationale=missing_rationale,
            checks=checks,
            limitations=limitations,
        )
    return _from_signal(
        statement=statement,
        evidence=evidence,
        present_status=SUPPORTED,
        absent_status=NOT_SUPPORTED,
        rationale_present=f"The {evidence.get('check_id')} evidence item has a present aggregate comparison signal.",
        rationale_absent=f"The {evidence.get('check_id')} evidence item did not record a present aggregate comparison signal.",
        route_name=route_name,
        issue_type=issue_type,
        checks=checks,
        limitations=limitations,
    )


def _context_hypothesis(
    *,
    statement: str,
    route_name: str,
    issue_type: str,
    rationale: str,
    checks: list[str],
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    return _manual_hypothesis(
        statement=statement,
        status=UNCLEAR,
        signal_level="not_applicable",
        route_name=route_name,
        issue_type=issue_type,
        rationale=rationale,
        checks=checks,
        limitations=limitations,
    )


def _manual_hypothesis(
    *,
    statement: str,
    status: str,
    signal_level: str,
    route_name: str,
    issue_type: str,
    rationale: str,
    checks: list[str],
    supporting: list[str] | None = None,
    contradicting: list[str] | None = None,
    inconclusive: list[str] | None = None,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "statement": statement,
        "status": status,
        "signal_level": signal_level,
        "route_name": route_name,
        "related_issue_type": issue_type,
        "supporting_evidence_ids": supporting or [],
        "contradicting_evidence_ids": contradicting or [],
        "inconclusive_evidence_ids": inconclusive or [],
        "rationale": rationale,
        "limitations": limitations or list(_COMMON_LIMITATIONS),
        "recommended_human_checks": checks,
    }


def _ids(items: list[dict[str, Any] | None]) -> list[str]:
    return [str(item.get("evidence_id")) for item in items if item is not None and item.get("evidence_id")]


def _signal_level(evidence: dict[str, Any]) -> str:
    strength = str(evidence.get("signal_strength", "low"))
    return strength if strength in {"low", "medium", "high"} else "low"


def _status_counts(hypotheses: list[dict[str, Any]]) -> dict[str, int]:
    return {
        SUPPORTED: sum(1 for item in hypotheses if item["status"] == SUPPORTED),
        NOT_SUPPORTED: sum(1 for item in hypotheses if item["status"] == NOT_SUPPORTED),
        UNCLEAR: sum(1 for item in hypotheses if item["status"] == UNCLEAR),
        NOT_ASSESSED: sum(1 for item in hypotheses if item["status"] == NOT_ASSESSED),
    }
