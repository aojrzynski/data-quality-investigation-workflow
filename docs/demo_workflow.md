# Demo workflow

This guided demo uses the example customer quality snapshots included in the repository.

## 1. Install the package

```bash
python -m pip install -e ".[dev]"
```

## 2. Run the baseline demo

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --baseline examples/customer_quality_snapshot_baseline.csv --issue "Nulls increased in the customer email field" --output-dir outputs/baseline_report_run
```

This writes deterministic local artifacts. No LLM is used and no API key is required.

## 3. Open the report

Open:

```text
outputs/baseline_report_run/investigation_report.md
```

Use it for the fastest readable overview of the issue, route, evidence summary, findings summary, limitations, and next steps.

## 4. Inspect the trace

Open:

```text
outputs/baseline_report_run/investigation_trace.json
```

Use it to confirm the run status, stage, artifact paths, and concise metadata.

## 5. Inspect the evidence ledger

Open:

```text
outputs/baseline_report_run/evidence_ledger.json
```

Use it to review deterministic aggregate evidence items and checks not run. Evidence IDs in later artifacts point back here.

## 6. Inspect findings

Open:

```text
outputs/baseline_report_run/investigation_findings.json
```

Use it to see evidence-supported signals, unclear items, and suggested human checks.

## 7. Optional LLM notes

If you want optional notes, install the LLM extra and provide an API key:

```bash
python -m pip install -e ".[dev,llm]"
export OPENAI_API_KEY="..."
dq-investigate --input examples/customer_quality_snapshot.csv --baseline examples/customer_quality_snapshot_baseline.csv --issue "Nulls increased in the customer email field" --llm-notes --output-dir outputs/baseline_llm_notes_run
```

PowerShell:

```powershell
$env:OPENAI_API_KEY="..."
```

Open `llm_safe_input_summary.json` first to see the aggregate-only input. Open `llm_investigation_notes.md` only if validation succeeds.

## 8. What not to conclude

Do not conclude that the tool has identified root cause, confirmed the issue as final, approved the dataset, certified the dataset, or replaced human review. The output is review material for the next human checks.
