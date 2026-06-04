"""Markdown investigation report builders and writers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

REPORT_FILENAME = "investigation_report.md"
REPORT_SECTION_COUNT = 10

_REPORT_LIMITATIONS = [
    "Evidence is aggregate-only and deterministic.",
    "Raw rows, sampled records, value lists, repeated-value details, and row numbers are not included.",
    "The report does not determine root cause.",
    "The report does not approve, fix, certify, or trust the dataset.",
    "The report does not make legal, compliance, privacy, or governance verdicts.",
    "This deterministic report is not LLM-generated and remains separate from optional LLM notes.",
    "Human review remains the final authority.",
]

_SCALAR_TYPES = (str, int, float, bool)
_MAX_METRICS_PER_ITEM = 4


def build_investigation_report(
    *,
    investigation_case: dict[str, Any],
    dataset_profile: dict[str, Any],
    investigation_plan: dict[str, Any],
    evidence_ledger: dict[str, Any],
    hypothesis_tracker: dict[str, Any],
    investigation_findings: dict[str, Any],
    artifacts: dict[str, str | None],
    baseline_profile: dict[str, Any] | None = None,
    baseline_comparison: dict[str, Any] | None = None,
) -> str:
    """Build a plain Markdown report from already-created safe artifacts."""
    lines: list[str] = []
    lines.extend(_opening())
    lines.extend(_issue_summary(investigation_findings, investigation_plan))
    lines.extend(
        _run_context(
            investigation_case, dataset_profile, baseline_profile, baseline_comparison
        )
    )
    lines.extend(_artifact_map(artifacts))
    lines.extend(_evidence_summary(evidence_ledger))
    lines.extend(_hypothesis_summary(hypothesis_tracker))
    lines.extend(_findings_summary(investigation_findings))
    lines.extend(_limitations())
    lines.extend(_next_steps(investigation_findings))
    return "\n".join(lines).rstrip() + "\n"


def write_investigation_report(
    *,
    output_dir: str | Path,
    investigation_case: dict[str, Any],
    dataset_profile: dict[str, Any],
    investigation_plan: dict[str, Any],
    evidence_ledger: dict[str, Any],
    hypothesis_tracker: dict[str, Any],
    investigation_findings: dict[str, Any],
    artifacts: dict[str, str | None],
    baseline_profile: dict[str, Any] | None = None,
    baseline_comparison: dict[str, Any] | None = None,
) -> Path:
    """Write the Markdown investigation report."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_path = output_path / REPORT_FILENAME
    report = build_investigation_report(
        investigation_case=investigation_case,
        dataset_profile=dataset_profile,
        baseline_profile=baseline_profile,
        investigation_plan=investigation_plan,
        baseline_comparison=baseline_comparison,
        evidence_ledger=evidence_ledger,
        hypothesis_tracker=hypothesis_tracker,
        investigation_findings=investigation_findings,
        artifacts=artifacts,
    )
    report_path.write_text(report, encoding="utf-8")
    return report_path


def build_report_metadata(
    *,
    report_path: Path,
    hypothesis_tracker: dict[str, Any],
    investigation_findings: dict[str, Any],
) -> dict[str, Any]:
    """Build concise trace metadata for a written Markdown report."""
    return {
        "report_artifact": report_path.as_posix(),
        "report_written": True,
        "report_section_count": REPORT_SECTION_COUNT,
        "finding_status": investigation_findings.get("finding_status"),
        "hypothesis_count": len(hypothesis_tracker.get("hypotheses", [])),
        "supported_signal_count": investigation_findings.get("summary", {}).get(
            "supported_signal_count", 0
        ),
    }


def _opening() -> list[str]:
    return [
        "# Data Quality Investigation Report",
        "",
        "This report summarizes deterministic, aggregate-only investigation artifacts created by Data Quality Investigation Workflow.",
        "",
        "It supports human review. It does not determine root cause, approve the dataset, certify the dataset, or make legal, compliance, privacy, or governance verdicts.",
        "",
        "Human review remains the final authority.",
        "",
    ]


