"""Command line interface for the scaffold workflow."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from data_quality_investigation_workflow import __version__
from data_quality_investigation_workflow.trace import write_scaffold_trace

DEFAULT_OUTPUT_DIR = Path("outputs/scaffold_run")


def build_parser() -> argparse.ArgumentParser:
    """Build the command line argument parser."""
    parser = argparse.ArgumentParser(
        prog="dq-investigate",
        description=(
            "Write a scaffold-only investigation trace for a suspected data "
            "quality issue. Dataset intake and investigation checks are not "
            "implemented yet."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--issue",
        help="Known or suspected data quality issue statement to record in the trace.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        type=Path,
        help=f"Directory for scaffold artifacts. Defaults to {DEFAULT_OUTPUT_DIR}.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the scaffold CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    trace_path = write_scaffold_trace(
        output_dir=args.output_dir,
        issue_statement=args.issue,
    )
    print(f"Scaffold investigation trace written to {trace_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
