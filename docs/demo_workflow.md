# Demo workflow

The repository includes synthetic current and baseline CSV files under `examples/`:

- current file: `examples/customer_quality_snapshot.csv`
- baseline file: `examples/customer_quality_snapshot_baseline.csv`

The demo uses column names and aggregate signals only. It does not include raw dataset values in this walkthrough.

## Run the baseline demo

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --baseline examples/customer_quality_snapshot_baseline.csv --issue "Nulls increased in the customer email field" --output-dir outputs/baseline_report_run
```

## Artifacts generated

The run writes:

- `investigation_case.json`
- `dataset_profile.json`
- `baseline_profile.json`
- `investigation_plan.json`
- `baseline_comparison.json`
- `evidence_ledger.json`
- `hypothesis_tracker.json`
- `investigation_findings.json`
- `investigation_report.md`
- `investigation_trace.json`

## How to use the report

Open `outputs/baseline_report_run/investigation_report.md` on GitHub or in a Markdown viewer. The report gives a reviewer-friendly summary of issue context, dataset counts, baseline availability, artifact paths, evidence IDs, hypothesis statuses, supported/not-supported/unclear signals, limitations, and recommended checks.

## What the report does not decide

The report does not determine root cause, approve the dataset, certify the dataset, make legal/compliance/privacy/governance verdicts, or state that the dataset is production-ready. It is a review aid built from deterministic aggregate artifacts.

## Optional LLM notes in a demo

For demos with an API key, run the deterministic workflow with `--llm-notes` to add separate optional notes files. The deterministic `investigation_report.md` remains the primary report; `llm_investigation_notes.md` is secondary reviewer assistance generated only from `llm_safe_input_summary.json`.
