# Design principles

Data Quality Investigation Workflow is designed to create clear review material for suspected data quality issues. It is intentionally small, local, and cautious.

## Local-first by default

The default workflow reads local files and writes local artifacts. It does not connect to databases, cloud services, or SaaS tools. This keeps the first version easy to run and easy to reason about.

## Deterministic evidence first

The workflow writes deterministic aggregate evidence before it writes interpretation aids or narrative reports. The same inputs should produce the same evidence-supported signal.

## Safe aggregate artifacts

Artifacts may include column names, aggregate counts, percentages, IDs, paths, and human review prompts. They do not include raw rows, sampled rows, example values, top values, category labels, or raw failing records.

## Issue-led workflow

The workflow starts from a known or suspected issue. The issue statement guides route selection and planned checks. The tool is not a general data catalog or broad profiling dashboard.

## Human review final authority

The artifacts help a person decide what to inspect next. They do not identify root cause, confirm the issue as final, approve a dataset, or replace human review.

## Optional LLM notes are non-authoritative

No LLM is used unless `--llm-notes` is explicitly supplied. Optional LLM notes are based only on `llm_safe_input_summary.json`, do not see raw rows, and are secondary to the deterministic report.

## JSON artifacts before Markdown

The JSON artifacts are written before the Markdown report so each stage can be inspected on its own. The report is a readable summary of existing artifacts, not a separate source of truth.

## Traceability over magic

The workflow records evidence IDs, hypothesis IDs, artifact paths, stages, and status. This makes it easier to see why a summary was written and what still needs human review.

## No raw rows in prompts or artifacts

Raw rows are intentionally excluded from prompts and artifacts. This keeps the review material focused on aggregate signals and avoids exposing specific record values.

## No generated code execution

The tool does not generate code to run against the dataset. Checks are deterministic Python code shipped with the package.
