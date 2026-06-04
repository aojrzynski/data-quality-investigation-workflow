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
    "row_numbers",
    "duplicated_values",
    "category_labels",
    "full_distribution",
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


def test_cli_case_plan_run_writes_case_plan_and_trace(tmp_path: Path) -> None:
    output_dir = tmp_path / "plan_run"
    issue = "Customer IDs have started duplicating"

    result = run_cli("--issue", issue, "--output-dir", str(output_dir))

    case_path = output_dir / "investigation_case.json"
    trace_path = output_dir / "investigation_trace.json"
    profile_path = output_dir / "dataset_profile.json"
    plan_path = output_dir / "investigation_plan.json"
    assert result.returncode == 0, result.stderr
    assert case_path.exists()
    assert trace_path.exists()
    assert plan_path.exists()
    ledger_path = output_dir / "evidence_ledger.json"
    assert not profile_path.exists()
    assert not ledger_path.exists()
    assert f"Investigation case written to {case_path.as_posix()}" in result.stdout
    assert f"Investigation plan written to {plan_path.as_posix()}" in result.stdout
    assert f"Investigation trace written to {trace_path.as_posix()}" in result.stdout

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["issue"]["issue_type"] == "duplicate_key"
    assert plan["route"]["route_name"] == "duplicate_key_investigation"
    assert all(check["status"] == "planned_not_run" for check in plan["planned_checks"])

    case = json.loads(case_path.read_text(encoding="utf-8"))
    assert case["artifact_type"] == "investigation_case"
    assert case["case_version"] == "0.1"
    assert case["case_id"].startswith("case-")
    assert case["issue"]["statement"] == issue
    assert case["issue"]["provided"] is True
    assert case["issue"]["classification_status"] == "classified_for_planning"
    assert case["issue"]["issue_type"] == "duplicate_key"
    assert case["issue"]["selected_route"] == "duplicate_key_investigation"
    assert case["workflow"]["status"] == "planned"
    assert case["workflow"]["stage"] == "investigation_plan_created"
    assert case["dataset_reference"]["input_provided"] is False
    assert case["dataset_reference"]["profile_artifact"] is None
    assert case["artifacts"]["investigation_case"] == case_path.as_posix()
    assert case["artifacts"]["dataset_profile"] is None
    assert case["artifacts"]["investigation_plan"] == plan_path.as_posix()
    assert case["artifacts"]["evidence_ledger"] is None
    assert case["artifacts"]["investigation_trace"] == trace_path.as_posix()

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["issue_statement"] == issue
    assert trace["status"] == "planned"
    assert trace["stage"] == "investigation_plan_created"
    assert trace["planning"]["issue_type"] == "duplicate_key"
    assert trace["planning"]["route_name"] == "duplicate_key_investigation"
    assert trace["artifacts"]["investigation_case"] == case_path.as_posix()
    assert trace["artifacts"]["investigation_plan"] == plan_path.as_posix()
    assert trace["artifacts"]["evidence_ledger"] is None
    assert trace["artifacts"]["investigation_trace"] == trace_path.as_posix()
    assert "safe aggregate dataset profiling" in trace["implemented_scope"]
    assert "investigation case file" in trace["implemented_scope"]
    assert "deterministic current-dataset issue checks" in trace["implemented_scope"]
    assert "Human review remains the final authority." in trace["authority_boundary"]