def _issue_summary(findings: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    issue = findings.get("issue", {})
    route = plan.get("route", {})
    return [
        "## Issue summary",
        "",
        f"- Issue statement: {_text(issue.get('statement'))}",
        f"- Issue type: `{_text(issue.get('issue_type'))}`",
        f"- Selected route: `{_text(issue.get('selected_route') or route.get('route_name'))}`",
        f"- Finding status: `{_text(findings.get('finding_status'))}`",
        "",
    ]


def _run_context(
    case: dict[str, Any],
    profile: dict[str, Any],
    baseline_profile: dict[str, Any] | None,
    baseline_comparison: dict[str, Any] | None,
) -> list[str]:
    dataset = case.get("dataset_reference", {})
    baseline = case.get("baseline_reference", {})
    profile_dataset = profile.get("dataset", {})
    baseline_dataset = baseline_profile.get("dataset", {}) if baseline_profile else {}
    baseline_available = baseline_comparison is not None
    return [
        "## Run context",
        "",
        "| Context | Value |",
        "| --- | --- |",
        f"| Current dataset file | {_cell(dataset.get('file_name'))} |",
        f"| Current row count | {_cell(dataset.get('row_count', profile_dataset.get('row_count')))} |",
        f"| Current column count | {_cell(dataset.get('column_count', profile_dataset.get('column_count')))} |",
        f"| Baseline dataset file | {_cell(baseline.get('file_name'))} |",
        f"| Baseline row count | {_cell(baseline.get('row_count', baseline_dataset.get('row_count')))} |",
        f"| Baseline column count | {_cell(baseline.get('column_count', baseline_dataset.get('column_count')))} |",
        f"| Baseline comparison available | {_cell(baseline_available)} |",
        "",
    ]


def _artifact_map(artifacts: dict[str, str | None]) -> list[str]:
    order = [
        "investigation_case",
        "dataset_profile",
        "baseline_profile",
        "investigation_plan",
        "baseline_comparison",
        "evidence_ledger",
        "hypothesis_tracker",
        "investigation_findings",
        "investigation_report",
        "investigation_trace",
    ]
    lines = [
        "## Artifact map",
        "",
        "| Artifact | Path |",
        "| --- | --- |",
    ]
    for key in order:
        value = artifacts.get(key)
        if value is not None:
            lines.append(f"| `{key}` | `{_cell(value)}` |")
    lines.append("")
    return lines


def _evidence_summary(ledger: dict[str, Any]) -> list[str]:
    execution = ledger.get("execution", {})
    items = list(ledger.get("evidence_items", []))
    lines = [
        "## Evidence summary",
        "",
        f"- Evidence item count: {_text(execution.get('evidence_item_count', len(items)))}",
        f"- Checks executed count: {_text(execution.get('checks_executed_count'))}",
        f"- Checks not run count: {_text(execution.get('checks_not_run_count'))}",
        f"- Baseline available: {_text(execution.get('baseline_available'))}",
        "",
        "| Evidence ID | Check | Signal | Strength | Related columns | Summary |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in items:
        lines.append(
            "| {evidence_id} | {check_name} | {signal} | {strength} | {columns} | {summary} |".format(
                evidence_id=_cell(item.get("evidence_id")),
                check_name=_cell(item.get("check_name")),
                signal=_cell(item.get("signal")),
                strength=_cell(item.get("signal_strength")),
                columns=_cell(_join(item.get("related_columns", []))),
                summary=_cell(item.get("summary")),
            )
        )
    lines.append("")
    metrics = _safe_metric_rows(items)
    if metrics:
        lines.extend(
            [
                "### Key aggregate metrics",
                "",
                "| Evidence ID | Metric | Value |",
                "| --- | --- | --- |",
            ]
        )
        for evidence_id, key, value in metrics:
            lines.append(f"| {_cell(evidence_id)} | `{_cell(key)}` | {_cell(value)} |")
        lines.append("")
    return lines


def _hypothesis_summary(tracker: dict[str, Any]) -> list[str]:
    summary = tracker.get("hypothesis_summary", {})
    hypotheses = list(tracker.get("hypotheses", []))
    lines = [
        "## Hypothesis summary",
        "",
        "| Status | Count |",
        "| --- | --- |",
    ]
    for status in [
        "supported_by_evidence",
        "not_supported_by_evidence",
        "unclear",
        "not_assessed",
    ]:
        lines.append(f"| `{status}` | {_cell(summary.get(status, 0))} |")
    lines.extend(
        [
            "",
            "| Hypothesis ID | Status | Signal level | Statement | Supporting evidence | Contradicting evidence | Inconclusive evidence | Rationale |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in hypotheses:
        lines.append(
            "| {hypothesis_id} | {status} | {level} | {statement} | {supporting} | {contradicting} | {inconclusive} | {rationale} |".format(
                hypothesis_id=_cell(item.get("hypothesis_id")),
                status=_cell(item.get("status")),
                level=_cell(item.get("signal_level")),
                statement=_cell(item.get("statement")),
                supporting=_cell(_join(item.get("supporting_evidence_ids", []))),
                contradicting=_cell(_join(item.get("contradicting_evidence_ids", []))),
                inconclusive=_cell(_join(item.get("inconclusive_evidence_ids", []))),
                rationale=_cell(item.get("rationale")),
            )
        )
    lines.append("")
    return lines


def _findings_summary(findings: dict[str, Any]) -> list[str]:
    lines = ["## Findings summary", ""]
    lines.extend(
        _finding_table(
            "Evidence-supported signals", findings.get("supported_signals", [])
        )
    )
    lines.extend(
        _finding_table(
            "Not supported by current evidence",
            findings.get("not_supported_signals", []),
        )
    )
    lines.extend(_unclear_table(findings.get("unclear_items", [])))
    lines.extend(_checks_table(findings.get("recommended_human_checks", [])))
    return lines


def _finding_table(heading: str, items: list[dict[str, Any]]) -> list[str]:
    lines = [f"### {heading}", ""]
    if not items:
        return [*lines, "No items were summarized for this section.", ""]
    lines.extend(["| Signal ID | Statement | Evidence IDs |", "| --- | --- | --- |"])
    for item in items:
        lines.append(
            "| {signal_id} | {statement} | {evidence_ids} |".format(
                signal_id=_cell(item.get("signal_id")),
                statement=_cell(item.get("statement")),
                evidence_ids=_cell(_join(item.get("related_evidence_ids", []))),
            )
        )
    lines.append("")
    return lines


def _unclear_table(items: list[dict[str, Any]]) -> list[str]:
    lines = ["### Unclear items", ""]
    if not items:
        return [*lines, "No unclear items were summarized.", ""]
    lines.extend(
        ["| Item ID | Statement | Reason | Human check |", "| --- | --- | --- | --- |"]
    )
    for item in items:
        lines.append(
            "| {item_id} | {statement} | {reason} | {check} |".format(
                item_id=_cell(item.get("item_id")),
                statement=_cell(item.get("statement")),
                reason=_cell(item.get("reason")),
                check=_cell(item.get("recommended_human_check")),
            )
        )
    lines.append("")
    return lines


def _checks_table(checks: list[str]) -> list[str]:
    lines = ["### Recommended human review checks", ""]
    unique_checks = _dedupe(checks)
    if not unique_checks:
        return [*lines, "No recommended human checks were summarized.", ""]
    lines.extend(["| # | Check |", "| --- | --- |"])
    for index, check in enumerate(unique_checks, start=1):
        lines.append(f"| {index} | {_cell(check)} |")
    lines.append("")
    return lines


def _limitations() -> list[str]:
    lines = ["## Limitations and authority boundary", ""]
    lines.extend(f"- {item}" for item in _REPORT_LIMITATIONS)
    lines.append("")
    return lines


def _next_steps(findings: dict[str, Any]) -> list[str]:
    checks = _dedupe(list(findings.get("recommended_human_checks", [])))
    lines = ["## Next steps", ""]
    if not checks:
        lines.append(
            "- Review the JSON artifacts and decide which additional checks are needed."
        )
    else:
        lines.extend(f"- {check}" for check in checks)
    lines.append("")
    return lines


def _safe_metric_rows(items: list[dict[str, Any]]) -> list[tuple[str, str, Any]]:
    rows: list[tuple[str, str, Any]] = []
    for item in items:
        evidence_id = str(item.get("evidence_id", "not_available"))
        metrics = item.get("metrics", {})
        if not isinstance(metrics, dict):
            continue
        count = 0
        for key, value in metrics.items():
            if count >= _MAX_METRICS_PER_ITEM:
                break
            if _is_safe_metric(key, value):
                rows.append((evidence_id, str(key), value))
                count += 1
    return rows


def _is_safe_metric(key: str, value: Any) -> bool:
    forbidden_fragments = {
        "raw",
        "sample",
        "preview",
        "category_label",
        "distribution",
        "row_number",
        "failing_record",
    }
    key_folded = key.casefold()
    return isinstance(value, _SCALAR_TYPES) and not any(
        fragment in key_folded for fragment in forbidden_fragments
    )


def _join(values: Any) -> str:
    if not values:
        return "None"
    if isinstance(values, list):
        return ", ".join(str(value) for value in values) if values else "None"
    return str(values)


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _cell(value: Any) -> str:
    text = _report_safe_text(_text(value))
    return text.replace("|", "\\|").replace("\n", " ")


def _text(value: Any) -> str:
    if value is None:
        return "Not available"
    return str(value)


def _report_safe_text(text: str) -> str:
    replacements = {
        "Root cause remains unclear.": "Cause remains undetermined.",
        "root cause remains unclear.": "cause remains undetermined.",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text
