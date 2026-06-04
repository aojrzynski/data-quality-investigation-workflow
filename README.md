# Data Quality Investigation Workflow

Data Quality Investigation Workflow is a local-first Python project for investigating known or suspected data quality issues. The goal is to help a human reviewer move from an issue statement, such as "Customer IDs have started duplicating," to a structured investigation record with deterministic evidence, clear open questions, and reviewable artifacts.

This repository is at **PR #5 deterministic checks and evidence ledger status**. The current implementation can create an `investigation_case.json`, create `dataset_profile.json` when input is supplied, classify issue statements for planning only, select a planned investigation route, create `investigation_plan.json`, execute a small set of deterministic current-dataset checks when input and issue context are supplied, create `evidence_ledger.json`, record aggregate evidence only, and write an updated `investigation_trace.json`. Case creation, profiling, planning, and evidence recording are foundation steps only; they do not create final findings, prove the issue exists, compare against a baseline, or identify root cause.

## The problem

Data quality issues often begin as a short observation:

- Customer IDs have started duplicating.
- Nulls increased in the customer email field.
- A report total dropped unexpectedly.
- A date gap appeared in the extract.
- A category value spiked or disappeared.
- A pipeline output looks wrong compared with last week.

Those observations need a repeatable investigation path. A reviewer usually needs to know what was checked, what evidence was found, what remains unclear, and what a human should inspect next. Ad hoc notes and one-off scripts can make that hard to reconstruct later.

## What this project does

The intended workflow will eventually:

1. capture the issue statement;
2. classify the issue type;
3. build an investigation plan;
4. run deterministic checks relevant to the issue;
5. record evidence;
6. update hypotheses;
7. identify what is confirmed, not confirmed, or still unclear;
8. optionally use an LLM only over safe evidence to suggest follow-up questions or investigation notes;
9. write JSON and Markdown artifacts for human review.

What exists now:

- package code under `src/data_quality_investigation_workflow`;
- `dq-investigate` CLI entry point;
- `--input`, `--sheet`, `--issue`, `--output-dir`, and `--version` CLI options;
- case + plan runs when `--input` is omitted;
- `investigation_case.json` generation for issue-led case context;
- deterministic issue classification for planning only;
- planned route selection;
- `investigation_plan.json` generation with planned check records marked `planned_not_run`;
- local CSV/XLSX/XLSM dataset intake;
- optional Excel sheet selection with `--sheet`;
- safe aggregate `dataset_profile.json` generation when input is supplied;
- deterministic current-dataset checks for selected planning routes;
- aggregate-only `evidence_ledger.json` generation when input is supplied;
- updated `investigation_trace.json` generation that references case, plan, profile, and evidence artifacts when available, plus concise route and evidence metadata;
- a small synthetic customer example dataset;
- pytest tests, Ruff checks, and GitHub Actions CI.

What does not exist yet:

- final findings;
- `hypothesis_tracker.json`;
- `investigation_findings.json`;
- baseline comparison execution;
- Markdown report generation;
- proof that the issue exists;
- root-cause identification;
- approval, fixing, certification, or trust decisions for a dataset;
- LangGraph orchestration;
- OpenAI or other LLM integration.

## Investigation case file

Every successful run writes `investigation_case.json`. The case file records the issue statement if supplied, whether an input dataset was supplied, concise dataset reference metadata when available, artifact paths, current workflow status, current workflow stage, not-yet-implemented workflow capabilities, and authority boundaries.

If `--issue` is omitted, the case file is still written. In that situation, `issue.provided` is `false`, `issue.statement` is `null`, and the file includes a note that later investigation steps will be more useful when an issue statement is supplied.

The case file includes deterministic planning classification metadata, but that classification is only a planning aid. The case file does **not** confirm the issue, identify root cause, approve the data, or include raw rows or value previews.

## Safe aggregate profiling

When `--input` is provided, the CLI loads the dataset and writes `dataset_profile.json`. The profile contains dataset metadata and aggregate column summaries such as row counts, column counts, null counts, unique counts, numeric min/max/mean values, datetime parse/range summaries, and text length summaries.

The profile intentionally does **not** include:

- raw rows;
- sampled rows;
- first or last rows;
- example values;
- top values;
- distinct value lists;
- raw failing records;
- value previews.

For CSV input, pandas' default null handling is used, so blank cells may be treated as null values. Text columns may include length statistics, but not the text values themselves.

## Evidence ledger

When `--input` is supplied, the CLI writes `evidence_ledger.json`. If an issue statement is supplied, the ledger records deterministic current-dataset evidence items for the selected route. If input is supplied but the issue statement is omitted, the ledger records `not_executed` status and explains that route-specific evidence checks were not executed.