def test_cli_profiled_case_plan_run_writes_case_profile_plan_evidence_and_trace(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "customer_plan_profile"
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
    plan_path = output_dir / "investigation_plan.json"
    ledger_path = output_dir / "evidence_ledger.json"
    assert result.returncode == 0, result.stderr
    assert case_path.exists()
    assert profile_path.exists()
    assert trace_path.exists()
    assert plan_path.exists()
    assert ledger_path.exists()
    assert f"Investigation case written to {case_path.as_posix()}" in result.stdout
    assert f"Dataset profile written to {profile_path.as_posix()}" in result.stdout
    assert f"Investigation plan written to {plan_path.as_posix()}" in result.stdout
    assert f"Evidence ledger written to {ledger_path.as_posix()}" in result.stdout
    assert f"Investigation trace written to {trace_path.as_posix()}" in result.stdout

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    assert profile["source"]["file_name"] == "customer_quality_snapshot.csv"
    assert profile["source"]["file_extension"] == ".csv"
    assert profile["source"]["sheet_name"] is None
    assert profile["dataset"]["row_count"] == 12
    assert profile["dataset"]["column_count"] == 6

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["inputs"]["dataset_profile_available"] is True
    assert plan["dataset_context"]["input_file_name"] == "customer_quality_snapshot.csv"
    assert plan["dataset_context"]["row_count"] == 12
    assert {
        column["name"] for column in plan["dataset_context"]["candidate_columns"]
    } >= {"customer_id"}

    case = json.loads(case_path.read_text(encoding="utf-8"))
    assert case["issue"]["statement"] == issue
    assert case["issue"]["classification_status"] == "classified_for_planning"
    assert case["issue"]["issue_type"] == "duplicate_key"
    assert case["issue"]["selected_route"] == "duplicate_key_investigation"
    assert case["workflow"]["status"] == "report_written"
    assert case["workflow"]["stage"] == "markdown_report_created"
    assert case["dataset_reference"] == {
        "input_provided": True,
        "file_name": "customer_quality_snapshot.csv",
        "file_extension": ".csv",
        "sheet_name": None,
        "row_count": 12,
        "column_count": 6,
        "profile_artifact": profile_path.as_posix(),
    }
    assert case["artifacts"]["investigation_case"] == case_path.as_posix()
    assert case["artifacts"]["dataset_profile"] == profile_path.as_posix()
    assert case["artifacts"]["investigation_plan"] == plan_path.as_posix()
    assert case["artifacts"]["evidence_ledger"] == ledger_path.as_posix()
    assert (
        case["artifacts"]["hypothesis_tracker"]
        == (output_dir / "hypothesis_tracker.json").as_posix()
    )
    assert (
        case["artifacts"]["investigation_findings"]
        == (output_dir / "investigation_findings.json").as_posix()
    )
    assert (
        case["artifacts"]["investigation_report"]
        == (output_dir / "investigation_report.md").as_posix()
    )
    assert case["artifacts"]["investigation_trace"] == trace_path.as_posix()

    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["issue_statement"] == issue
    assert trace["status"] == "report_written"
    assert trace["stage"] == "markdown_report_created"
    assert trace["planning"]["issue_type"] == "duplicate_key"
    assert trace["planning"]["route_name"] == "duplicate_key_investigation"
    assert trace["dataset"] == {
        "input_file_name": "customer_quality_snapshot.csv",
        "file_extension": ".csv",
        "sheet_name": None,
        "row_count": 12,
        "column_count": 6,
    }
    assert trace["artifacts"]["investigation_case"] == case_path.as_posix()
    assert trace["artifacts"]["dataset_profile"] == profile_path.as_posix()
    assert trace["artifacts"]["investigation_plan"] == plan_path.as_posix()
    assert trace["artifacts"]["evidence_ledger"] == ledger_path.as_posix()
    assert (
        trace["artifacts"]["hypothesis_tracker"]
        == (output_dir / "hypothesis_tracker.json").as_posix()
    )
    assert (
        trace["artifacts"]["investigation_findings"]
        == (output_dir / "investigation_findings.json").as_posix()
    )
    assert (
        trace["artifacts"]["investigation_report"]
        == (output_dir / "investigation_report.md").as_posix()
    )
    assert trace["artifacts"]["investigation_trace"] == trace_path.as_posix()
    assert "columns" not in trace
    assert "safety_notes" not in trace


def test_cli_writes_case_plan_and_trace_without_issue(tmp_path: Path) -> None:
    output_dir = tmp_path / "plan_run"

    result = run_cli("--output-dir", str(output_dir))

    case = json.loads(
        (output_dir / "investigation_case.json").read_text(encoding="utf-8")
    )
    plan = json.loads(
        (output_dir / "investigation_plan.json").read_text(encoding="utf-8")
    )
    trace = json.loads(
        (output_dir / "investigation_trace.json").read_text(encoding="utf-8")
    )
    assert result.returncode == 0, result.stderr
    assert case["issue"]["provided"] is False
    assert case["issue"]["statement"] is None
    assert "No issue statement was provided" in case["issue"]["missing_issue_note"]
    assert case["issue"]["classification_status"] == "missing_issue_statement"
    assert case["issue"]["issue_type"] == "missing_issue_statement"
    assert case["issue"]["selected_route"] == "missing_issue_statement"
    assert plan["issue"]["issue_type"] == "missing_issue_statement"
    assert plan["route"]["route_name"] == "missing_issue_statement"
    assert plan["planned_checks"] == []
    assert trace["issue_statement"] is None
    assert trace["status"] == "plan_not_ready"
    assert trace["stage"] == "missing_issue_statement"
    assert trace["planning"]["issue_type"] == "missing_issue_statement"


def test_investigation_case_does_not_include_raw_rows_or_value_previews(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "customer_plan_profile"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        "Customer IDs have started duplicating",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    case = json.loads(
        (output_dir / "investigation_case.json").read_text(encoding="utf-8")
    )
    assert _find_forbidden_keys(case) == []
    serialized = json.dumps(case)
    assert "avery@example.test" not in serialized
    assert "CUST-001" not in serialized


def test_investigation_plan_does_not_include_raw_rows_values_or_findings(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "customer_plan_profile"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        "Customer IDs have started duplicating",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    plan = json.loads(
        (output_dir / "investigation_plan.json").read_text(encoding="utf-8")
    )
    assert _find_forbidden_keys(plan) == []
    serialized = json.dumps(plan)
    assert "avery@example.test" not in serialized
    assert "CUST-001" not in serialized
    assert "confirmed_findings" not in serialized
    assert "root_cause" not in serialized
    assert plan["artifacts"]["evidence_ledger"] is not None


def test_cli_rejects_unsupported_file_extension(tmp_path: Path) -> None:
    unsupported = tmp_path / "customers.json"
    unsupported.write_text("[]", encoding="utf-8")

    result = run_cli("--input", str(unsupported), "--output-dir", str(tmp_path / "out"))

    assert result.returncode != 0
    assert "Unsupported input file extension" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_rejects_missing_input_file(tmp_path: Path) -> None:
    result = run_cli(
        "--input", str(tmp_path / "missing.csv"), "--output-dir", str(tmp_path / "out")
    )

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
        pd.DataFrame(
            {"customer_id": ["CUST-001", "CUST-002"], "value": [1, 2]}
        ).to_excel(
            writer,
            sheet_name="Customers",
            index=False,
        )

    output_dir = tmp_path / "excel_plan_profile"
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
    case = json.loads(
        (output_dir / "investigation_case.json").read_text(encoding="utf-8")
    )
    profile = json.loads(
        (output_dir / "dataset_profile.json").read_text(encoding="utf-8")
    )
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

    result = run_cli(
        "--input", str(workbook_path), "--output-dir", str(tmp_path / "out")
    )

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
    assert (
        json.loads(case_path.read_text(encoding="utf-8"))["issue"]["statement"] == issue
    )
    assert (
        json.loads(trace_path.read_text(encoding="utf-8"))["issue_statement"] == issue
    )


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


def test_duplicate_key_evidence_ledger_records_aggregate_signal(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "customer_evidence_run"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        "Customer IDs have started duplicating",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    ledger = json.loads(
        (output_dir / "evidence_ledger.json").read_text(encoding="utf-8")
    )
    assert ledger["issue"]["issue_type"] == "duplicate_key"
    assert ledger["issue"]["selected_route"] == "duplicate_key_investigation"
    assert ledger["evidence_items"]
    assert any(
        "customer_id" in item["related_columns"] for item in ledger["evidence_items"]
    )
    duplicate_item = next(
        item
        for item in ledger["evidence_items"]
        if item["check_id"] == "duplicate_key_summary"
    )
    assert duplicate_item["signal"] == "present"
    assert duplicate_item["metrics"]["columns_with_duplicate_non_null_values"] >= 1
    assert duplicate_item["metrics"]["max_duplicate_value_count"] >= 1
    serialized = json.dumps(ledger)
    assert "CUST-001" not in serialized
    assert "CUST-010" not in serialized


def test_missing_issue_with_input_writes_not_executed_ledger(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "missing_issue_evidence"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    ledger = json.loads(
        (output_dir / "evidence_ledger.json").read_text(encoding="utf-8")
    )
    assert ledger["execution"]["status"] == "not_executed"
    assert ledger["evidence_items"] == []
    assert "No issue statement was supplied" in ledger["execution"]["reason"]


def test_null_issue_evidence_is_current_only(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "null_evidence"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        "Nulls increased in the customer email field",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    ledger = json.loads(
        (output_dir / "evidence_ledger.json").read_text(encoding="utf-8")
    )
    assert ledger["issue"]["selected_route"] == "null_increase_investigation"
    item = ledger["evidence_items"][0]
    assert item["check_id"] == "current_null_summary"
    assert (
        "baseline is required for current-vs-baseline increase evidence"
        in item["summary"]
    )
    assert item["metrics"]["total_null_cells"] >= 1
    assert "baseline_delta" not in json.dumps(item)


def test_date_gap_evidence_uses_aggregate_period_metrics(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "date_evidence"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        "A date gap appeared in the signup_date field",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    ledger = json.loads(
        (output_dir / "evidence_ledger.json").read_text(encoding="utf-8")
    )
    assert ledger["issue"]["selected_route"] == "date_gap_investigation"
    gap_item = next(
        item
        for item in ledger["evidence_items"]
        if item["check_id"] == "date_gap_summary"
    )
    assert "min_date" in gap_item["metrics"]
    assert "max_date" in gap_item["metrics"]
    assert "missing_daily_period_count" in gap_item["metrics"]
    assert "missing_dates" not in json.dumps(ledger)


def test_schema_route_evidence_is_current_schema_only(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "schema_evidence"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        "Header changed in the customer file",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    ledger = json.loads(
        (output_dir / "evidence_ledger.json").read_text(encoding="utf-8")
    )
    assert ledger["issue"]["selected_route"] == "schema_change_investigation"
    item = ledger["evidence_items"][0]
    assert item["check_id"] == "current_schema_summary"
    assert "inferred_kind_counts" in item["metrics"]
    assert ledger["execution"]["baseline_available"] is False


def test_evidence_ledger_safety_boundaries(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "safe_evidence"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        "Customer IDs have started duplicating",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    ledger = json.loads(
        (output_dir / "evidence_ledger.json").read_text(encoding="utf-8")
    )
    assert _find_forbidden_keys(ledger) == []
    serialized = json.dumps(ledger)
    assert "avery@example.test" not in serialized
    assert "CUST-001" not in serialized
    assert "root_cause" not in serialized
    assert "final_finding" not in serialized
    assert "confirmed_findings" not in serialized
    assert "hypothesis_tracker" not in serialized


def test_trace_evidence_metadata_is_concise(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "trace_evidence"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        "Customer IDs have started duplicating",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    trace = json.loads(
        (output_dir / "investigation_trace.json").read_text(encoding="utf-8")
    )
    assert (
        trace["artifacts"]["evidence_ledger"]
        == (output_dir / "evidence_ledger.json").as_posix()
    )
    assert trace["evidence"]["evidence_item_count"] >= 1
    assert trace["evidence"]["checks_executed_count"] >= 1
    assert "evidence_items" not in trace


def test_planned_check_requirement_flags_are_precise(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "plan_flags"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        "Nulls increased in the customer email field",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    plan = json.loads(
        (output_dir / "investigation_plan.json").read_text(encoding="utf-8")
    )
    assert not all(check["requires_raw_dataset"] for check in plan["planned_checks"])
    baseline_checks = [
        check for check in plan["planned_checks"] if check["requires_baseline"]
    ]
    assert baseline_checks
    assert all(check["status"] == "planned_not_run" for check in baseline_checks)
    ledger = json.loads(
        (output_dir / "evidence_ledger.json").read_text(encoding="utf-8")
    )
    assert all(
        "baseline" in item["reason"].casefold()
        for item in ledger["checks_not_run"]
        if "baseline" in item["check_id"]
    )


def test_no_code_path_uses_legacy_scaffold_trace_name() -> None:
    for path in Path("src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "write_scaffold_trace" not in text


def test_cli_baseline_csv_run_writes_expected_artifacts(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "baseline_evidence_run"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--baseline",
        "examples/customer_quality_snapshot_baseline.csv",
        "--issue",
        "Nulls increased in the customer email field",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    for name in [
        "investigation_case.json",
        "dataset_profile.json",
        "baseline_profile.json",
        "investigation_plan.json",
        "baseline_comparison.json",
        "evidence_ledger.json",
        "investigation_trace.json",
    ]:
        assert (output_dir / name).exists()
    assert "Baseline profile written to" in result.stdout
    assert "Baseline comparison written to" in result.stdout


def test_cli_rejects_baseline_without_current_input(tmp_path: Path) -> None:
    result = run_cli(
        "--baseline",
        "examples/customer_quality_snapshot_baseline.csv",
        "--output-dir",
        str(tmp_path / "out"),
    )

    assert result.returncode != 0
    assert "--baseline requires --input" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_rejects_baseline_sheet_with_csv(tmp_path: Path) -> None:
    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--baseline",
        "examples/customer_quality_snapshot_baseline.csv",
        "--baseline-sheet",
        "Sheet1",
        "--output-dir",
        str(tmp_path / "out"),
    )

    assert result.returncode != 0
    assert (
        "--baseline-sheet can only be used with Excel baseline files" in result.stderr
    )
    assert "Traceback" not in result.stderr


def test_baseline_comparison_artifact_is_aggregate_only(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "baseline_evidence_run"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--baseline",
        "examples/customer_quality_snapshot_baseline.csv",
        "--issue",
        "Nulls increased in the customer email field",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    comparison = json.loads(
        (output_dir / "baseline_comparison.json").read_text(encoding="utf-8")
    )
    assert comparison["artifact_type"] == "baseline_comparison"
    for key in [
        "row_count_comparison",
        "schema_comparison",
        "null_comparison",
        "numeric_comparison",
        "date_comparison",
        "category_shape_comparison",
        "duplicate_comparison",
    ]:
        assert key in comparison
    assert comparison["safety_notes"]
    assert _find_forbidden_keys(comparison) == []
    serialized = json.dumps(comparison)
    assert "avery@example.test" not in serialized
    assert "CUST-001" not in serialized


def test_null_increase_baseline_evidence_records_signal_without_final_language(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "baseline_null_run"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--baseline",
        "examples/customer_quality_snapshot_baseline.csv",
        "--issue",
        "Nulls increased in the customer email field",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    ledger = json.loads(
        (output_dir / "evidence_ledger.json").read_text(encoding="utf-8")
    )
    assert ledger["issue"]["selected_route"] == "null_increase_investigation"
    item = _evidence_item(ledger, "baseline_null_comparison")
    assert item is not None
    email_delta = next(
        delta
        for delta in item["metrics"]["column_deltas"]
        if delta["column_name"] == "email"
    )
    assert (
        email_delta["current_null_percentage"] > email_delta["baseline_null_percentage"]
    )
    serialized = json.dumps(item).casefold()
    assert "confirmed" not in serialized
    assert "proved" not in serialized


def test_duplicate_baseline_evidence_does_not_write_duplicated_values(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "baseline_duplicate_run"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--baseline",
        "examples/customer_quality_snapshot_baseline.csv",
        "--issue",
        "Customer IDs have started duplicating",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    ledger = json.loads(
        (output_dir / "evidence_ledger.json").read_text(encoding="utf-8")
    )
    item = _evidence_item(ledger, "baseline_duplicate_comparison")
    assert item is not None
    assert item["metrics"]["max_duplicate_count_delta"] >= 1
    assert _find_forbidden_keys(item) == []
    assert "CUST-010" not in json.dumps(item)


def test_schema_baseline_evidence_uses_column_names_only(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "baseline_schema_run"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--baseline",
        "examples/customer_quality_snapshot_baseline.csv",
        "--issue",
        "Header changed in the customer file",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    ledger = json.loads(
        (output_dir / "evidence_ledger.json").read_text(encoding="utf-8")
    )
    item = _evidence_item(ledger, "baseline_schema_comparison")
    assert item is not None
    assert "added_columns" in item["metrics"]
    assert "removed_columns" in item["metrics"]
    assert _find_forbidden_keys(item) == []
    assert "avery@example.test" not in json.dumps(item)


def test_missing_issue_with_input_and_baseline_writes_not_executed_ledger(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "baseline_missing_issue_run"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--baseline",
        "examples/customer_quality_snapshot_baseline.csv",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    assert (output_dir / "baseline_profile.json").exists()
    assert (output_dir / "baseline_comparison.json").exists()
    ledger = json.loads(
        (output_dir / "evidence_ledger.json").read_text(encoding="utf-8")
    )
    assert ledger["execution"]["status"] == "not_executed"
    assert ledger["evidence_items"] == []
    assert "No issue statement was supplied" in ledger["execution"]["reason"]


def test_trace_contains_concise_baseline_metadata_only(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "baseline_trace_run"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--baseline",
        "examples/customer_quality_snapshot_baseline.csv",
        "--issue",
        "Nulls increased in the customer email field",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    trace = json.loads(
        (output_dir / "investigation_trace.json").read_text(encoding="utf-8")
    )
    assert (
        trace["artifacts"]["baseline_profile"]
        == (output_dir / "baseline_profile.json").as_posix()
    )
    assert (
        trace["artifacts"]["baseline_comparison"]
        == (output_dir / "baseline_comparison.json").as_posix()
    )
    assert trace["baseline"]["available"] is True
    assert trace["baseline"]["row_count"] == 12
    assert "comparison_signal_count" in trace["baseline_comparison"]
    assert "null_comparison" not in trace
    assert "evidence_items" not in trace


def test_case_contains_baseline_reference(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "baseline_case_run"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--baseline",
        "examples/customer_quality_snapshot_baseline.csv",
        "--issue",
        "Nulls increased in the customer email field",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    case = json.loads(
        (output_dir / "investigation_case.json").read_text(encoding="utf-8")
    )
    assert case["baseline_reference"]["input_provided"] is True
    assert (
        case["baseline_reference"]["baseline_profile_artifact"]
        == (output_dir / "baseline_profile.json").as_posix()
    )
    assert (
        case["baseline_reference"]["baseline_comparison_artifact"]
        == (output_dir / "baseline_comparison.json").as_posix()
    )


def test_baseline_artifacts_and_ledger_avoid_forbidden_keys_and_raw_values(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "baseline_safety_run"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--baseline",
        "examples/customer_quality_snapshot_baseline.csv",
        "--issue",
        "Customer IDs have started duplicating",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    for name in [
        "baseline_profile.json",
        "baseline_comparison.json",
        "evidence_ledger.json",
    ]:
        payload = json.loads((output_dir / name).read_text(encoding="utf-8"))
        assert _find_forbidden_keys(payload) == []
        serialized = json.dumps(payload)
        assert "avery@example.test" not in serialized
        assert "CUST-001" not in serialized
        assert "customer_id" in serialized or name == "baseline_profile.json"


def _evidence_item(ledger: dict[str, Any], check_id: str) -> dict[str, Any] | None:
    return next(
        (item for item in ledger["evidence_items"] if item["check_id"] == check_id),
        None,
    )


def test_current_duplicate_run_writes_hypotheses_and_findings(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "customer_findings_run"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        "Customer IDs have started duplicating",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    for name in [
        "investigation_case.json",
        "dataset_profile.json",
        "investigation_plan.json",
        "evidence_ledger.json",
        "hypothesis_tracker.json",
        "investigation_findings.json",
        "investigation_trace.json",
    ]:
        assert (output_dir / name).exists()
    assert "Hypothesis tracker written to" in result.stdout
    assert "Investigation findings written to" in result.stdout

    tracker = json.loads(
        (output_dir / "hypothesis_tracker.json").read_text(encoding="utf-8")
    )
    assert tracker["issue"]["issue_type"] == "duplicate_key"
    assert tracker["hypotheses"]
    duplicate_hypothesis = next(
        item
        for item in tracker["hypotheses"]
        if "duplicate non-null" in item["statement"]
    )
    assert duplicate_hypothesis["supporting_evidence_ids"]
    assert all(
        isinstance(evidence_id, str)
        for evidence_id in duplicate_hypothesis["supporting_evidence_ids"]
    )

    findings = json.loads(
        (output_dir / "investigation_findings.json").read_text(encoding="utf-8")
    )
    assert findings["finding_status"] == "review_required"
    assert findings["supported_signals"] or findings["unclear_items"]


def test_baseline_null_run_maps_baseline_signal_to_findings(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "baseline_findings_run"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--baseline",
        "examples/customer_quality_snapshot_baseline.csv",
        "--issue",
        "Nulls increased in the customer email field",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    for name in [
        "investigation_case.json",
        "dataset_profile.json",
        "baseline_profile.json",
        "investigation_plan.json",
        "baseline_comparison.json",
        "evidence_ledger.json",
        "hypothesis_tracker.json",
        "investigation_findings.json",
        "investigation_trace.json",
    ]:
        assert (output_dir / name).exists()

    tracker = json.loads(
        (output_dir / "hypothesis_tracker.json").read_text(encoding="utf-8")
    )
    baseline_hypotheses = [
        item
        for item in tracker["hypotheses"]
        if "higher null percentage than the baseline" in item["statement"]
    ]
    assert baseline_hypotheses
    assert baseline_hypotheses[0]["status"] == "supported_by_evidence"
    assert baseline_hypotheses[0]["supporting_evidence_ids"]

    findings = json.loads(
        (output_dir / "investigation_findings.json").read_text(encoding="utf-8")
    )
    serialized = json.dumps(findings).casefold()
    assert any(
        baseline_hypotheses[0]["hypothesis_id"] in signal["related_hypotheses"]
        for signal in findings["supported_signals"]
    )
    assert "issue confirmed" not in serialized
    assert "root cause identified" not in serialized
    assert "proved" not in serialized


def test_no_input_run_does_not_write_hypothesis_or_findings(tmp_path: Path) -> None:
    output_dir = tmp_path / "plan_run"

    result = run_cli(
        "--issue",
        "Customer IDs have started duplicating",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    assert not (output_dir / "hypothesis_tracker.json").exists()
    assert not (output_dir / "investigation_findings.json").exists()
    trace = json.loads(
        (output_dir / "investigation_trace.json").read_text(encoding="utf-8")
    )
    assert trace["stage"] == "investigation_plan_created"
    assert "hypotheses" not in trace
    assert "findings" not in trace
    assert "hypothesis_tracker" not in trace["artifacts"]
    assert "investigation_findings" not in trace["artifacts"]


def test_missing_issue_with_input_does_not_write_hypothesis_or_findings(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "missing_issue"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    ledger = json.loads(
        (output_dir / "evidence_ledger.json").read_text(encoding="utf-8")
    )
    assert ledger["execution"]["status"] == "not_executed"
    assert not (output_dir / "hypothesis_tracker.json").exists()
    assert not (output_dir / "investigation_findings.json").exists()
    trace = json.loads(
        (output_dir / "investigation_trace.json").read_text(encoding="utf-8")
    )
    assert trace["stage"] == "missing_issue_statement"
    assert "hypotheses" not in trace
    assert "findings" not in trace


def test_schema_baseline_findings_include_schema_checks_and_safe_values(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "schema_findings"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--baseline",
        "examples/customer_quality_snapshot_baseline.csv",
        "--issue",
        "Header changed in the customer file",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    tracker = json.loads(
        (output_dir / "hypothesis_tracker.json").read_text(encoding="utf-8")
    )
    assert tracker["issue"]["selected_route"] == "schema_change_investigation"
    schema_hypothesis = next(
        item
        for item in tracker["hypotheses"]
        if "Current and baseline schemas differ" in item["statement"]
    )
    assert schema_hypothesis["status"] in {
        "supported_by_evidence",
        "not_supported_by_evidence",
    }
    findings = json.loads(
        (output_dir / "investigation_findings.json").read_text(encoding="utf-8")
    )
    assert "Confirm expected required columns" in json.dumps(findings)
    _assert_review_artifact_safety(tracker)
    _assert_review_artifact_safety(findings)


def test_date_route_mentions_daily_cadence_without_missing_date_lists(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "date_findings"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        "A date gap appeared in the signup_date field",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    tracker = json.loads(
        (output_dir / "hypothesis_tracker.json").read_text(encoding="utf-8")
    )
    findings = json.loads(
        (output_dir / "investigation_findings.json").read_text(encoding="utf-8")
    )
    assert "Daily cadence is an assumption" in json.dumps(tracker)
    assert "Confirm the expected date cadence" in json.dumps(findings)
    assert "missing_dates" not in json.dumps(tracker)
    assert "missing_dates" not in json.dumps(findings)


def test_trace_contains_concise_hypothesis_and_finding_metadata(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "trace_findings"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        "Customer IDs have started duplicating",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    trace = json.loads(
        (output_dir / "investigation_trace.json").read_text(encoding="utf-8")
    )
    assert (
        trace["artifacts"]["hypothesis_tracker"]
        == (output_dir / "hypothesis_tracker.json").as_posix()
    )
    assert (
        trace["artifacts"]["investigation_findings"]
        == (output_dir / "investigation_findings.json").as_posix()
    )
    assert trace["hypotheses"]["hypothesis_count"] >= 1
    assert trace["findings"]["finding_status"] == "review_required"
    assert "hypotheses" not in trace["hypotheses"]
    assert "supported_signals" not in trace
    assert "evidence_items" not in trace


def test_findings_structure_is_id_reference_only_and_deduplicated(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "findings_structure"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        "Customer IDs have started duplicating",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    tracker = json.loads(
        (output_dir / "hypothesis_tracker.json").read_text(encoding="utf-8")
    )
    findings = json.loads(
        (output_dir / "investigation_findings.json").read_text(encoding="utf-8")
    )
    supported_hypothesis_ids = {
        item["hypothesis_id"]
        for item in tracker["hypotheses"]
        if item["status"] == "supported_by_evidence"
    }
    supported_signal_hypothesis_ids = {
        hypothesis_id
        for signal in findings["supported_signals"]
        for hypothesis_id in signal["related_hypotheses"]
    }
    assert supported_signal_hypothesis_ids <= supported_hypothesis_ids
    assert len(findings["recommended_human_checks"]) == len(
        set(findings["recommended_human_checks"])
    )
    for signal in findings["supported_signals"] + findings["not_supported_signals"]:
        assert all(
            str(evidence_id).startswith("ev-")
            for evidence_id in signal["related_evidence_ids"]
        )
        assert "metrics" not in signal


def test_hypothesis_and_findings_safety_boundaries(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "review_artifact_safety"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        "Customer IDs have started duplicating",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    for name in ["hypothesis_tracker.json", "investigation_findings.json"]:
        payload = json.loads((output_dir / name).read_text(encoding="utf-8"))
        _assert_review_artifact_safety(payload)


def _assert_review_artifact_safety(payload: dict[str, Any]) -> None:
    forbidden_keys = {*FORBIDDEN_KEYS, "generated_code"}
    assert _find_forbidden_keys_with_set(payload, forbidden_keys) == []
    serialized = json.dumps(payload).casefold()
    assert "avery@example.test" not in serialized
    assert "cust-001" not in serialized
    for phrase in [
        "approved",
        "certified",
        "production-ready",
        "compliant verdict",
        "root cause identified",
        "issue confirmed",
        "proved",
    ]:
        assert phrase not in serialized


def _find_forbidden_keys_with_set(value: Any, forbidden_keys: set[str]) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in forbidden_keys:
                found.append(key)
            found.extend(_find_forbidden_keys_with_set(child, forbidden_keys))
    elif isinstance(value, list):
        for child in value:
            found.extend(_find_forbidden_keys_with_set(child, forbidden_keys))
    return found


def test_current_input_issue_writes_safe_markdown_report(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "customer_report_run"
    issue = "Customer IDs have started duplicating"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        issue,
        "--output-dir",
        str(output_dir),
    )

    report_path = output_dir / "investigation_report.md"
    assert result.returncode == 0, result.stderr
    assert report_path.exists()
    report = report_path.read_text(encoding="utf-8")
    assert "Data Quality Investigation Report" in report
    assert issue in report
    assert "Selected route" in report
    assert "Evidence-supported signals" in report
    assert "Recommended human review checks" in report
    assert "Human review remains the final authority" in report
    _assert_report_safety(report)


def test_baseline_input_issue_report_includes_baseline_context(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "baseline_report_run"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--baseline",
        "examples/customer_quality_snapshot_baseline.csv",
        "--issue",
        "Nulls increased in the customer email field",
        "--output-dir",
        str(output_dir),
    )

    report_path = output_dir / "investigation_report.md"
    assert result.returncode == 0, result.stderr
    assert report_path.exists()
    report = report_path.read_text(encoding="utf-8")
    assert "Baseline comparison available | True" in report
    assert "baseline_comparison.json" in report
    assert "higher null percentage than the baseline" in report
    assert "Baseline null comparison" in report
    _assert_report_safety(report)


def test_no_input_run_does_not_write_or_claim_report(tmp_path: Path) -> None:
    output_dir = tmp_path / "plan_run"

    result = run_cli(
        "--issue",
        "Customer IDs have started duplicating",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    assert not (output_dir / "investigation_report.md").exists()
    trace = json.loads(
        (output_dir / "investigation_trace.json").read_text(encoding="utf-8")
    )
    case = json.loads(
        (output_dir / "investigation_case.json").read_text(encoding="utf-8")
    )
    assert trace["status"] == "planned"
    assert trace["stage"] == "investigation_plan_created"
    assert "report" not in trace
    assert "investigation_report" not in trace["artifacts"]
    assert "investigation_report" not in case["artifacts"]


def test_missing_issue_with_input_does_not_write_or_claim_report(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "missing_issue_run"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    assert not (output_dir / "investigation_report.md").exists()
    assert not (output_dir / "hypothesis_tracker.json").exists()
    assert not (output_dir / "investigation_findings.json").exists()
    ledger = json.loads(
        (output_dir / "evidence_ledger.json").read_text(encoding="utf-8")
    )
    trace = json.loads(
        (output_dir / "investigation_trace.json").read_text(encoding="utf-8")
    )
    assert ledger["execution"]["status"] == "not_executed"
    assert "report" not in trace
    assert "investigation_report" not in trace["artifacts"]


def test_trace_and_case_include_concise_report_metadata(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "trace_report"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        "Customer IDs have started duplicating",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    report_path = output_dir / "investigation_report.md"
    trace = json.loads(
        (output_dir / "investigation_trace.json").read_text(encoding="utf-8")
    )
    case = json.loads(
        (output_dir / "investigation_case.json").read_text(encoding="utf-8")
    )
    assert trace["status"] == "report_written"
    assert trace["stage"] == "markdown_report_created"
    assert trace["artifacts"]["investigation_report"] == report_path.as_posix()
    assert trace["report"]["report_artifact"] == report_path.as_posix()
    assert trace["report"]["report_written"] is True
    assert trace["report"]["finding_status"] == "review_required"
    assert trace["report"]["hypothesis_count"] >= 1
    assert trace["report"]["supported_signal_count"] >= 1
    assert "Data Quality Investigation Report" not in json.dumps(trace)
    assert "evidence_items" not in trace
    assert "hypotheses" not in trace["hypotheses"]
    assert "supported_signals" not in trace
    assert case["workflow"]["status"] == "report_written"
    assert case["workflow"]["stage"] == "markdown_report_created"
    assert case["artifacts"]["investigation_report"] == report_path.as_posix()


def test_artifact_references_and_report_map_include_report(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "artifact_refs"

    result = run_cli(
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--baseline",
        "examples/customer_quality_snapshot_baseline.csv",
        "--issue",
        "Nulls increased in the customer email field",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    report_path = output_dir / "investigation_report.md"
    tracker = json.loads(
        (output_dir / "hypothesis_tracker.json").read_text(encoding="utf-8")
    )
    findings = json.loads(
        (output_dir / "investigation_findings.json").read_text(encoding="utf-8")
    )
    report = report_path.read_text(encoding="utf-8")
    assert tracker["artifacts"]["investigation_report"] == report_path.as_posix()
    assert findings["artifacts"]["investigation_report"] == report_path.as_posix()
    for name in [
        "investigation_case.json",
        "dataset_profile.json",
        "baseline_profile.json",
        "investigation_plan.json",
        "baseline_comparison.json",
        "evidence_ledger.json",
        "hypothesis_tracker.json",
        "investigation_findings.json",
        "investigation_report.md",
        "investigation_trace.json",
    ]:
        assert name in report


def test_docs_exist_and_roadmap_mentions_current_scope() -> None:
    for path in [
        Path("docs/architecture.md"),
        Path("docs/design_principles.md"),
        Path("docs/artifacts.md"),
        Path("docs/example_commands.md"),
        Path("docs/safety_boundaries.md"),
        Path("docs/demo_workflow.md"),
    ]:
        assert path.exists()
    roadmap = Path("docs/roadmap.md").read_text(encoding="utf-8").casefold()
    assert "finished v1 scope" in roadmap
    assert "pr #10 polished" in roadmap


def _assert_report_safety(report: str) -> None:
    folded = report.casefold()
    for forbidden in [
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
        "row_numbers",
        "duplicated_values",
        "category_labels",
        "full_distribution",
        "raw_values",
        "generated_code",
        "avery@example.test",
        "cust-001",
    ]:
        assert forbidden not in folded
    for phrase in [
        "approved",
        "certified",
        "production-ready",
        "compliant verdict",
        "root cause identified",
        "issue confirmed",
        "proved",
    ]:
        assert phrase not in folded
