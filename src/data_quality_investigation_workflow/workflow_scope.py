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
    "deterministic current-dataset issue checks",
    "aggregate-only evidence ledger",
    "safe aggregate baseline comparison",
    "hypothesis tracking from aggregate evidence IDs",
    "cautious investigation finding summaries",
    "Markdown investigation report",
    "optional bounded LLM notes",
]

NOT_YET_IMPLEMENTED = [
    "source comment/docstring cleanup",
]

AUTHORITY_BOUNDARY = [
    "Profiling is not investigation.",
    "Issue classification is a planning aid only.",
    "Deterministic checks record aggregate evidence signals only.",
    "Evidence signals and finding summaries are not final verdicts.",
    "The workflow does not confirm the reported issue.",
    "The workflow does not identify root cause.",
    "This tool does not approve, fix, certify, or trust a dataset.",
    "This tool does not make legal, compliance, privacy, or governance verdicts.",
    "No raw rows are written to artifacts.",
    "No raw rows are sent to an LLM.",
    "Human review remains the final authority.",
]
