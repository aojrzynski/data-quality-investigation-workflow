"""Command line interface for dataset intake and safe profiling."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from data_quality_investigation_workflow import __version__
from data_quality_investigation_workflow.errors import WorkflowUserError
from data_quality_investigation_workflow.trace import (
    DATASET_PROFILE_FILENAME,
    write_scaffold_trace,
)

DEFAULT_OUTPUT_DIR = Path("outputs/scaffold_run")


def build_parser() -> argparse.ArgumentParser:
    """Build the command line argument parser."""
    parser = argparse.ArgumentParser(
        prog="dq-investigate",
        description=(
            "Record an issue-led data quality workflow trace. Optionally load a "
            "local CSV/XLSX/XLSM dataset and write a safe aggregate profile."
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
        help="Optional local CSV, XLSX, or XLSM dataset to profile.",
    )
    parser.add_argument(
        "--sheet",
        help="Worksheet name for Excel input. Not valid for CSV input.",
    )
    parser.add_argument(
        "--issue",
        help="Known or suspected data quality issue statement to record in the trace.",
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
        if args.input is None:
            trace_path = write_scaffold_trace(
                output_dir=args.output_dir,
                issue_statement=args.issue,
            )
            print(f"Scaffold investigation trace written to {trace_path.as_posix()}")
            return 0

        from data_quality_investigation_workflow.intake import load_dataset
        from data_quality_investigation_workflow.trace import write_profiled_trace

        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        profile_path = output_dir / DATASET_PROFILE_FILENAME

        loaded_dataset = load_dataset(args.input, sheet=args.sheet)

        from data_quality_investigation_workflow.profiling import build_dataset_profile

        profile = build_dataset_profile(loaded_dataset)
        profile_path.write_text(
            json.dumps(profile, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        trace_path = write_profiled_trace(
            output_dir=output_dir,
            issue_statement=args.issue,
            loaded_dataset=loaded_dataset,
            profile_path=profile_path,
        )
        print(f"Dataset profile written to {profile_path.as_posix()}")
        print(f"Investigation trace written to {trace_path.as_posix()}")
        return 0
    except WorkflowUserError as error:
        parser.exit(status=2, message=f"Error: {error}\n")
    except ModuleNotFoundError as error:
        missing_dependency = error.name or "required dependency"
        if missing_dependency in {"pandas", "openpyxl"}:
            parser.exit(
                status=2,
                message=(
                    f"Error: Missing required dependency {missing_dependency!r}. "
                    "Install the package with runtime dependencies before profiling datasets.\n"
                ),
            )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
