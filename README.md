# Data Quality Investigation Workflow

Data Quality Investigation Workflow is a local-first Python project for investigating known or suspected data quality issues. The goal is to help a human reviewer move from an issue statement, such as "Customer IDs have started duplicating," to structured, deterministic, aggregate-only investigation artifacts.

This repository is at **PR #6 baseline comparison support status**. The current implementation can create issue-led case and plan artifacts, profile a current dataset, optionally profile a baseline dataset, compare current vs baseline datasets using safe aggregate signals, execute deterministic current-dataset checks, record route-aware baseline comparison evidence when a baseline is supplied, and write a concise trace. These artifacts support human review; they do **not** create final findings, prove the issue exists, or identify root cause.

## The problem

Data quality issues often begin as a short observation:

- Customer IDs have started duplicating.
- Nulls increased in the customer email field.
- A report total dropped unexpectedly.
- A date gap appeared in the extract.
- A category value spiked or disappeared.
- A pipeline output looks wrong compared with last week.

Those observations need a repeatable investigation path. A reviewer usually needs to know what was checked, what aggregate evidence signals were recorded, what remains unclear, and what a human should inspect next.

## What this project does

The intended workflow will eventually:

1. capture the issue statement;
2. classify the issue type for planning;
3. build an investigation plan;
4. run deterministic checks relevant to the issue;
5. record current-dataset and baseline comparison evidence;
6. update hypotheses;
7. identify what is confirmed, not confirmed, or still unclear;
8. optionally use an LLM only over safe evidence to suggest follow-up questions or investigation notes;
9. write JSON and Markdown artifacts for human review.

What exists now:

- package code under `src/data_quality_investigation_workflow`;
- `dq-investigate` CLI entry point;
- `--input`, `--sheet`, `--baseline`, `--baseline-sheet`, `--issue`, `--output-dir`, and `--version` CLI options;
- case + plan runs when `--input` is omitted;
- `investigation_case.json` generation for issue-led case context;
- deterministic issue classification for planning only;
- planned route selection;
- `investigation_plan.json` generation with baseline availability metadata and planned check executability metadata;
- local CSV/XLSX/XLSM current dataset intake;
- local CSV/XLSX/XLSM baseline dataset intake when `--baseline` is supplied;
- optional Excel sheet selection with `--sheet` and `--baseline-sheet`;
- safe aggregate `dataset_profile.json` generation when current input is supplied;
- safe aggregate `baseline_profile.json` generation when baseline input is supplied;
- safe aggregate `baseline_comparison.json` generation when baseline input is supplied;
- deterministic current-dataset checks for selected planning routes;
- route-aware baseline comparison evidence for null, duplicate, date, total, schema, category, and general routes;
- aggregate-only `evidence_ledger.json` generation when input is supplied;
- updated `investigation_trace.json` generation with concise dataset, baseline, comparison, route, and evidence metadata;
- synthetic current and baseline customer example datasets;
- pytest tests, Ruff checks, and GitHub Actions CI.

What does not exist yet:

- final findings;
- `hypothesis_tracker.json`;
- `investigation_findings.json`;
- Markdown report generation;
- proof that the issue exists;
- root-cause identification;
- approval, fixing, certification, or trust decisions for a dataset;
- database or cloud connectors;
- LangGraph orchestration;
- OpenAI or other LLM integration.

## Investigation case file

Every successful run writes `investigation_case.json`. The case file records the issue statement if supplied, concise current dataset reference metadata when available, baseline reference metadata when supplied, artifact paths, current workflow status, current workflow stage, implemented scope, not-yet-implemented workflow capabilities, and authority boundaries.

If `--issue` is omitted, the case file is still written. In that situation, `issue.provided` is `false`, `issue.statement` is `null`, and the file includes a note that later investigation steps will be more useful when an issue statement is supplied.

The case file includes deterministic planning classification metadata, but that classification is only a planning aid. The case file does **not** confirm the issue, identify root cause, approve the data, or include raw rows or value previews.

## Safe aggregate profiling

When `--input` is provided, the CLI loads the current dataset and writes `dataset_profile.json`. When `--baseline` is also provided, the CLI loads the baseline dataset and writes `baseline_profile.json` with the same safe aggregate profile structure.

Profiles contain dataset metadata and aggregate column summaries such as row counts, column counts, null counts, unique counts, duplicate aggregate counts, numeric min/max/mean values, datetime parse/range summaries, and text length summaries.

Profiles intentionally do **not** include:

- raw rows;
- sampled rows;
- first or last rows;
- example values;
- top values;
- distinct value lists;
- duplicated values;
- raw failing records;
- value previews.

For CSV input, pandas' default null handling is used, so blank cells may be treated as null values. Text columns may include length statistics, but not the text values themselves.

## Baseline comparison

When `--input` and `--baseline` are both supplied, the CLI writes `baseline_comparison.json`. The comparison artifact records safe aggregate current-vs-baseline signals only, including:

- current and baseline source metadata;
- row count and column count deltas;
- schema comparison using column names only;
- null count and null percentage comparison by matching column names;
- numeric total comparison by matching numeric columns;
- date range and missing daily period comparison for date-like columns;
- category shape comparison without category labels;
- duplicate aggregate comparison for candidate key columns;
- safety notes, limitations, artifact references, and authority boundaries.

