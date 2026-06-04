# Data Quality Investigation Workflow

Data Quality Investigation Workflow is a local-first Python project for investigating known or suspected data quality issues. The goal is to help a human reviewer move from an issue statement, such as "Customer IDs have started duplicating," to a structured investigation record with deterministic evidence, clear open questions, and reviewable artifacts.

This repository is at **PR #3 investigation case file foundation status**. The current implementation can create an `investigation_case.json` with the reported issue and run context, run without input as a case-only/scaffold run, or load a local CSV/XLSX/XLSM dataset and write a safe aggregate `dataset_profile.json` plus an updated `investigation_trace.json`. Case creation and profiling are foundation steps only; they do not investigate, confirm, or explain the reported issue.

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
- case-only/scaffold runs when `--input` is omitted;
- `investigation_case.json` generation for issue-led case context;
- local CSV/XLSX/XLSM dataset intake;
- optional Excel sheet selection with `--sheet`;
- safe aggregate `dataset_profile.json` generation when input is supplied;
- updated `investigation_trace.json` generation that references the case artifact;
- a small synthetic customer example dataset;
- pytest tests, Ruff checks, and GitHub Actions CI.

What does not exist yet:

- issue classification;
- investigation planning;
- route selection;
- issue-specific deterministic data checks;
- evidence ledger logic;
- hypothesis tracking;
- baseline comparison;
- Markdown report generation;
- LangGraph orchestration;
- OpenAI or other LLM integration.

## Investigation case file

Every successful run writes `investigation_case.json`. The case file records the issue statement if supplied, whether an input dataset was supplied, concise dataset reference metadata when available, artifact paths, current workflow status, current workflow stage, not-yet-implemented workflow capabilities, and authority boundaries.

If `--issue` is omitted, the case file is still written. In that situation, `issue.provided` is `false`, `issue.statement` is `null`, and the file includes a note that later investigation steps will be more useful when an issue statement is supplied.

The case file does **not** classify the issue, confirm the issue, identify root cause, approve the data, or include raw rows or value previews.

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

## Why deterministic evidence matters

A data quality investigation should be grounded in checks that can be inspected and repeated. Counts, null rates, duplicate measurements, date ranges, category frequencies, and baseline comparisons are examples of evidence that can be recorded with clear inputs and outputs.

Deterministic evidence does not remove the need for judgment. It gives reviewers a more stable basis for deciding what to inspect next and for explaining how an investigation reached its current state.

## Why not just ask an LLM?

LLMs can be useful for summarizing safe evidence or suggesting follow-up questions, but they should not be the source of truth for a data quality investigation. This project is designed around these boundaries:

- do not send raw rows to an LLM;
- do not execute arbitrary generated code;
- do not treat LLM output as authoritative;
- do not use an LLM to approve, certify, or fix a dataset.

Future LLM support, if added, will be optional and bounded to safe evidence artifacts. Human review remains the final authority.

## Why this is a workflow

A suspected data quality issue usually needs multiple steps, not a single answer. The workflow framing is intended to keep each step explicit:

- what issue was reported;
- what type of issue it appears to be;
- what checks were planned;
- what checks were run;
- what evidence was recorded;
- which hypotheses changed;
- what is confirmed, not confirmed, or still unclear;
- what a human should check next.

PR #3 adds the investigation case file foundation. Later PRs will add investigation planning, route selection, checks, evidence, hypotheses, findings, and reports one step at a time.

## Quick start

Use Python 3.11 or newer.

```bash
python -m pip install -e ".[dev]"
```

Run a case-only/scaffold command:

```bash
dq-investigate --issue "Customer IDs have started duplicating" --output-dir outputs/case_run
```

The command writes:

```text
outputs/case_run/investigation_case.json
outputs/case_run/investigation_trace.json
```

Run a CSV case + profile command:

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --output-dir outputs/customer_case_profile
```

The command writes:

```text
outputs/customer_case_profile/investigation_case.json
outputs/customer_case_profile/dataset_profile.json
outputs/customer_case_profile/investigation_trace.json
```

Equivalent module command:

```bash
python -m data_quality_investigation_workflow.cli --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --output-dir outputs/customer_case_profile
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

Case-only/scaffold run without dataset input:

```bash
dq-investigate --issue "Customer IDs have started duplicating" --output-dir outputs/case_run
```

CSV case + profile:

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --output-dir outputs/customer_case_profile
```

Excel case + profile:

```bash
dq-investigate --input path/to/workbook.xlsx --sheet Sheet1 --issue "Nulls increased in the customer email field" --output-dir outputs/excel_case_profile
```

## Output artifacts

Implemented in PR #3:

- `investigation_case.json` — records the issue statement if supplied, case ID, creation time, workflow status/stage, dataset reference metadata when available, artifact paths, scope boundaries, and authority boundaries.
- `dataset_profile.json` — safe aggregate dataset metadata and column summaries. Written only when `--input` is provided.
- `investigation_trace.json` — records whether the run was case-only or dataset-profiled, the issue statement if supplied, implemented scope, remaining not-yet-implemented workflow pieces, concise profiled dataset metadata when relevant, artifact paths, and authority boundaries.

Planned for future PRs, not implemented yet:

- `investigation_plan.json`;
- `evidence_ledger.json`;
- `hypothesis_tracker.json`;
- `investigation_findings.json`;
- `investigation_report.md`.

## Authority boundary

This project is meant to support human review, not replace it. It must not claim to:

- treat profiling as investigation;
- classify, confirm, or explain the reported issue in PR #3;
- identify root cause from a case file or profile alone;
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
│       ├── cli.py
│       ├── errors.py
│       ├── intake.py
│       ├── profiling.py
│       └── trace.py
├── tests/
│   ├── test_build_backend.py
│   ├── test_cli.py
│   ├── test_intake.py
│   └── test_profiling.py
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

The CI workflow runs compile, pytest, and Ruff checks on pull requests and pushes to `main`.

## Limitations and non-goals

For PR #3, this repository intentionally does not include:

- issue classification;
- `investigation_plan.json`;
- `evidence_ledger.json`;
- `hypothesis_tracker.json`;
- `investigation_findings.json`;
- `investigation_report.md`;
- baseline/current comparison;
- LangGraph orchestration;
- OpenAI or other LLM code;
- arbitrary generated code execution;
- database or cloud connectors;
- committed generated outputs.

The investigation case and dataset profile are useful foundation artifacts. They are not investigation results and do not confirm whether the reported issue exists.

## Further reading

- [Roadmap](docs/roadmap.md)
- [Python packaging user guide](https://packaging.python.org/)
- [pandas documentation](https://pandas.pydata.org/docs/)
- [openpyxl documentation](https://openpyxl.readthedocs.io/)
- [pytest documentation](https://docs.pytest.org/)
- [Ruff documentation](https://docs.astral.sh/ruff/)
