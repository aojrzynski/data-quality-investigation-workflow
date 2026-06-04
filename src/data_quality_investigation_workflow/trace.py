"""Investigation trace artifact builders and writers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from data_quality_investigation_workflow import __version__

if TYPE_CHECKING:
    from data_quality_investigation_workflow.intake import LoadedDataset

TOOL_NAME = "Data Quality Investigation Workflow"
TRACE_FILENAME = "investigation_trace.json"
DATASET_PROFILE_FILENAME = "dataset_profile.json"

IMPLEMENTED_SCOPE = [
    "CLI entry point",
    "output directory creation",
    "scaffold trace artifact",
    "local CSV/XLSX/XLSM dataset intake",
    "safe aggregate dataset profiling",
]

NOT_YET_IMPLEMENTED = [
    "issue classification",
    "investigation case file",
    "investigation planning",
    "route selection",
    "deterministic issue checks",
    "evidence ledger",
    "hypothesis tracking",
    "baseline comparison",
    "Markdown investigation report",
    "optional LLM notes",
]

AUTHORITY_BOUNDARY = [
    "Profiling is not investigation.",
    "The profile does not confirm the reported issue.",
    "The profile does not identify root cause.",
    "This tool does not approve, fix, certify, or trust a dataset.",
    "This tool does not make legal, compliance, privacy, or governance verdicts.",
    "No raw rows are written to artifacts.",
    "No raw rows are sent to an LLM.",
    "Human review remains the final authority.",
]


def build_scaffold_trace(issue_statement: str | None, trace_path: Path) -> dict[str, Any]:
    """Build the scaffold-only investigation trace payload."""
    return {
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": "scaffold",
        "stage": "repo_scaffold",
        "run_timestamp_utc": datetime.now(UTC).isoformat(),
        "issue_statement": issue_statement,
        "implemented_scope": IMPLEMENTED_SCOPE,
        "not_yet_implemented": NOT_YET_IMPLEMENTED,
        "artifacts": {
            "investigation_trace": trace_path.as_posix(),
        },
        "authority_boundary": AUTHORITY_BOUNDARY,
    }


def build_profiled_trace(
    *,
    issue_statement: str | None,
    loaded_dataset: "LoadedDataset",
    profile_path: Path,
    trace_path: Path,
) -> dict[str, Any]:
    """Build a trace payload for a run that produced a dataset profile."""
    return {
        "tool_name": TOOL_NAME,
        "package_version": __version__,
        "status": "profiled",
        "stage": "dataset_profiled",
        "run_timestamp_utc": datetime.now(UTC).isoformat(),
        "issue_statement": issue_statement,
        "implemented_scope": IMPLEMENTED_SCOPE,
        "not_yet_implemented": NOT_YET_IMPLEMENTED,
        "dataset": {
            "input_file_name": loaded_dataset.file_name,
            "file_extension": loaded_dataset.file_extension,
            "sheet_name": loaded_dataset.sheet_name,
            "row_count": loaded_dataset.row_count,
            "column_count": loaded_dataset.column_count,
        },
        "artifacts": {
            "dataset_profile": profile_path.as_posix(),
            "investigation_trace": trace_path.as_posix(),
        },
        "authority_boundary": AUTHORITY_BOUNDARY,
    }


def write_scaffold_trace(output_dir: str | Path, issue_statement: str | None) -> Path:
    """Create the output directory and write the scaffold trace JSON artifact."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    trace_path = output_path / TRACE_FILENAME
    trace = build_scaffold_trace(issue_statement=issue_statement, trace_path=trace_path)
    _write_json(trace_path, trace)
    return trace_path


def write_profiled_trace(
    *,
    output_dir: str | Path,
    issue_statement: str | None,
    loaded_dataset: "LoadedDataset",
    profile_path: Path,
) -> Path:
    """Create the output directory and write a profiled-run trace artifact."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    trace_path = output_path / TRACE_FILENAME
    trace = build_profiled_trace(
        issue_statement=issue_statement,
        loaded_dataset=loaded_dataset,
        profile_path=profile_path,
        trace_path=trace_path,
    )
    _write_json(trace_path, trace)
    return trace_path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
