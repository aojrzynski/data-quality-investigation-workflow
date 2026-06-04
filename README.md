# Data Quality Investigation Workflow

Data Quality Investigation Workflow is a local-first Python project for investigating known or suspected data quality issues. It helps a human reviewer move from an issue statement, such as "Customer IDs have started duplicating," to structured, deterministic, aggregate-only investigation artifacts.

This repository is at **PR #7 hypothesis tracker and findings builder status**. The current implementation can create issue-led case and plan artifacts, profile a current dataset, optionally profile a baseline dataset, compare current vs baseline datasets using safe aggregate signals, execute deterministic current-dataset checks, record route-aware baseline comparison evidence, map evidence IDs into cautious hypotheses, summarize supported/not-supported/unclear signals for human review, and write a concise trace.

The workflow supports human review; it does **not** identify root cause, generate a Markdown report, call an LLM, approve/fix/certify/trust a dataset, make legal/compliance/privacy/governance verdicts, or use database/cloud connectors.

## The problem

Data quality issues often begin as a short observation:

- Customer IDs have started duplicating.
- Nulls increased in the customer email field.
- A report total dropped unexpectedly.
- A date gap appeared in the extract.
- A category value spiked or disappeared.
- A pipeline output looks wrong compared with last week.

Those observations need a repeatable investigation path. A reviewer usually needs to know what was checked, what aggregate evidence signals were recorded, what remains unclear, and what a human should inspect next.

## Why deterministic evidence matters

The project is deterministic-evidence-first because data quality review often needs reproducible artifacts. The CLI records local, aggregate-only signals such as row counts, null counts, duplicate counts, date-range summaries, schema metadata, and current-vs-baseline comparison counts. It references evidence by ID in later artifacts so reviewers can trace a finding summary back to deterministic checks without exposing raw rows or value lists.

## Why not just ask an LLM?

An LLM can be useful later for bounded notes, but it should not be the source of evidence. This implementation does not call an LLM. It first creates structured local artifacts from deterministic checks so human reviewers can inspect evidence, limitations, and recommended next checks. Optional bounded LLM notes belong to a later PR and must operate only over safe artifacts.

## What this project does now

Current PR #7 behavior can:

- create `investigation_case.json` for issue-led case context;
- create `dataset_profile.json` when current input is supplied;
- create `baseline_profile.json` when baseline input is supplied;
- create `investigation_plan.json` with deterministic route selection and planned checks;
- create `baseline_comparison.json` when baseline input is supplied;
- create `evidence_ledger.json` when input is supplied;
- create `hypothesis_tracker.json` when input and issue are supplied;
- create `investigation_findings.json` when input and issue are supplied;
- write an updated `investigation_trace.json` with concise dataset, baseline, evidence, hypothesis, and finding metadata.

The package code lives under `src/data_quality_investigation_workflow`, and the CLI is available as `dq-investigate` after installation.

## Example commands

Case + plan, no evidence:

```bash
dq-investigate --issue "Customer IDs have started duplicating" --output-dir outputs/plan_run
```

Current-only evidence + hypotheses + findings:

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --output-dir outputs/customer_findings_run
```

Baseline comparison + hypotheses + findings:

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --baseline examples/customer_quality_snapshot_baseline.csv --issue "Nulls increased in the customer email field" --output-dir outputs/baseline_findings_run
```

Excel baseline comparison:

```bash
dq-investigate --input path/to/current.xlsx --sheet Current --baseline path/to/baseline.xlsx --baseline-sheet Baseline --issue "The report total dropped unexpectedly" --output-dir outputs/excel_findings_run
```

## Artifact behavior

- `investigation_case.json` records the issue statement if supplied, concise dataset and baseline references, artifact paths, workflow status/stage, implemented scope, and authority boundaries.
- `dataset_profile.json` records safe aggregate profile metadata for the current dataset.
- `baseline_profile.json` records safe aggregate profile metadata for the baseline dataset when supplied.
- `investigation_plan.json` records deterministic issue classification for planning only, selected route, planned checks, available inputs, and human review prompts.
- `baseline_comparison.json` records safe aggregate current-vs-baseline comparison signals when a baseline is supplied.
- `evidence_ledger.json` records deterministic current-dataset evidence and route-aware baseline comparison evidence as aggregate-only evidence items.
- `hypothesis_tracker.json` maps evidence IDs into a small bounded set of route-specific hypotheses with cautious statuses: `supported_by_evidence`, `not_supported_by_evidence`, `unclear`, or `not_assessed`.
- `investigation_findings.json` summarizes evidence-supported signals, not-supported signals, unclear items, and recommended human checks. It is a finding summary for review, not a final verdict.
- `investigation_trace.json` records concise run metadata and artifact paths. For input + issue runs, it includes counts for hypotheses and finding summaries but does not duplicate full evidence, hypotheses, or findings.

Plan-only runs do not write `hypothesis_tracker.json` or `investigation_findings.json`. Runs with input but no issue still write a not-executed `evidence_ledger.json`, but do not write hypothesis or findings artifacts.

## Safe aggregate profiling and evidence

Profiles and evidence artifacts intentionally do **not** include:

- raw rows;
- sampled rows;
- first or last rows;
- example values;
- top values;
- distinct value lists;
- duplicated values;
- raw failing records;
- category labels;
- full category distributions;
- row numbers;
- value previews.

Column names, aggregate counts, aggregate percentages, evidence IDs, hypothesis IDs, and signal IDs are allowed.

## Run tests

Install the package with development dependencies and run the checks used by CI:

```bash
python -m pip install -e ".[dev]"
python -m compileall src tests
python -m pytest -q
python -m ruff check .
```

## Limitations and non-goals

This project is meant to support human review, not replace it. The implementation still does not:

- identify root cause;
- generate `investigation_report.md`;
- call an LLM;
- approve, fix, certify, or trust a dataset;
- make legal, compliance, privacy, or governance verdicts;
- decide that a dataset is production-ready or ready for downstream use;
- use database or cloud connectors;
- write raw rows, sampled rows, example values, top values, distinct value lists, duplicated values, category labels, full distributions, row numbers, or raw failing records to artifacts;
- send raw rows anywhere;
- execute arbitrary generated code;
- treat finding summaries as final verdicts.

Human review remains the final authority.

## Project structure

```text
.
├── docs/
│   └── roadmap.md
├── examples/
│   ├── customer_quality_snapshot.csv
│   └── customer_quality_snapshot_baseline.csv
├── src/
│   └── data_quality_investigation_workflow/
│       ├── baseline.py
│       ├── case_file.py
│       ├── checks.py
│       ├── cli.py
│       ├── evidence.py
│       ├── findings.py
│       ├── hypotheses.py
│       ├── intake.py
│       ├── issue_classifier.py
│       ├── planning.py
│       ├── profiling.py
│       ├── trace.py
│       └── workflow_scope.py
├── tests/
├── LICENSE
├── README.md
└── pyproject.toml
```

## Further reading

- See [`docs/roadmap.md`](docs/roadmap.md) for the planned pull request sequence.
- See [`examples/customer_quality_snapshot.csv`](examples/customer_quality_snapshot.csv) and [`examples/customer_quality_snapshot_baseline.csv`](examples/customer_quality_snapshot_baseline.csv) for synthetic local test data.
- See the tests under [`tests/`](tests/) for executable examples of current CLI behavior and artifact safety boundaries.
