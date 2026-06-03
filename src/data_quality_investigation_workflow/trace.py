"""Scaffold trace artifact writer for the initial repository setup."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from data_quality_investigation_workflow import __version__

TOOL_NAME = "Data Quality Investigation Workflow"
TRACE_FILENAME = "investigation_trace.json"

IMPLEMENTED_SCOPE = [
    "CLI entry point",
    "output directory creation",
    "scaffold trace artifact",
]

NOT_YET_IMPLEMENTED = [
    "dataset intake",
    "issue classification",
    "investigation planning",
    "deterministic checks",
    "evidence ledger",
    "hypothesis tracking",
    "baseline comparison",
    "Markdown investigation report",
    "optional LLM notes",
]

AUTHORITY_BOUNDARY = [
    "This scaffold does not investigate data quality issues.",
    "This scaffold does not confirm root cause.",
    "This scaffold does not approve, fix, or certify a dataset.",
    "This scaffold does not make legal, compliance, privacy, or governance verdicts.",
    "This scaffold does not send raw rows to an LLM.",
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


def write_scaffold_trace(output_dir: str | Path, issue_statement: str | None) -> Path:
    """Create the output directory and write the scaffold trace JSON artifact."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    trace_path = output_path / TRACE_FILENAME
    trace = build_scaffold_trace(issue_statement=issue_statement, trace_path=trace_path)
    trace_path.write_text(json.dumps(trace, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return trace_path
