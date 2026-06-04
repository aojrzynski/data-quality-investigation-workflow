# Architecture

Data Quality Investigation Workflow is a local-first CLI that turns an issue statement and optional local datasets into deterministic review material.

## Final v1 flow

```text
case
-> current profile if input exists
-> optional baseline profile
-> plan
-> optional baseline comparison
-> evidence ledger
-> hypothesis tracker
-> investigation findings
-> deterministic Markdown report
-> optional safe LLM notes
-> trace
```

The main sequence is coordinated by `src/data_quality_investigation_workflow/cli.py`. Each stage writes a small artifact that can be opened directly.

## Stage overview

1. **Case** records the issue, available inputs, workflow scope, artifact paths, and authority boundaries.
2. **Current profile** reads a local CSV or Excel file and records aggregate profile information.
3. **Baseline profile** does the same for an optional baseline file.
4. **Plan** uses deterministic keyword rules to choose a route and planned checks.
5. **Baseline comparison** records aggregate current-vs-baseline signals when a baseline is supplied.
6. **Evidence ledger** records deterministic aggregate checks and checks not run.
7. **Hypothesis tracker** maps evidence IDs to cautious hypotheses.
8. **Investigation findings** summarize evidence-supported signals and human review prompts.
9. **Markdown report** summarizes the deterministic JSON artifacts for easier reading.
10. **Optional LLM notes** are downstream and separate. They are written only with `--llm-notes` and use only `llm_safe_input_summary.json`.
11. **Trace** records concise run status, stage, metadata, and artifact paths.

## Why the stages are separate

Separate artifacts make the workflow easier to inspect. If a report says there is an evidence-supported signal, a reviewer can open `evidence_ledger.json` and find the evidence ID behind it. If a stage did not run, `investigation_trace.json` explains the status.

## Deterministic core

The deterministic path does not call an LLM and does not require `OPENAI_API_KEY`. It relies on local file intake, aggregate profiling, route selection, current-dataset checks, and optional aggregate baseline comparison.

## Optional LLM notes

Optional LLM notes are not part of the evidence source. They are generated after deterministic artifacts exist, from a safe aggregate summary. Validation can fail, and failed validation is recorded without writing Markdown notes.

## Safety and authority boundaries

The architecture keeps raw rows out of artifacts and prompts. It also keeps authority boundaries visible: the workflow does not identify root cause, confirm an issue as final, approve a dataset, certify a dataset, or replace human review.