The baseline comparison does **not** write raw rows, sampled rows, example values, top values, distinct value lists, duplicated values, category labels, full distributions, raw failing records, row numbers, final findings, or root-cause claims.

Date gap comparison currently assumes a daily cadence for aggregate missing-period counts. That assumption is recorded as a limitation in the comparison and evidence artifacts; missing date lists are not written.

## Evidence ledger

When `--input` is supplied, the CLI writes `evidence_ledger.json`. If an issue statement is supplied, the ledger records deterministic current-dataset evidence items for the selected route. If a baseline is supplied, it also records route-aware baseline comparison evidence items where useful. If input is supplied but the issue statement is omitted, the ledger records `not_executed` status and explains that route-specific evidence checks were not executed.

The evidence ledger uses wording such as "signal," "aggregate comparison," and "current vs baseline difference." It does **not** claim that an issue is finally confirmed, does **not** identify root cause, and does **not** create final findings.

## Example commands

Case + plan, no evidence:

```bash
dq-investigate --issue "Customer IDs have started duplicating" --output-dir outputs/plan_run
```

Current-only evidence:

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --output-dir outputs/customer_evidence_run
```

Baseline comparison evidence:

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --baseline examples/customer_quality_snapshot_baseline.csv --issue "Nulls increased in the customer email field" --output-dir outputs/baseline_evidence_run
```

Excel baseline comparison:

```bash
dq-investigate --input path/to/current.xlsx --sheet Current --baseline path/to/baseline.xlsx --baseline-sheet Baseline --issue "The report total dropped unexpectedly" --output-dir outputs/excel_baseline_evidence_run
```

## Output artifacts

Implemented in PR #6:

- `investigation_case.json` — records the issue statement if supplied, deterministic planning classification metadata, selected route, case ID, creation time, workflow status/stage, current dataset reference metadata, baseline reference metadata when supplied, artifact paths, scope boundaries, and authority boundaries.
- `dataset_profile.json` — safe aggregate current dataset metadata and column summaries. Written only when `--input` is provided.
- `baseline_profile.json` — safe aggregate baseline dataset metadata and column summaries. Written only when `--baseline` is provided.
- `investigation_plan.json` — records the issue statement, planning classification status, deterministic issue type, selected route, planned checks, available/missing inputs, baseline availability, safe candidate columns from column names/profile metadata only, limitations, human review prompts, artifact paths, and authority boundaries.
- `baseline_comparison.json` — safe aggregate current-vs-baseline comparison metadata. Written only when `--baseline` is provided.
- `evidence_ledger.json` — records deterministic current-dataset check execution metadata, route-aware baseline comparison evidence when available, aggregate-only evidence items, planned checks not run, safety notes, limitations, artifact paths, and authority boundaries. Written when `--input` is provided.
- `investigation_trace.json` — records whether the run was planned or evidence-recorded, the issue statement if supplied, concise route metadata, implemented scope, remaining not-yet-implemented workflow pieces, concise current and baseline dataset metadata when relevant, concise comparison/evidence counts when relevant, artifact paths, and authority boundaries.

Planned for future PRs, not implemented yet:

- `hypothesis_tracker.json`;
- `investigation_findings.json`;
- `investigation_report.md`;
- optional LLM-generated investigation notes over safe evidence only.

## Run tests

Install the package with development dependencies and run the checks used by CI:

```bash
python -m pip install -e ".[dev]"
python -m compileall src tests
python -m pytest -q
python -m ruff check .
```

## Limitations and non-goals

This project is meant to support human review, not replace it. It must not claim to:

- treat profiling as final investigation;
- treat planning classification as evidence, confirmation, or explanation of the reported issue;
- create final findings in PR #6;
- create `hypothesis_tracker.json` in PR #6;
- create `investigation_findings.json` in PR #6;
- generate a Markdown report in PR #6;
- call an LLM in PR #6;
- prove the issue exists;
- identify root cause;
- fix data;
- approve, certify, or trust a dataset;
- decide that a dataset is complete, compliant, production-ready, or ready for downstream use;
- use database or cloud connectors;
- make legal, compliance, privacy, or governance verdicts;
- write raw rows, sampled rows, example values, top values, distinct value lists, duplicated values, category labels, full distributions, row numbers, or raw failing records to artifacts;
- send raw rows to an LLM;
- execute arbitrary generated code;
- treat LLM output as authoritative.

Human review remains the final authority.

## Project structure

```text
.
├── .github/workflows/ci.yml
├── docs/
│   └── roadmap.md
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
│       ├── intake.py
│       ├── issue_classifier.py
│       ├── planning.py
│       ├── profiling.py
│       ├── trace.py
│       └── workflow_scope.py
├── tests/
│   ├── test_build_backend.py
│   ├── test_cli.py
│   ├── test_intake.py
│   ├── test_issue_classifier.py
│   └── test_profiling.py
├── LICENSE
├── README.md
└── pyproject.toml
```

## Further reading

- See [`docs/roadmap.md`](docs/roadmap.md) for the planned pull request sequence.
- See [`examples/customer_quality_snapshot.csv`](examples/customer_quality_snapshot.csv) and [`examples/customer_quality_snapshot_baseline.csv`](examples/customer_quality_snapshot_baseline.csv) for synthetic local test data.
- See the tests under [`tests/`](tests/) for executable examples of current CLI behavior and artifact safety boundaries.
