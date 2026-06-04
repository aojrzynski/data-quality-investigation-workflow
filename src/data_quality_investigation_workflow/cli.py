"""Command line interface for dataset intake and safe profiling."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from data_quality_investigation_workflow import __version__
from data_quality_investigation_workflow.baseline import (
    BASELINE_COMPARISON_FILENAME,
    BASELINE_PROFILE_FILENAME,
    write_baseline_comparison,
)
from data_quality_investigation_workflow.case_file import write_investigation_case
from data_quality_investigation_workflow.evidence import LEDGER_FILENAME, write_evidence_ledger
from data_quality_investigation_workflow.findings import FINDINGS_FILENAME, write_investigation_findings
from data_quality_investigation_workflow.hypotheses import HYPOTHESIS_TRACKER_FILENAME, write_hypothesis_tracker
from data_quality_investigation_workflow.errors import DatasetIntakeError, WorkflowUserError
from data_quality_investigation_workflow.intake import EXCEL_EXTENSIONS, load_dataset
from data_quality_investigation_workflow.issue_classifier import classify_issue
from data_quality_investigation_workflow.planning import PLAN_FILENAME, write_investigation_plan
from data_quality_investigation_workflow.profiling import build_dataset_profile
from data_quality_investigation_workflow.trace import (
    DATASET_PROFILE_FILENAME,
    TRACE_FILENAME,
    write_investigation_trace,
)

DEFAULT_OUTPUT_DIR = Path("outputs/plan_run")


def build_parser() -> argparse.ArgumentParser:
    """Build the command line argument parser."""
    parser = argparse.ArgumentParser(
        prog="dq-investigate",
        description=(
            "Record an issue-led data quality workflow trace. Optionally load "
            "local CSV/XLSX/XLSM current and baseline datasets and write safe "
            "aggregate evidence artifacts."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Optional local CSV, XLSX, or XLSM current dataset to profile.",
    )
    parser.add_argument(
        "--sheet",
        help="Worksheet name for Excel input. Not valid for CSV input.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Optional local CSV, XLSX, or XLSM baseline dataset to compare.",
    )
    parser.add_argument(
        "--baseline-sheet",
        help="Worksheet name for Excel baseline input. Not valid for CSV baseline input.",
    )
    parser.add_argument(
        "--issue",
        help="Known or suspected data quality issue statement to record in the case and trace.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        type=Path,
        help=f"Directory for output artifacts. Defaults to {DEFAULT_OUTPUT_DIR}.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        _validate_baseline_args(args)
        if args.input is None:
            _run_plan_only(args)
            return 0

        _run_dataset_workflow(args)
        return 0
    except WorkflowUserError as error:
        parser.exit(status=2, message=f"Error: {error}\n")


def _validate_baseline_args(args: argparse.Namespace) -> None:
    if args.baseline is not None and args.input is None:
        raise WorkflowUserError("--baseline requires --input for the current dataset.")
    if args.baseline_sheet is not None and args.baseline is None:
        raise WorkflowUserError("--baseline-sheet can only be used when --baseline is supplied.")
    if args.baseline is not None and args.baseline.suffix.lower() not in EXCEL_EXTENSIONS:
        if args.baseline_sheet is not None:
            raise WorkflowUserError(
                "--baseline-sheet can only be used with Excel baseline files, not CSV input."
            )


def _run_plan_only(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    plan_path = output_dir / PLAN_FILENAME
    case_path = write_investigation_case(
        output_dir=output_dir,
        issue_statement=args.issue,
        plan_path=plan_path,
    )
    plan_path = write_investigation_plan(
        output_dir=output_dir,
        issue_statement=args.issue,
        case_path=case_path,
    )
    trace_path = write_investigation_trace(
        output_dir=output_dir,
        issue_statement=args.issue,
        case_path=case_path,
        plan_path=plan_path,
    )
    print(f"Investigation case written to {case_path.as_posix()}")
    print(f"Investigation plan written to {plan_path.as_posix()}")
    print(f"Investigation trace written to {trace_path.as_posix()}")


def _run_dataset_workflow(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    profile_path = output_dir / DATASET_PROFILE_FILENAME
    baseline_profile_path = output_dir / BASELINE_PROFILE_FILENAME
    baseline_comparison_path = output_dir / BASELINE_COMPARISON_FILENAME
    plan_path = output_dir / PLAN_FILENAME
    trace_path = output_dir / TRACE_FILENAME
    ledger_path = output_dir / LEDGER_FILENAME

    loaded_dataset = load_dataset(args.input, sheet=args.sheet)
    classification = classify_issue(args.issue)
    issue_provided = bool(classification.get("provided"))
    hypothesis_tracker_path = (
        output_dir / HYPOTHESIS_TRACKER_FILENAME if issue_provided else None
    )
    findings_path = output_dir / FINDINGS_FILENAME if issue_provided else None
    profile = build_dataset_profile(loaded_dataset)
    _write_json(profile_path, profile)

    baseline_dataset = None
    baseline_profile = None
    baseline_comparison = None
    if args.baseline is not None:
        baseline_dataset = _load_baseline_dataset(args.baseline, args.baseline_sheet)
        baseline_profile = build_dataset_profile(baseline_dataset)
        baseline_profile["artifact_type"] = "baseline_profile"
        _write_json(baseline_profile_path, baseline_profile)
        baseline_comparison = _build_and_write_baseline_comparison(
            output_dir=output_dir,
            loaded_dataset=loaded_dataset,
            baseline_dataset=baseline_dataset,
            profile=profile,
            baseline_profile=baseline_profile,
            profile_path=profile_path,
            baseline_profile_path=baseline_profile_path,
        )

    case_path = write_investigation_case(
        output_dir=output_dir,
        issue_statement=args.issue,
        loaded_dataset=loaded_dataset,
        profile_path=profile_path,
        plan_path=plan_path,
        ledger_path=ledger_path,
        baseline_dataset=baseline_dataset,
        baseline_profile_path=baseline_profile_path if baseline_dataset else None,
        baseline_comparison_path=baseline_comparison_path if baseline_dataset else None,
        hypothesis_tracker_path=hypothesis_tracker_path,
        findings_path=findings_path,
    )
    plan_path = write_investigation_plan(
        output_dir=output_dir,
        issue_statement=args.issue,
        loaded_dataset=loaded_dataset,
        dataset_profile=profile,
        case_path=case_path,
        profile_path=profile_path,
        ledger_path=ledger_path,
        baseline_dataset=baseline_dataset,
        baseline_profile_path=baseline_profile_path if baseline_dataset else None,
        baseline_comparison_path=baseline_comparison_path if baseline_dataset else None,
        hypothesis_tracker_path=hypothesis_tracker_path,
        findings_path=findings_path,
    )
    investigation_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    ledger_path = write_evidence_ledger(
        output_dir=output_dir,
        issue_statement=args.issue,
        classification=classification,
        route_name=classification["selected_route"],
        loaded_dataset=loaded_dataset,
        dataset_profile=profile,
        investigation_plan=investigation_plan,
        case_path=case_path,
        profile_path=profile_path,
        plan_path=plan_path,
        trace_path=trace_path,
        baseline_comparison=baseline_comparison,
        baseline_profile_path=baseline_profile_path if baseline_dataset else None,
        baseline_comparison_path=baseline_comparison_path if baseline_dataset else None,
    )
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    hypothesis_metadata = None
    findings_metadata = None
    if issue_provided and ledger["execution"]["status"] == "checks_executed":
        artifact_refs = _artifact_refs(
            case_path=case_path,
            profile_path=profile_path,
            plan_path=plan_path,
            ledger_path=ledger_path,
            trace_path=trace_path,
            baseline_profile_path=baseline_profile_path if baseline_dataset else None,
            baseline_comparison_path=baseline_comparison_path if baseline_dataset else None,
            hypothesis_tracker_path=hypothesis_tracker_path,
            findings_path=findings_path,
        )
        assert hypothesis_tracker_path is not None
        assert findings_path is not None
        hypothesis_tracker_path = write_hypothesis_tracker(
            output_dir=output_dir,
            issue_statement=args.issue,
            classification=classification,
            investigation_plan=investigation_plan,
            evidence_ledger=ledger,
            artifacts=artifact_refs,
            baseline_comparison_available=baseline_comparison is not None,
        )
        hypothesis_tracker = json.loads(hypothesis_tracker_path.read_text(encoding="utf-8"))
        findings_path = write_investigation_findings(
            output_dir=output_dir,
            issue_statement=args.issue,
            classification=classification,
            hypothesis_tracker=hypothesis_tracker,
            evidence_ledger=ledger,
            artifacts=artifact_refs,
            baseline_comparison_available=baseline_comparison is not None,
        )
        findings = json.loads(findings_path.read_text(encoding="utf-8"))
        hypothesis_metadata = {
            "hypothesis_count": len(hypothesis_tracker["hypotheses"]),
            "supported_hypothesis_count": hypothesis_tracker["hypothesis_summary"]["supported_by_evidence"],
            "unclear_hypothesis_count": hypothesis_tracker["hypothesis_summary"]["unclear"],
            "not_supported_hypothesis_count": hypothesis_tracker["hypothesis_summary"]["not_supported_by_evidence"],
        }
        findings_metadata = {
            "supported_signal_count": findings["summary"]["supported_signal_count"],
            "unclear_item_count": len(findings["unclear_items"]),
            "finding_status": findings["finding_status"],
        }

    trace_path = write_investigation_trace(
        output_dir=output_dir,
        issue_statement=args.issue,
        loaded_dataset=loaded_dataset,
        profile_path=profile_path,
        case_path=case_path,
        plan_path=plan_path,
        ledger_path=ledger_path,
        baseline_dataset=baseline_dataset,
        baseline_profile_path=baseline_profile_path if baseline_dataset else None,
        baseline_comparison_path=baseline_comparison_path if baseline_dataset else None,
        baseline_comparison_metadata=baseline_comparison,
        evidence_metadata={
            "checks_executed_count": ledger["execution"]["checks_executed_count"],
            "evidence_item_count": ledger["execution"]["evidence_item_count"],
            "checks_not_run_count": ledger["execution"]["checks_not_run_count"],
        },
        hypothesis_tracker_path=hypothesis_tracker_path,
        findings_path=findings_path,
        hypothesis_metadata=hypothesis_metadata,
        findings_metadata=findings_metadata,
    )
    print(f"Investigation case written to {case_path.as_posix()}")
    print(f"Dataset profile written to {profile_path.as_posix()}")
    if baseline_dataset is not None:
        print(f"Baseline profile written to {baseline_profile_path.as_posix()}")
    print(f"Investigation plan written to {plan_path.as_posix()}")
    if baseline_dataset is not None:
        print(f"Baseline comparison written to {baseline_comparison_path.as_posix()}")
    print(f"Evidence ledger written to {ledger_path.as_posix()}")
    if hypothesis_tracker_path is not None:
        print(f"Hypothesis tracker written to {hypothesis_tracker_path.as_posix()}")
    if findings_path is not None:
        print(f"Investigation findings written to {findings_path.as_posix()}")
    print(f"Investigation trace written to {trace_path.as_posix()}")



def _artifact_refs(
    *,
    case_path: Path,
    profile_path: Path,
    plan_path: Path,
    ledger_path: Path,
    trace_path: Path,
    baseline_profile_path: Path | None,
    baseline_comparison_path: Path | None,
    hypothesis_tracker_path: Path | None,
    findings_path: Path | None,
) -> dict[str, str | None]:
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
    return artifacts

def _load_baseline_dataset(path: Path, sheet: str | None):
    try:
        return load_dataset(path, sheet=sheet)
    except DatasetIntakeError as error:
        message = str(error)
        message = message.replace("Input file", "Baseline file")
        message = message.replace("Provide --sheet", "Provide --baseline-sheet")
        message = message.replace("--sheet can only", "--baseline-sheet can only")
        raise DatasetIntakeError(message) from error


def _build_and_write_baseline_comparison(
    *,
    output_dir: Path,
    loaded_dataset,
    baseline_dataset,
    profile: dict[str, object],
    baseline_profile: dict[str, object],
    profile_path: Path,
    baseline_profile_path: Path,
) -> dict[str, object]:
    comparison_path = write_baseline_comparison(
        output_dir=output_dir,
        current_dataset=loaded_dataset,
        baseline_dataset=baseline_dataset,
        current_profile=profile,
        baseline_profile=baseline_profile,
        dataset_profile_path=profile_path,
        baseline_profile_path=baseline_profile_path,
    )
    return json.loads(comparison_path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
