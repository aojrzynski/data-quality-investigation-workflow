"""Review-oriented finding summary builders.

Findings summarize evidence-supported signals and human checks. They are
interpretation aids, not final decisions.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from data_quality_investigation_workflow.hypotheses import (
    NOT_ASSESSED,
    NOT_SUPPORTED,
    SUPPORTED,
    UNCLEAR,
)

FINDINGS_FILENAME = "investigation_findings.json"
FINDINGS_VERSION = "0.1"

FINDING_STATUS_REVIEW_REQUIRED = "review_required"

NON_GOALS = [
    "This artifact does not identify root cause.",
    "This artifact does not approve, fix, certify, or trust a dataset.",
    "This artifact does not make legal, compliance, privacy, or governance verdicts.",
]

SAFETY_NOTES = [
    "Findings reference hypothesis IDs and evidence IDs only.",
    "Raw rows, sampled records, example values, top values, distinct value lists, duplicated values, and category labels are not included.",
]

AUTHORITY_BOUNDARY = [
    "Finding summaries are not final verdicts.",
    "Finding summaries do not identify root cause.",
    "Human review remains the final authority.",
]

ROUTE_HUMAN_CHECKS = {
    "duplicate_key": [
        "Confirm which column or combination of columns is the business key.",
        "Confirm whether duplicate identifiers are always invalid or sometimes expected.",
        "Review source, extract, or join changes if duplicate counts increased against baseline.",
    ],
    "null_increase": [
        "Confirm the specific column or columns meant by the issue statement.",
        "Check whether upstream validation, extraction, or optionality rules changed.",
        "Decide whether the observed null difference is operationally meaningful.",
    ],
    "date_gap": [
        "Confirm the expected date cadence, especially whether daily cadence is valid.",
        "Check upstream scheduling, file delivery, or filter changes.",
        "Review whether missing periods are expected non-business days or true gaps.",
    ],
    "total_change": [
        "Confirm the correct business metric for the reported total.",
        "Check whether row-count or numeric-total differences are expected.",
        "Review filters, source scope, and aggregation logic between baseline and current datasets.",
    ],
    "schema_change": [
        "Confirm expected required columns and allowed optional columns.",
        "Check whether added or removed columns are expected schema evolution.",
        "Review downstream dependencies before changing any contracts.",
    ],
    "category_shift": [
        "Confirm which categorical column is relevant to the issue statement.",
        "Review whether unique-count changes are meaningful without seeing category labels in this artifact.",
        "Inspect source system changes or mapping rules if category shape changed.",
    ],
    "general_suspected_issue": [
        "Clarify the issue statement.",
        "Review profile and baseline comparison summaries to decide which route should be investigated next.",
        "Add a more specific issue statement for a more useful follow-up run.",
    ],
}

GENERIC_UNCLEAR_ITEMS = [
    (
        "Root cause remains unclear.",
        "Evidence records aggregate signals only and does not inspect upstream process changes.",
        "Review upstream extraction, transformation, validation, and business-process changes.",
    ),
    (
        "Business impact remains unclear.",
        "Aggregate evidence does not determine operational impact or acceptable tolerance.",
        "Decide whether the aggregate signal is operationally meaningful.",
    ),
    (
        "Expected behavior or threshold remains unclear.",
        "The artifact does not define business rules, expected thresholds, or acceptance criteria.",
        "Confirm expected behavior, thresholds, and relevant business columns.",
    ),
]


def build_investigation_findings(
    *,
    issue_statement: str | None,
    classification: dict[str, Any],
    hypothesis_tracker: dict[str, Any] | None,
    evidence_ledger: dict[str, Any] | None,
    artifacts: dict[str, str | None],
    baseline_comparison_available: bool,
) -> dict[str, Any]:
    """Build a cautious finding summary from hypotheses and evidence IDs."""
    hypotheses = list(hypothesis_tracker.get("hypotheses", [])) if hypothesis_tracker else []
    issue_type = str(classification["issue_type"])
    supported_signals = _supported_signals(hypotheses)
    not_supported_signals = _not_supported_signals(hypotheses)
    unclear_items = _unclear_items(hypotheses)
    unclear_items.extend(_generic_unclear_items(start=len(unclear_items) + 1))
    checks = _dedupe(
        [*ROUTE_HUMAN_CHECKS.get(issue_type, ROUTE_HUMAN_CHECKS["general_suspected_issue"]), *list(_hypothesis_checks(hypotheses))]
    )
    return {
        "artifact_type": "investigation_findings",
        "findings_version": FINDINGS_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "issue": {
            "statement": issue_statement,
            "issue_type": issue_type,
            "selected_route": classification["selected_route"],
        },
        "finding_status": FINDING_STATUS_REVIEW_REQUIRED if evidence_ledger else "no_evidence_available",
        "input_state": {
            "evidence_ledger_available": evidence_ledger is not None,
            "baseline_comparison_available": baseline_comparison_available,
            "hypothesis_tracker_available": hypothesis_tracker is not None,
        },
        "summary": {
            "supported_signal_count": len(supported_signals),
            "not_supported_signal_count": len(not_supported_signals),
            "unclear_signal_count": sum(1 for item in hypotheses if item.get("status") == UNCLEAR),
            "not_assessed_count": sum(1 for item in hypotheses if item.get("status") == NOT_ASSESSED),
        },
        "supported_signals": supported_signals,
        "not_supported_signals": not_supported_signals,
        "unclear_items": unclear_items,
        "recommended_human_checks": checks,
        "non_goals": NON_GOALS,
        "safety_notes": SAFETY_NOTES,
        "artifacts": artifacts,
        "authority_boundary": AUTHORITY_BOUNDARY,
    }


def write_investigation_findings(
    *,
    output_dir: str | Path,
    issue_statement: str | None,
    classification: dict[str, Any],
    hypothesis_tracker: dict[str, Any],
    evidence_ledger: dict[str, Any],
    artifacts: dict[str, str | None],
    baseline_comparison_available: bool,
) -> Path:
    """Write the investigation findings JSON artifact."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    findings_path = output_path / FINDINGS_FILENAME
    findings = build_investigation_findings(
        issue_statement=issue_statement,
        classification=classification,
        hypothesis_tracker=hypothesis_tracker,
        evidence_ledger=evidence_ledger,
        artifacts=artifacts,
        baseline_comparison_available=baseline_comparison_available,
    )
    findings_path.write_text(json.dumps(findings, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return findings_path


def _supported_signals(hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals = []
    for index, hypothesis in enumerate(
        [item for item in hypotheses if item.get("status") == SUPPORTED], start=1
    ):
        signals.append(
            {
                "signal_id": f"sig-{index:03d}",
                "statement": f"Evidence-supported signal: {hypothesis['statement']}",
                "basis": f"Mapped from supported hypothesis {hypothesis['hypothesis_id']}.",
                "related_hypotheses": [hypothesis["hypothesis_id"]],
                "related_evidence_ids": list(hypothesis.get("supporting_evidence_ids", [])),
                "human_review_required": True,
            }
        )
    return signals


def _not_supported_signals(hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals = []
    for index, hypothesis in enumerate(
        [item for item in hypotheses if item.get("status") == NOT_SUPPORTED], start=1
    ):
        signals.append(
            {
                "signal_id": f"notsup-{index:03d}",
                "statement": f"Not supported by current evidence: {hypothesis['statement']}",
                "basis": f"Mapped from not-supported hypothesis {hypothesis['hypothesis_id']}.",
                "related_hypotheses": [hypothesis["hypothesis_id"]],
                "related_evidence_ids": list(hypothesis.get("contradicting_evidence_ids", [])),
                "human_review_required": True,
            }
        )
    return signals


def _unclear_items(hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for index, hypothesis in enumerate(
        [item for item in hypotheses if item.get("status") in {UNCLEAR, NOT_ASSESSED}], start=1
    ):
        checks = list(hypothesis.get("recommended_human_checks", []))
        items.append(
            {
                "item_id": f"unc-{index:03d}",
                "statement": f"Unclear: {hypothesis['statement']}",
                "reason": str(hypothesis.get("rationale", "Aggregate evidence does not resolve this item.")),
                "related_hypotheses": [hypothesis["hypothesis_id"]],
                "related_evidence_ids": list(hypothesis.get("inconclusive_evidence_ids", [])),
                "recommended_human_check": checks[0] if checks else "Review the related aggregate evidence with business context.",
            }
        )
    return items


def _generic_unclear_items(*, start: int) -> list[dict[str, Any]]:
    return [
        {
            "item_id": f"unc-{index:03d}",
            "statement": statement,
            "reason": reason,
            "recommended_human_check": check,
        }
        for index, (statement, reason, check) in enumerate(GENERIC_UNCLEAR_ITEMS, start=start)
    ]


def _hypothesis_checks(hypotheses: list[dict[str, Any]]):
    for hypothesis in hypotheses:
        yield from hypothesis.get("recommended_human_checks", [])


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output = []
    for value in values:
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output
