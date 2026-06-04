# Artifacts

This page documents the artifacts produced by Data Quality Investigation Workflow. All artifacts are local files written under the selected output directory.

## `investigation_case.json`

- Purpose: records issue context, dataset/baseline references, workflow status/stage, artifact paths, implemented scope, and authority boundaries.
- Written: every successful run.
- Contains: issue statement if supplied, deterministic classification metadata, safe dataset references, and artifact map.
- Excludes: raw rows, final issue confirmation, root-cause decisions, and dataset approval.

## `dataset_profile.json`

- Purpose: summarizes the current dataset with safe aggregate metadata.
- Written: when `--input` is supplied.
- Contains: file metadata, row/column counts, column names, inferred kinds, null counts, duplicate counts, and aggregate percentages.
- Excludes: raw rows, example values, top values, distinct lists, category labels, and full distributions.

## `baseline_profile.json`

- Purpose: summarizes the baseline dataset with the same safe aggregate metadata as the current profile.
- Written: when `--baseline` is supplied with `--input`.
- Contains: baseline file metadata and aggregate profile details.
- Excludes: raw rows, value lists, and final comparison verdicts.

## `investigation_plan.json`

- Purpose: records deterministic issue classification, selected route, candidate columns, and planned checks.
- Written: every successful run.
- Contains: planning route, planned checks, input availability, and limitations.
- Excludes: executed check results and final findings.

## `baseline_comparison.json`

- Purpose: records safe aggregate current-vs-baseline comparison signals.
- Written: when `--baseline` is supplied with `--input`.
- Contains: row-count comparison, schema comparison, null-count comparison, numeric-total aggregate comparison, date-shape comparison, and category-shape aggregate comparison.
- Excludes: raw records, category labels, duplicated values, and root-cause claims.

## `evidence_ledger.json`

- Purpose: records deterministic aggregate evidence items and checks not run.
- Written: when `--input` is supplied. If no issue is supplied, execution status is `not_executed`.
- Contains: evidence IDs, check names, signal status, signal strength, related columns, safe metrics, limitations, and artifact paths.
- Excludes: raw failing records, row numbers, value previews, generated code, and final verdicts.

## `hypothesis_tracker.json`

- Purpose: maps evidence IDs into bounded route-specific hypotheses.
- Written: when both `--input` and `--issue` are supplied and checks execute.
- Contains: hypothesis IDs, cautious statuses, signal levels, rationale, evidence ID references, and recommended human checks.
- Excludes: raw values, broad free-form speculation, root-cause decisions, and final findings.

## `investigation_findings.json`

- Purpose: summarizes evidence-supported signals, not-supported signals, unclear items, and recommended human checks.
- Written: when `hypothesis_tracker.json` is written.
- Contains: signal IDs, related hypothesis IDs, related evidence IDs, finding status for review, and authority boundaries.
- Excludes: dataset approval, certification, compliance verdicts, production-readiness claims, raw rows, and raw values.

## `investigation_report.md`

- Purpose: gives a human-readable Markdown summary of the JSON artifacts.
- Written: when `investigation_findings.json` is written.
- Contains: issue summary, run context, artifact map, evidence summary, hypothesis summary, findings summary, limitations, and next steps.
- Excludes: raw rows, sampled rows, top values, distinct lists, duplicated values, category labels, final issue confirmation, root-cause decisions, and dataset approval.

## `investigation_trace.json`

- Purpose: records concise run metadata for automation and review.
- Written: every successful run.
- Contains: status/stage, route metadata, artifact paths, dataset counts, baseline availability, evidence counts, hypothesis counts, finding counts, and concise report metadata when applicable.
- Excludes: full report content, full evidence items, full hypotheses, full findings, raw rows, and value lists.

## Optional LLM notes artifacts

`llm_safe_input_summary.json` records the deterministic aggregate-only summary allowed to be sent to the LLM. It references source artifacts and includes issue, run-context, evidence, hypothesis, finding, safety, and instruction-boundary summaries without raw rows or raw values.

`llm_investigation_notes.json` records validated optional LLM notes, validation status, model, source artifacts, and authority boundaries. Failed validation artifacts contain safe error summaries and never store the raw invalid response.

`llm_investigation_notes.md` is a secondary human-readable rendering of successful optional notes. It does not replace `investigation_report.md`.
