from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

FORBIDDEN_KEYS = {
    "raw_rows",
    "sample_rows",
    "sampled_rows",
    "first_rows",
    "last_rows",
    "example_values",
    "examples",
    "top_values",
    "distinct_values",
    "value_preview",
    "value_previews",
    "raw_failing_records",
}


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


def test_cli_case_only_run_writes_case_and_trace(tmp_path: Path) -> None:
    output_dir = tmp_path / "case_run"
    issue = "Customer IDs have started duplicating"

    result = run_cli("--issue", issue, "--output-dir", str(output_dir))

    case_path = output_dir / "investigation_case.json"
    trace_path = output_dir / "investigation_trace.json"
    profile_path = output_dir / "dataset_profile.json"
    assert result.returncode == 0, result.stderr
    assert case_path.exists()
    assert trace_path.exists()
    assert not profile_path.exists()
    assert f"Investigation case written to {case_path.as_posix()}" in result.stdout
    assert f"Investigation trace written to {trace_path.as_posix()}" in result.stdout

    case = json.loads(case_path.read_text(encoding="utf-8"))
    assert case["artifact_type"] == "investigation_case"
    assert case["case_version"] == "0.1"
    assert case["case_id"].startswith("case-")
    assert case["issue"]["statement"] == issue
    assert case["issue"]["provided"] is True
    assert case["issue"]["classification_status"] == "not_classified"
    assert case["workflow"]["status"] == "case_created"
    assert case["workflow"]["stage"] == "investigation_case_created"
    assert case["dataset_reference"]["input_provided"] is False
    assert case["dataset_reference"]["profile_artifact"] is None
    assert case["artifacts"]["investigation_case"] == case_path.as_posix()
    assert case["artifacts"]["dataset_profile"] is None
    assert case["artifacts"]["investigation_trace"] == trace_path.as_posix()

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["issue_statement"] == issue
    assert trace["status"] == "case_created"
    assert trace["stage"] == "investigation_case_created"
    assert trace["artifacts"]["investigation_case"] == case_path.as_posix()
    assert trace["artifacts"]["investigation_trace"] == trace_path.as_posix()
    assert "safe aggregate dataset profiling" in trace["implemented_scope"]
    assert "investigation case file" in trace["implemented_scope"]
    assert "deterministic issue checks" in trace["not_yet_implemented"]
    assert "Human review remains the final authority." in trace["authority_boundary"]


def test_cli_profiled_case_run_writes_case_profile_and_trace(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "customer_case_profile"
    issue = "Customer IDs have started duplicating"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        issue,
        "--output-dir",
        str(output_dir),
    )

    case_path = output_dir / "investigation_case.json"
    profile_path = output_dir / "dataset_profile.json"
    trace_path = output_dir / "investigation_trace.json"
    assert result.returncode == 0, result.stderr
    assert case_path.exists()
    assert profile_path.exists()
    assert trace_path.exists()
    assert f"Investigation case written to {case_path.as_posix()}" in result.stdout
    assert f"Dataset profile written to {profile_path.as_posix()}" in result.stdout
    assert f"Investigation trace written to {trace_path.as_posix()}" in result.stdout

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    assert profile["source"]["file_name"] == "customer_quality_snapshot.csv"
    assert profile["source"]["file_extension"] == ".csv"
    assert profile["source"]["sheet_name"] is None
    assert profile["dataset"]["row_count"] == 12
    assert profile["dataset"]["column_count"] == 6

    case = json.loads(case_path.read_text(encoding="utf-8"))
    assert case["issue"]["statement"] == issue
    assert case["issue"]["classification_status"] == "not_classified"
    assert case["workflow"]["status"] == "case_profiled"
    assert case["workflow"]["stage"] == "dataset_profiled_case_created"
    assert case["dataset_reference"] == {
        "input_provided": True,
        "file_name": "customer_quality_snapshot.csv",
        "file_extension": ".csv",
        "sheet_name": None,
        "row_count": 12,
        "column_count": 6,
        "profile_artifact": profile_path.as_posix(),
    }
    assert case["artifacts"] == {
        "investigation_case": case_path.as_posix(),
        "dataset_profile": profile_path.as_posix(),
        "investigation_trace": trace_path.as_posix(),
    }

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["issue_statement"] == issue
    assert trace["status"] == "case_profiled"
    assert trace["stage"] == "dataset_profiled_case_created"
    assert trace["dataset"] == {
        "input_file_name": "customer_quality_snapshot.csv",
        "file_extension": ".csv",
        "sheet_name": None,
        "row_count": 12,
        "column_count": 6,
    }
    assert trace["artifacts"] == {
        "investigation_case": case_path.as_posix(),
        "dataset_profile": profile_path.as_posix(),
        "investigation_trace": trace_path.as_posix(),
    }
    assert "columns" not in trace
    assert "safety_notes" not in trace


def test_cli_writes_case_without_issue(tmp_path: Path) -> None:
    output_dir = tmp_path / "case_run"

    result = run_cli("--output-dir", str(output_dir))

    case = json.loads((output_dir / "investigation_case.json").read_text(encoding="utf-8"))
    trace = json.loads((output_dir / "investigation_trace.json").read_text(encoding="utf-8"))
    assert result.returncode == 0, result.stderr
    assert case["issue"]["provided"] is False
    assert case["issue"]["statement"] is None
    assert "No issue statement was provided" in case["issue"]["missing_issue_note"]
    assert case["issue"]["classification_status"] == "not_classified"
    assert trace["issue_statement"] is None
    assert trace["status"] == "case_created"
    assert "issue classification" in trace["not_yet_implemented"]


def test_investigation_case_does_not_include_raw_rows_or_value_previews(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "customer_case_profile"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        "Customer IDs have started duplicating",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    case = json.loads((output_dir / "investigation_case.json").read_text(encoding="utf-8"))
    assert _find_forbidden_keys(case) == []
    serialized = json.dumps(case)
    assert "avery@example.test" not in serialized
    assert "CUST-001" not in serialized


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

    output_dir = tmp_path / "excel_case_profile"
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
    case = json.loads((output_dir / "investigation_case.json").read_text(encoding="utf-8"))
    profile = json.loads((output_dir / "dataset_profile.json").read_text(encoding="utf-8"))
    assert case["dataset_reference"]["sheet_name"] == "Customers"
    assert case["dataset_reference"]["row_count"] == 2
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


def test_installed_console_script_writes_case_and_trace(tmp_path: Path) -> None:
    if shutil.which("dq-investigate") is None:
        pytest.skip("dq-investigate console script is not installed")

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

    case_path = output_dir / "investigation_case.json"
    trace_path = output_dir / "investigation_trace.json"
    assert result.returncode == 0, result.stderr
    assert case_path.exists()
    assert trace_path.exists()
    assert json.loads(case_path.read_text(encoding="utf-8"))["issue"]["statement"] == issue
    assert json.loads(trace_path.read_text(encoding="utf-8"))["issue_statement"] == issue


def _find_forbidden_keys(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS:
                found.append(key)
            found.extend(_find_forbidden_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_find_forbidden_keys(child))
    return found
