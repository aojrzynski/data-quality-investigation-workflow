# Example commands

Install the package in editable mode before running examples:

```bash
python -m pip install -e ".[dev]"
```

You can use either the console script or the Python module form:

```bash
dq-investigate --help
python -m data_quality_investigation_workflow.cli --help
```

Deterministic commands do not require `OPENAI_API_KEY`.

## Plan-only run

Use this when you have an issue statement but no local dataset ready yet.

```bash
dq-investigate --issue "Customer IDs have started duplicating" --output-dir outputs/plan_run
```

Python module equivalent:

```bash
python -m data_quality_investigation_workflow.cli --issue "Customer IDs have started duplicating" --output-dir outputs/plan_run
```

## Current dataset + issue

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --output-dir outputs/customer_report_run
```

## Recommended current + baseline demo

This is the most useful demo command because it writes the current profile, baseline profile, baseline comparison, evidence ledger, findings, report, and trace.

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --baseline examples/customer_quality_snapshot_baseline.csv --issue "Nulls increased in the customer email field" --output-dir outputs/baseline_report_run
```

Python module equivalent:

```bash
python -m data_quality_investigation_workflow.cli --input examples/customer_quality_snapshot.csv --baseline examples/customer_quality_snapshot_baseline.csv --issue "Nulls increased in the customer email field" --output-dir outputs/baseline_report_run
```

## Excel current + baseline

```bash
dq-investigate --input path/to/current.xlsx --sheet Current --baseline path/to/baseline.xlsx --baseline-sheet Baseline --issue "The report total dropped unexpectedly" --output-dir outputs/excel_report_run
```

## Missing issue with input

This profiles the input and records that investigation checks are not ready because no issue was supplied.

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --output-dir outputs/missing_issue_run
```

## Optional LLM notes

Optional LLM notes are disabled by default. They require the `llm` extra and `OPENAI_API_KEY`.

```bash
python -m pip install -e ".[dev,llm]"
export OPENAI_API_KEY="..."
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --llm-notes --output-dir outputs/customer_llm_notes_run
```

PowerShell:

```powershell
$env:OPENAI_API_KEY="..."
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --llm-notes --output-dir outputs/customer_llm_notes_run
```

Optional LLM notes use only `llm_safe_input_summary.json`; raw rows are not sent to the model.
