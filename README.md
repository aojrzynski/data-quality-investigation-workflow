# Data Quality Investigation Workflow

Data Quality Investigation Workflow is a local-first Python project for investigating known or suspected data quality issues. The goal is to help a human reviewer move from an issue statement, such as "Customer IDs have started duplicating," to a structured investigation record with deterministic evidence, clear open questions, and reviewable artifacts.

This repository is at **PR #2 dataset intake and safe profiling status**. The current implementation can run a scaffold-only trace or load a local CSV/XLSX/XLSM dataset and write a safe aggregate `dataset_profile.json` plus an updated `investigation_trace.json`. Profiling is a foundation step only; it does not investigate, confirm, or explain the reported issue.

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
- scaffold-only runs when `--input` is omitted;
- local CSV/XLSX/XLSM dataset intake;
- optional Excel sheet selection with `--sheet`;
- safe aggregate `dataset_profile.json` generation;
- updated `investigation_trace.json` generation;
- a small synthetic customer example dataset;
- pytest tests and GitHub Actions CI.

What does not exist yet:

- issue classification;
- investigation case file creation;
- investigation planning;
- route selection;
- issue-specific deterministic data checks;
- evidence ledger logic;
- hypothesis tracking;
- baseline comparison;
- Markdown report generation;
- LangGraph orchestration;
- OpenAI or other LLM integration.

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

PR #2 only adds dataset intake and safe aggregate profiling. Later PRs will add the investigation steps one at a time.

## Quick start

Use Python 3.11 or newer.

```bash
python -m pip install -e ".[dev]"
```

Run a CSV profile:

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --output-dir outputs/customer_profile
```

The command writes:

```text
outputs/customer_profile/dataset_profile.json
outputs/customer_profile/investigation_trace.json
```

Equivalent module command:

```bash
python -m data_quality_investigation_workflow.cli --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --output-dir outputs/customer_profile
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

CSV profile:

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --output-dir outputs/customer_profile
```

Excel profile:

```bash
dq-investigate --input path/to/workbook.xlsx --sheet Sheet1 --issue "Nulls increased in the customer email field" --output-dir outputs/excel_profile
```

Scaffold-only run without dataset input:

```bash
dq-investigate --issue "Customer IDs have started duplicating" --output-dir outputs/scaffold_run
```

## Output artifacts

Implemented in PR #2:

- `dataset_profile.json` — safe aggregate dataset metadata and column summaries. Written only when `--input` is provided.
- `investigation_trace.json` — records whether the run was scaffold-only or dataset-profiled, the issue statement if supplied, implemented scope, remaining not-yet-implemented workflow pieces, profiled dataset metadata when relevant, artifact paths, and authority boundaries.

Planned for future PRs, not implemented yet:

- `investigation_case.json`;
- `investigation_plan.json`;
- `evidence_ledger.json`;
- `hypothesis_tracker.json`;
- `investigation_findings.json`;
- `investigation_report.md`.

## Authority boundary

This project is meant to support human review, not replace it. It must not claim to:

- treat profiling as investigation;
- confirm the reported issue from a profile alone;
- identify root cause from a profile alone;
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
│       ├── cli.py
│       ├── errors.py
│       ├── intake.py
│       ├── profiling.py
│       └── trace.py
├── tests/
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

The CI workflow runs compile and pytest checks on pull requests and pushes to `main`.

## Limitations and non-goals

For PR #2, this repository intentionally does not include:

- issue classification;
- `investigation_case.json`;
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

The dataset profile is useful as an aggregate intake artifact. It is not an investigation result and does not confirm whether the reported issue exists.

## Further reading

- [Roadmap](docs/roadmap.md)
- [Python packaging user guide](https://packaging.python.org/)
- [pandas documentation](https://pandas.pydata.org/docs/)
- [openpyxl documentation](https://openpyxl.readthedocs.io/)
- [pytest documentation](https://docs.pytest.org/)
- [Ruff documentation](https://docs.astral.sh/ruff/)
