from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "data_quality_investigation_workflow.cli", *args],
        check=False,
        text=True,
        capture_output=True,
    )


def test_cli_help_exits_successfully() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert "--issue" in result.stdout
    assert "--output-dir" in result.stdout


def test_cli_version_exits_successfully() -> None:
    result = run_cli("--version")

    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def test_cli_writes_trace_with_issue_statement(tmp_path: Path) -> None:
    output_dir = tmp_path / "scaffold_run"
    issue = "Customer IDs have started duplicating"

    result = run_cli("--issue", issue, "--output-dir", str(output_dir))

    trace_path = output_dir / "investigation_trace.json"
    assert result.returncode == 0
    assert trace_path.exists()
    assert trace_path.as_posix() in result.stdout

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["issue_statement"] == issue
    assert trace["status"] == "scaffold"
    assert trace["stage"] == "repo_scaffold"
    assert "scaffold trace artifact" in trace["implemented_scope"]
    assert "dataset intake" in trace["not_yet_implemented"]
    assert "deterministic checks" in trace["not_yet_implemented"]
    assert "Human review remains the final authority." in trace["authority_boundary"]


def test_cli_writes_scaffold_only_trace_without_issue(tmp_path: Path) -> None:
    output_dir = tmp_path / "scaffold_run"

    result = run_cli("--output-dir", str(output_dir))

    trace = json.loads((output_dir / "investigation_trace.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert trace["issue_statement"] is None
    assert trace["status"] == "scaffold"
    assert "issue classification" in trace["not_yet_implemented"]
    assert "This scaffold does not investigate data quality issues." in trace[
        "authority_boundary"
    ]


def test_installed_console_script_writes_trace(tmp_path: Path) -> None:
    output_dir = tmp_path / "console_script_run"
    issue = "Nulls increased in the customer email field"

    result = subprocess.run(
        [
            "dq-investigate",
            "--issue",
            issue,
            "--output-dir",
            str(output_dir),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    trace_path = output_dir / "investigation_trace.json"
    assert result.returncode == 0
    assert trace_path.exists()
    assert json.loads(trace_path.read_text(encoding="utf-8"))["issue_statement"] == issue
