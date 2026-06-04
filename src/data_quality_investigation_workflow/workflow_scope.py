"""Shared workflow scope and authority boundary text."""

from __future__ import annotations

IMPLEMENTED_SCOPE = [
    "CLI entry point",
    "output directory creation",
    "scaffold trace artifact",
    "local CSV/XLSX/XLSM dataset intake",
    "safe aggregate dataset profiling",
    "investigation case file",
    "deterministic issue classification for planning",
    "investigation plan artifact",
    "planned route selection",
]

NOT_YET_IMPLEMENTED = [
    "deterministic issue checks",
    "evidence ledger",
    "hypothesis tracking",
    "baseline comparison",
    "Markdown investigation report",
    "optional LLM notes",
]

AUTHORITY_BOUNDARY = [
    "Profiling is not investigation.",
    "Issue classification is a planning aid only.",
    "Planned checks have not been executed.",
    "The plan does not confirm the reported issue.",
    "The plan does not identify root cause.",
    "This tool does not approve, fix, certify, or trust a dataset.",
    "This tool does not make legal, compliance, privacy, or governance verdicts.",
    "No raw rows are written to artifacts.",
    "No raw rows are sent to an LLM.",
    "Human review remains the final authority.",
]
