# Data Quality Investigation Workflow

Data Quality Investigation Workflow is a local-first Python CLI for investigating known or suspected data quality issues. Given an issue statement and optional local current/baseline datasets, it creates deterministic, aggregate-only artifacts that help a human reviewer decide what to inspect next.

This repository is at **PR #8 Markdown report and deeper docs status**. The current implementation can create case, profile, plan, evidence, baseline comparison, hypothesis, finding, trace, and human-readable Markdown report artifacts. `investigation_report.md` is generated for input + issue runs, summarizes the JSON artifacts, and is not generated for plan-only or missing-issue runs.

## The problem

Data quality investigations often start with a vague concern: duplicated identifiers, rising nulls, changed totals, date gaps, schema drift, or category-shape changes. Reviewers need reproducible evidence and clear next steps without exposing raw rows or letting a model invent findings.

## What this project does now

The `dq-investigate` CLI can:

- record an issue-led `investigation_case.json`;
- profile a local CSV/XLSX/XLSM current dataset into `dataset_profile.json`;
- optionally profile a local baseline dataset into `baseline_profile.json`;
- select a deterministic planning route from keyword rules;
- write `investigation_plan.json` with planned checks and candidate columns;
- compare current and baseline aggregate profiles when `--baseline` is supplied;
- execute deterministic current-dataset checks and route-aware baseline checks;
- write aggregate-only `evidence_ledger.json`;
- write `hypothesis_tracker.json` and `investigation_findings.json` for input + issue runs;
- write `investigation_report.md` for input + issue runs after findings are available;
- write concise `investigation_trace.json` metadata for every successful run.

## Why deterministic evidence matters

The project is deterministic-evidence-first because human reviewers need reproducible artifacts. The CLI records local aggregate signals such as row counts, column counts, null counts, duplicate counts, date summaries, schema metadata, and current-vs-baseline comparison counts. Later artifacts reference evidence IDs and hypothesis IDs so reviewers can trace each summary back to deterministic checks.

## Why not just ask an LLM?

An LLM can be useful for bounded narrative notes, but it should not be the source of evidence. By default, this implementation does not call an LLM. It first creates local, structured, aggregate-only artifacts. Optional bounded LLM notes are available only through explicit `--llm-notes` opt-in and operate only over `llm_safe_input_summary.json`.

## Quick start

```bash
python -m pip install -e ".[dev]"
dq-investigate --help
dq-investigate --version
```

## Example commands

Plan-only run:

```bash
dq-investigate --issue "Customer IDs have started duplicating" --output-dir outputs/plan_run
```

Current dataset + issue run:

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --output-dir outputs/customer_report_run
```

Current + baseline dataset + issue run:

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --baseline examples/customer_quality_snapshot_baseline.csv --issue "Nulls increased in the customer email field" --output-dir outputs/baseline_report_run
```

Excel current + baseline run:

```bash
dq-investigate --input path/to/current.xlsx --sheet Current --baseline path/to/baseline.xlsx --baseline-sheet Baseline --issue "The report total dropped unexpectedly" --output-dir outputs/excel_report_run
```

