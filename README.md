# Data Quality Investigation Workflow

Data Quality Investigation Workflow is a local-first Python project for investigating known or suspected data quality issues. The goal is to help a human reviewer move from an issue statement, such as "Customer IDs have started duplicating," to a structured investigation record with deterministic evidence, clear open questions, and reviewable artifacts.

This repository is at **PR #1 scaffold status**. The current implementation only provides the Python package scaffold, the `dq-investigate` CLI entry point, an initial `investigation_trace.json` artifact, tests, and CI. It does not load datasets or investigate data yet.

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

- package scaffold under `src/data_quality_investigation_workflow`;
- `dq-investigate` CLI entry point;
- `--issue`, `--output-dir`, and `--version` CLI options;
- output directory creation;
- scaffold-only `investigation_trace.json` artifact;
- pytest tests;
- GitHub Actions CI.

What does not exist yet:

- dataset loading;
- issue classification;
- investigation planning;
- deterministic data checks;
- evidence ledger logic;
- hypothesis tracking;
- baseline comparison;
- Markdown report generation;
- LangGraph orchestration;
- OpenAI or other LLM integration.

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

PR #1 only creates the starting point for this workflow. Later PRs will add the investigation steps one at a time.

## Quick start

Use Python 3.11 or newer.

```bash
python -m pip install -e ".[dev]"
```

Run the scaffold CLI:

```bash
dq-investigate --issue "Customer IDs have started duplicating" --output-dir outputs/scaffold_run
```

Equivalent module command:

```bash
python -m data_quality_investigation_workflow.cli --issue "Customer IDs have started duplicating" --output-dir outputs/scaffold_run
```

The command currently writes:

```text
outputs/scaffold_run/investigation_trace.json
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

Write a scaffold trace with an issue statement:

```bash
dq-investigate --issue "Customer IDs have started duplicating" --output-dir outputs/scaffold_run
```

Write a scaffold trace using the module entry point:

```bash
python -m data_quality_investigation_workflow.cli --issue "Nulls increased in the customer email field" --output-dir outputs/scaffold_run
```

## Output artifacts

Implemented in PR #1:

- `investigation_trace.json` — records that this was a scaffold-only run, the issue statement if supplied, the implemented scope, not-yet-implemented areas, and authority boundaries.

Planned for future PRs, not implemented yet:

- `investigation_case.json`;
- `dataset_profile.json`;
- `investigation_plan.json`;
- `evidence_ledger.json`;
- `hypothesis_tracker.json`;
- `investigation_findings.json`;
- `investigation_report.md`;
- `investigation_trace.json` updates as the workflow grows.

## Authority boundary

This project is meant to support human review, not replace it. It must not claim to:

- fix data;
- prove root cause;
- approve a dataset;
- decide that a dataset is trusted, safe, complete, compliant, production-ready, or ready for downstream use;
- make legal, compliance, privacy, or governance verdicts;
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
├── src/
│   └── data_quality_investigation_workflow/
│       ├── __init__.py
│       ├── cli.py
│       └── trace.py
├── tests/
│   └── test_cli.py
├── LICENSE
├── README.md
└── pyproject.toml
```

## Run tests

```bash
python -m compileall src tests
python -m pytest -q
```

The CI workflow runs the same checks on pull requests and pushes to `main`.

## Limitations and non-goals

For PR #1, this repository intentionally does not include:

- dataset intake or parsing;
- pandas or openpyxl dependencies;
- example datasets;
- generated output files committed to the repository;
- issue classification;
- investigation plans;
- deterministic checks;
- evidence ledger implementation;
- hypothesis tracking;
- baseline comparison;
- Markdown report generation;
- LangGraph orchestration;
- OpenAI or other LLM code.

The scaffold trace is useful only as a wiring check. It is not an investigation result.

## Further reading

- [Roadmap](docs/roadmap.md)
- [Python packaging user guide](https://packaging.python.org/)
- [pytest documentation](https://docs.pytest.org/)
- [Ruff documentation](https://docs.astral.sh/ruff/)
