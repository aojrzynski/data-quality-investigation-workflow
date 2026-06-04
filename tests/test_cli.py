from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


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
    assert "--input" in result.stdout
    assert "--sheet" in result.stdout
    assert "--issue" in result.stdout
    assert "--output-dir" in result.stdout


def test_cli_version_exits_successfully() -> None:
    result = run_cli("--version")

    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def test_cli_with_input_writes_profile_and_trace(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "profile_run"
    issue = "Customer IDs have started duplicating"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        issue,
        "--output-dir",
        str(output_dir),
    )

    profile_path = output_dir / "dataset_profile.json"
    trace_path = output_dir / "investigation_trace.json"
    assert result.returncode == 0, result.stderr
    assert profile_path.exists()
    assert trace_path.exists()
    assert f"Dataset profile written to {profile_path.as_posix()}" in result.stdout
    assert f"Investigation trace written to {trace_path.as_posix()}" in result.stdout

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    assert profile["source"]["file_name"] == "customer_quality_snapshot.csv"
    assert profile["source"]["file_extension"] == ".csv"
    assert profile["source"]["sheet_name"] is None
    assert profile["dataset"]["row_count"] == 12
    assert profile["dataset"]["column_count"] == 6

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["issue_statement"] == issue
    assert trace["status"] == "profiled"
    assert trace["stage"] == "dataset_profiled"
    assert trace["dataset"] == {
        "input_file_name": "customer_quality_snapshot.csv",
        "file_extension": ".csv",
        "sheet_name": None,
        "row_count": 12,
        "column_count": 6,
    }
    assert "local CSV/XLSX/XLSM dataset intake" in trace["implemented_scope"]
    assert "dataset intake" not in trace["not_yet_implemented"]
    assert "deterministic issue checks" in trace["not_yet_implemented"]


def test_cli_without_input_preserves_scaffold_only_trace(tmp_path: Path) -> None:
    output_dir = tmp_path / "scaffold_run"
    issue = "Customer IDs have started duplicating"

    result = run_cli("--issue", issue, "--output-dir", str(output_dir))

    trace_path = output_dir / "investigation_trace.json"
    profile_path = output_dir / "dataset_profile.json"
    assert result.returncode == 0
    assert trace_path.exists()
    assert not profile_path.exists()
    assert trace_path.as_posix() in result.stdout

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["issue_statement"] == issue
    assert trace["status"] == "scaffold"
    assert trace["stage"] == "repo_scaffold"
    assert "safe aggregate dataset profiling" in trace["implemented_scope"]
    assert "deterministic issue checks" in trace["not_yet_implemented"]
    assert "Profiling is not investigation." in trace["authority_boundary"]
    assert "Human review remains the final authority." in trace["authority_boundary"]


def test_cli_writes_scaffold_only_trace_without_issue(tmp_path: Path) -> None:
    output_dir = tmp_path / "scaffold_run"

    result = run_cli("--output-dir", str(output_dir))

    trace = json.loads((output_dir / "investigation_trace.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert trace["issue_statement"] is None
    assert trace["status"] == "scaffold"
    assert "issue classification" in trace["not_yet_implemented"]


def test_cli_rejects_unsupported_file_extension(tmp_path: Path) -> None:
    unsupported = tmp_path / "customers.json"
    unsupported.write_text("[]", encoding="utf-8")

    result = run_cli("--input", str(unsupported), "--output-dir", str(tmp_path / "out"))

    assert result.returncode != 0
    assert "Unsupported input file extension" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_rejects_missing_input_file(tmp_path: Path) -> None:
    result = run_cli("--input", str(tmp_path / "missing.csv"), "--output-dir", str(tmp_path / "out"))

    assert result.returncode != 0
    assert "Input file does not exist" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_rejects_sheet_with_csv(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--sheet",
        "Sheet1",
        "--output-dir",
        str(tmp_path / "out"),
    )

    assert result.returncode != 0
    assert "--sheet can only be used with Excel files" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_profiles_excel_with_sheet(tmp_path: Path) -> None:
    pd = pytest.importorskip("pandas")
    workbook_path = tmp_path / "customers.xlsx"
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        pd.DataFrame({"customer_id": ["CUST-001", "CUST-002"], "value": [1, 2]}).to_excel(
            writer,
            sheet_name="Customers",
            index=False,
        )

    output_dir = tmp_path / "excel_profile"
    result = run_cli(
        "--input",
        str(workbook_path),
        "--sheet",
        "Customers",
        "--issue",
        "Nulls increased in the customer email field",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    profile = json.loads((output_dir / "dataset_profile.json").read_text(encoding="utf-8"))
    assert profile["source"]["sheet_name"] == "Customers"
    assert profile["dataset"]["row_count"] == 2


def test_cli_rejects_multi_sheet_excel_without_sheet(tmp_path: Path) -> None:
    pd = pytest.importorskip("pandas")
    workbook_path = tmp_path / "customers.xlsx"
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        pd.DataFrame({"id": [1]}).to_excel(writer, sheet_name="Customers", index=False)
        pd.DataFrame({"id": [2]}).to_excel(writer, sheet_name="Archive", index=False)

    result = run_cli("--input", str(workbook_path), "--output-dir", str(tmp_path / "out"))

    assert result.returncode != 0
    assert "Excel workbook contains multiple sheets" in result.stderr
    assert "Provide --sheet" in result.stderr
    assert "Traceback" not in result.stderr


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