Missing issue with input:

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --output-dir outputs/missing_issue_run
```

## Output artifacts

- `investigation_case.json` records issue context, dataset references, artifact references, workflow status/stage, scope, and authority boundaries.
- `dataset_profile.json` records safe aggregate profile metadata for the current dataset.
- `baseline_profile.json` records the same safe profile metadata for a supplied baseline dataset.
- `investigation_plan.json` records deterministic issue classification, selected route, candidate columns, and planned checks.
- `baseline_comparison.json` records safe aggregate current-vs-baseline comparison signals when a baseline is supplied.
- `evidence_ledger.json` records deterministic aggregate evidence items and checks not run.
- `hypothesis_tracker.json` maps evidence IDs into bounded route-specific hypotheses.
- `investigation_findings.json` summarizes evidence-supported signals, not-supported signals, unclear items, and recommended human checks.
- `investigation_report.md` summarizes the existing JSON artifacts for human review when findings are written.
- `investigation_trace.json` records concise run metadata and artifact paths without duplicating report contents, evidence items, hypotheses, or findings.

Plan-only runs write case, plan, and trace only. Missing-issue runs with input write a not-executed evidence ledger but do not write hypotheses, findings, or a Markdown report.

## Markdown report

`investigation_report.md` is generated only for input + issue runs where `investigation_findings.json` is generated. The report includes issue summary, run context, artifact map, evidence summary, hypothesis summary, finding summary, limitations, and next steps.

The report summarizes deterministic aggregate artifacts. It does not identify root cause, approve the dataset, certify the dataset, make legal/compliance/privacy/governance verdicts, or decide production readiness. Human review remains required.

## Safe aggregate boundaries

Artifacts and reports may include:

- column names;
- row counts and column counts;
- aggregate counts and percentages;
- inferred data kinds and schema metadata;
- evidence IDs, hypothesis IDs, and signal IDs;
- cautious human-review notes.

Artifacts and reports do not include raw rows, sampled rows, first/last rows, example values, top values, distinct value lists, raw failing records, duplicated values, category labels, full category distributions, row numbers, generated code, or LLM output.

## Authority boundary

The workflow supports investigation planning and human review. It does not confirm that an issue is final, determine root cause, approve/fix/certify/trust a dataset, or make legal, compliance, privacy, or governance verdicts. Human review remains the final authority.

## Project structure

```text
.
├── .github/
│   └── workflows/
│       └── ci.yml
├── docs/
│   ├── architecture.md
│   ├── artifacts.md
│   ├── demo_workflow.md
│   ├── example_commands.md
│   ├── roadmap.md
│   └── safety_boundaries.md
├── examples/
│   ├── customer_quality_snapshot.csv
│   └── customer_quality_snapshot_baseline.csv
├── src/
│   └── data_quality_investigation_workflow/
│       ├── __init__.py
│       ├── baseline.py
│       ├── case_file.py
│       ├── checks.py
│       ├── cli.py
│       ├── errors.py
│       ├── evidence.py
│       ├── findings.py
│       ├── hypotheses.py
│       ├── intake.py
│       ├── issue_classifier.py
│       ├── planning.py
│       ├── profiling.py
│       ├── reporting.py
│       ├── trace.py
│       └── workflow_scope.py
├── tests/
├── LICENSE
├── README.md
└── pyproject.toml
```

## Run tests

```bash
python -m compileall src tests
python -m pytest -q
python -m ruff check .
```

## Limitations and non-goals

The current implementation is intentionally bounded. It does not execute generated code, add database/cloud connectors, call an LLM unless `--llm-notes` is explicitly supplied, inspect upstream systems, write remediations, or certify datasets. It provides deterministic aggregate evidence and review-oriented summaries by default, with optional non-authoritative LLM notes available only over safe artifacts.

## Further reading

- [Architecture](docs/architecture.md)
- [Artifacts](docs/artifacts.md)
- [Example commands](docs/example_commands.md)
- [Safety boundaries](docs/safety_boundaries.md)
- [Demo workflow](docs/demo_workflow.md)
- [Roadmap](docs/roadmap.md)

## Optional bounded LLM notes

No LLM is used unless `--llm-notes` is explicitly supplied. Optional LLM notes require the `llm` extra and `OPENAI_API_KEY`:

```bash
python -m pip install -e ".[dev,llm]"
export OPENAI_API_KEY="..."
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --llm-notes --output-dir outputs/customer_llm_notes_run
```

For Windows PowerShell, use `$env:OPENAI_API_KEY="..."`. The LLM receives only `llm_safe_input_summary.json`, which is built from safe aggregate artifacts. LLM notes are non-authoritative, do not replace deterministic JSON artifacts or `investigation_report.md`, and do not identify root cause or make approval, certification, trust, legal, compliance, privacy, or governance verdicts. See [docs/llm_notes.md](docs/llm_notes.md).
