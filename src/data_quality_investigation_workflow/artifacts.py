"""Helpers for consistent artifact reference maps.

The workflow writes several small files in a fixed order. Keeping the common
reference map in one place reduces drift between the CLI and report-oriented
artifacts without changing artifact names.
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
    """Build the standard artifact path map used by downstream summaries."""
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
