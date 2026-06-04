# Artifacts

This page explains what each artifact is for, when it is written, what to open it for, and what it excludes.

## Common exclusions

Artifacts are safe aggregate review material. They exclude raw rows, sampled rows, example values, top values, distinct value lists, duplicated values, category labels, row numbers, raw failing records, and generated code.

## `investigation_case.json`

- **Purpose:** Records the issue, available inputs, workflow status, artifact paths, scope, and authority boundaries.
- **When written:** Every successful run.
- **Open it for:** A quick machine-readable view of the case and what artifacts should exist.
- **Excludes:** Raw rows and any final decision about whether the issue is confirmed.

## `dataset_profile.json`

- **Purpose:** Records aggregate current-dataset profile information.
- **When written:** When `--input` is supplied and loaded.
- **Open it for:** Row count, column count, column names, inferred types, null counts, numeric summaries, and date summaries.
- **Excludes:** Raw values, samples, top values, distinct value lists, and raw failing records.

## `baseline_profile.json`

- **Purpose:** Records aggregate baseline profile information in the same style as the current profile.
- **When written:** When `--baseline` is supplied and loaded.
- **Open it for:** Baseline row count, column count, column names, and aggregate profile context.
- **Excludes:** Raw baseline rows, examples, top values, and category labels.

## `investigation_plan.json`

- **Purpose:** Records deterministic route selection, candidate columns, planned checks, and limitations.
- **When written:** Every successful run.
- **Open it for:** Understanding what the workflow planned to check and why.
- **Excludes:** A claim that the route is correct or that the issue is confirmed.

## `baseline_comparison.json`

- **Purpose:** Records aggregate current-vs-baseline comparison signals.
- **When written:** When both current and baseline datasets are supplied.
- **Open it for:** Row count, schema, null, numeric, date, category-shape, and duplicate aggregate comparison signals.
- **Excludes:** Raw rows, missing date lists, duplicated values, top values, and category labels.

## `evidence_ledger.json`

- **Purpose:** Records deterministic aggregate evidence items and checks not run.
- **When written:** When an input dataset is supplied.
- **Open it for:** Evidence IDs, check names, aggregate signal summaries, and limits.
- **Excludes:** Interpretation as a final decision and any raw failing records.

## `hypothesis_tracker.json`

- **Purpose:** Maps evidence IDs into cautious hypotheses.
- **When written:** When input and issue are supplied.
- **Open it for:** Hypothesis IDs and the evidence IDs that support or do not support each hypothesis.
- **Excludes:** Raw evidence payloads and root-cause decisions.

## `investigation_findings.json`

- **Purpose:** Summarizes evidence-supported signals, not-supported signals, unclear items, and suggested human checks.
- **When written:** When input and issue are supplied.
- **Open it for:** Review-oriented interpretation aids and next checks.
- **Excludes:** Final approval, certification, root-cause identification, and raw records.

## `investigation_report.md`

- **Purpose:** Provides a deterministic human-readable summary of the JSON artifacts.
- **When written:** When input and issue are supplied.
- **Open it for:** The fastest readable overview after a run.
- **Excludes:** Raw rows, generated code, and any authoritative decision.

## `llm_safe_input_summary.json`

- **Purpose:** Provides a bounded aggregate-only input summary for optional LLM notes.
- **When written:** Only with `--llm-notes`.
- **Open it for:** Seeing exactly what the LLM was allowed to use.
- **Excludes:** Raw rows, sampled rows, example values, top values, category labels, and generated code.

## `llm_investigation_notes.json`

- **Purpose:** Records validated optional LLM notes or validation errors.
- **When written:** Only with `--llm-notes`.
- **Open it for:** Checking whether optional LLM notes passed validation and what was returned.
- **Excludes:** Evidence creation, final decisions, and raw rows.

## `llm_investigation_notes.md`

- **Purpose:** Renders optional LLM notes in Markdown.
- **When written:** Only with `--llm-notes` when validation succeeds.
- **Open it for:** Easier reading of optional notes.
- **Excludes:** Any source of truth beyond the deterministic artifacts.

## `investigation_trace.json`

- **Purpose:** Records concise run metadata, status, stage, artifact paths, and counts.
- **When written:** Every successful run.
- **Open it for:** Checking what ran, what was skipped, and where outputs were written.
- **Excludes:** Full report text, evidence payloads, hypotheses, findings, and raw rows.