The evidence ledger includes aggregate metrics only, such as column names, row counts, column counts, null counts, duplicate aggregate counts, unique counts, numeric aggregate totals, date ranges, missing daily period counts, inferred kind counts, check status, and signal labels. It does **not** include raw rows, sampled records, example values, top values, distinct value lists, raw failing records, row numbers, duplicated values, category labels, or full category distributions.

PR #5 checks are current-dataset only. Baseline comparison belongs to PR #6, so PR #5 does not claim that nulls increased, totals changed, schemas changed, or category distributions shifted.

## Why deterministic evidence matters

A data quality investigation should be grounded in checks that can be inspected and repeated. Counts, null rates, duplicate measurements, date ranges, category shape metrics, and baseline comparisons are examples of evidence that can be recorded with clear inputs and outputs.

Deterministic evidence does not remove the need for judgment. It gives reviewers a more stable basis for deciding what to inspect next and for explaining how an investigation reached its current state.

## Why not just ask an LLM?

LLMs can be useful for summarizing safe evidence or suggesting follow-up questions, but they should not be the source of truth for a data quality investigation. This project is designed around these boundaries:

- do not send raw rows to an LLM;
- do not execute arbitrary generated code;
- do not treat LLM output as authoritative;
- do not use an LLM to approve, certify, or fix a dataset.

Future LLM support, if added, will be optional and bounded to safe evidence artifacts only.

## Usage

Install locally in editable mode:

```bash
python -m pip install -e ".[dev]"
```

Run case + plan without dataset input. This writes case, plan, and trace artifacts only; no evidence ledger is written because no current dataset is available for checks:

```bash
dq-investigate --issue "Customer IDs have started duplicating" --output-dir outputs/plan_run
```

Run CSV case + profile + plan + evidence:

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --output-dir outputs/customer_evidence_run
```

Expected CSV artifacts:

```text
outputs/customer_evidence_run/investigation_case.json
outputs/customer_evidence_run/dataset_profile.json
outputs/customer_evidence_run/investigation_plan.json
outputs/customer_evidence_run/evidence_ledger.json
outputs/customer_evidence_run/investigation_trace.json
```

Equivalent module command:

```bash
python -m data_quality_investigation_workflow.cli --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --output-dir outputs/customer_evidence_run
```

## Example commands

Show help:

```bash
dq-investigate --help
```

Show the package version:

```bash
dq-investigate --version
```

Case + plan, no evidence:

```bash
dq-investigate --issue "Customer IDs have started duplicating" --output-dir outputs/plan_run
```

CSV case + profile + plan + evidence:

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --output-dir outputs/customer_evidence_run
```

Excel case + profile + plan + evidence:

```bash
dq-investigate --input path/to/workbook.xlsx --sheet Sheet1 --issue "Nulls increased in the customer email field" --output-dir outputs/excel_evidence_run
```

## Output artifacts

Implemented in PR #5:

- `investigation_case.json` — records the issue statement if supplied, deterministic planning classification metadata, selected route, case ID, creation time, workflow status/stage, dataset reference metadata when available, artifact paths, scope boundaries, and authority boundaries.
- `dataset_profile.json` — safe aggregate dataset metadata and column summaries. Written only when `--input` is provided.
- `investigation_plan.json` — records the issue statement, planning classification status, deterministic issue type, selected route, planned checks with `planned_not_run` status, required/available/missing inputs, safe candidate columns from column names/profile metadata only, limitations, human review prompts, artifact paths, and authority boundaries.
- `evidence_ledger.json` — records deterministic current-dataset check execution metadata, aggregate-only evidence items, planned checks not run, safety notes, limitations, artifact paths, and authority boundaries. Written when `--input` is provided.
- `investigation_trace.json` — records whether the run was planned or evidence-recorded, the issue statement if supplied, concise route metadata, implemented scope, remaining not-yet-implemented workflow pieces, concise profiled dataset metadata when relevant, concise evidence counts when relevant, artifact paths, and authority boundaries.

Planned for future PRs, not implemented yet:

- `hypothesis_tracker.json`;
- `investigation_findings.json`;
- `investigation_report.md`;
- baseline comparison support.

## Authority boundary

This project is meant to support human review, not replace it. It must not claim to:

- treat profiling as final investigation;
- treat planning classification as evidence, confirmation, or explanation of the reported issue;
- create final findings in PR #5;
- compare against a baseline in PR #5;
- prove the issue exists;
- identify root cause;
- fix data;
- approve, certify, or trust a dataset;
- decide that a dataset is complete, compliant, production-ready, or ready for downstream use;
- make legal, compliance, privacy, or governance verdicts;
- write raw rows to artifacts;
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
│   └── customer_quality_snapshot.csv
├── src/
│   └── data_quality_investigation_workflow/
│       ├── __init__.py
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
