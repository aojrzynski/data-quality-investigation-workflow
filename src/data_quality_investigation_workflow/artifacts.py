"""Helpers for consistent artifact reference maps.

The workflow writes a case file, profiles, a plan, an evidence ledger, a
report, and a trace. Those files refer to each other by path, so the path map is
centralized here instead of rebuilt slightly differently in each stage. Keeping
this map in one place avoids drift between case, plan, evidence, report, LLM,
and trace artifacts while preserving the existing artifact names.
"""

from __future__ import annotations

from pathlib import Path


def build_artifact_refs(
    *,
    case_path: Path,
    profile_path: Path,
    plan_path: Path,
    ledger_path: Path,
    trace_path: Path,
    baseline_profile_path: Path | None = None,
    baseline_comparison_path: Path | None = None,
    hypothesis_tracker_path: Path | None = None,
    findings_path: Path | None = None,
    report_path: Path | None = None,
) -> dict[str, str | None]:
    """Build the standard artifact path map used by downstream summaries.

    Each downstream artifact should point to the same case, plan, ledger, report,
    and trace paths. Passing paths through this helper avoids subtle naming drift
    when optional baseline or LLM artifacts are present.
    """
    artifacts: dict[str, str | None] = {
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
    if hypothesis_tracker_path is not None:
        artifacts["hypothesis_tracker"] = hypothesis_tracker_path.as_posix()
    if findings_path is not None:
        artifacts["investigation_findings"] = findings_path.as_posix()
    if report_path is not None:
        artifacts["investigation_report"] = report_path.as_posix()
    return artifacts
