# Architecture

Data Quality Investigation Workflow is a local-first CLI. It reads local files, builds safe aggregate artifacts, and keeps each step deterministic so a human reviewer can inspect how the investigation moved from issue statement to evidence and recommended checks.

## Flow

```text
CLI
-> intake
-> profiling
-> case file
-> planning
-> baseline comparison
-> checks
-> evidence ledger
-> hypotheses
-> findings
-> Markdown report
-> trace
```

Some steps are conditional:

- Baseline profiling and baseline comparison run only when `--baseline` is supplied.
- Evidence, hypotheses, findings, and the Markdown report run only when both `--input` and `--issue` are supplied.
- Plan-only runs write case, plan, and trace artifacts only.
- Missing-issue input runs write a current profile, case, plan, not-executed evidence ledger, and trace, but no hypotheses, findings, or report.

## Module responsibilities

- `cli.py` coordinates arguments, local file loading, artifact sequencing, and user-facing output.
- `intake.py` loads CSV/XLSX/XLSM files from local paths.
- `profiling.py` builds safe aggregate dataset profiles.
- `case_file.py` records case context, artifact references, workflow status, and authority boundaries.
- `issue_classifier.py` selects deterministic planning routes from keyword rules.
- `planning.py` writes route plans and safe candidate-column choices.
- `baseline.py` writes baseline profiles and aggregate current-vs-baseline comparisons.
- `checks.py` executes deterministic current and baseline-aware aggregate checks.
- `evidence.py` writes the aggregate-only evidence ledger.
- `hypotheses.py` maps evidence IDs into bounded route-specific hypotheses.
- `findings.py` creates review-oriented finding summaries and recommended human checks.
- `reporting.py` renders `investigation_report.md` from already-built JSON artifacts.
- `trace.py` writes concise metadata and artifact paths.
- `workflow_scope.py` centralizes implemented scope and authority-boundary text.

## Why JSON artifacts are written before Markdown

The JSON artifacts are the structured source of truth. The Markdown report is a review layer generated after findings exist. This keeps report generation simple, deterministic, and standard-library-only, while allowing reviewers or tests to inspect the underlying case, profile, plan, evidence, hypotheses, and findings independently.

## Trace design

The trace remains concise. It records status, stage, route, artifact paths, dataset metadata, baseline availability, evidence counts, hypothesis counts, finding counts, and report metadata when a report is written. It does not duplicate full report content, full evidence items, full hypotheses, or full findings.

## Future LLM notes

Future optional bounded LLM notes would fit after deterministic artifacts are written and before or alongside human-facing narrative notes. They are not implemented here. Any future LLM step must consume only safe aggregate artifacts, avoid raw rows and value lists, and remain subordinate to deterministic evidence and human review.
