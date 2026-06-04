# Example commands

Install locally for development:

```bash
python -m pip install -e ".[dev]"
```

Show help and version:

```bash
dq-investigate --help
dq-investigate --version
```

## Plan-only run

```bash
dq-investigate --issue "Customer IDs have started duplicating" --output-dir outputs/plan_run
```

Expected artifacts:

- `investigation_case.json`
- `investigation_plan.json`
- `investigation_trace.json`

No Markdown report is written for plan-only runs.

## Current-only input + issue run

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --output-dir outputs/customer_report_run
```

Expected artifacts:

- `investigation_case.json`
- `dataset_profile.json`
- `investigation_plan.json`
- `evidence_ledger.json`
- `hypothesis_tracker.json`
- `investigation_findings.json`
- `investigation_report.md`
- `investigation_trace.json`

## Baseline input + issue run

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --baseline examples/customer_quality_snapshot_baseline.csv --issue "Nulls increased in the customer email field" --output-dir outputs/baseline_report_run
```

Expected artifacts:

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

## Excel current/baseline run

```bash
dq-investigate --input path/to/current.xlsx --sheet Current --baseline path/to/baseline.xlsx --baseline-sheet Baseline --issue "The report total dropped unexpectedly" --output-dir outputs/excel_report_run
```

The artifact list matches the baseline input + issue run when the files and sheets are valid.

## Missing issue with input

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --output-dir outputs/missing_issue_run
```

Expected artifacts:

- `investigation_case.json`
- `dataset_profile.json`
- `investigation_plan.json`
- `evidence_ledger.json`
- `investigation_trace.json`

The evidence ledger records `not_executed`. No hypothesis tracker, findings artifact, or Markdown report is written.

## Optional LLM notes

```bash
python -m pip install -e ".[dev,llm]"
export OPENAI_API_KEY="..."
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --llm-notes --output-dir outputs/customer_llm_notes_run
```

Windows PowerShell: `$env:OPENAI_API_KEY="..."`
