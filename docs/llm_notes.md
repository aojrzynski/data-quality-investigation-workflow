# Optional LLM notes

Optional LLM notes are disabled by default. The normal deterministic workflow does not call an LLM and does not require `OPENAI_API_KEY`.

## What they are for

LLM notes can provide bounded reviewer notes, follow-up questions, communication notes, and limitations to keep visible. They are secondary to `investigation_report.md` and the deterministic JSON artifacts.

## Requirements

Install the LLM extra and set an API key:

```bash
python -m pip install -e ".[dev,llm]"
export OPENAI_API_KEY="..."
```

PowerShell:

```powershell
$env:OPENAI_API_KEY="..."
```

Then pass `--llm-notes`:

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --llm-notes --output-dir outputs/customer_llm_notes_run
```

You may override the model with `--llm-model` or the `DQIW_LLM_MODEL` environment variable.

## What the LLM sees

The LLM uses only `llm_safe_input_summary.json`. That file is built from deterministic aggregate artifacts.

It does not include raw rows, sampled rows, example values, top values, distinct value lists, duplicated values, category labels, row numbers, raw failing records, or generated code.

## Validation can fail

LLM output must be valid JSON in the expected schema. It must stay within length limits and avoid blocked raw-value markers or authority language. If validation fails, the workflow records validation errors in `llm_investigation_notes.json` and does not write `llm_investigation_notes.md`.

## Authority boundary

LLM notes are optional and non-authoritative. They do not identify root cause, confirm the issue as final, approve a dataset, certify a dataset, trust a dataset, fix data, or make legal, compliance, privacy, or governance verdicts. Human review remains the final authority.
