# Optional LLM Investigation Notes

PR #9 adds optional bounded LLM investigation notes. They are disabled by default and are never required for the deterministic workflow.

## Enablement

Install the optional extra and set an API key before using `--llm-notes`:

```bash
python -m pip install -e ".[dev,llm]"
export OPENAI_API_KEY="..."
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --llm-notes --output-dir outputs/customer_llm_notes_run
```

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="..."
```

## Safety model

The LLM receives only `llm_safe_input_summary.json`, a deterministic safe summary assembled from already-written aggregate artifacts. It does not receive raw rows, sampled rows, example values, top values, distinct value lists, duplicated values, category labels, full distributions, row numbers, or raw failing records.

The notes are non-authoritative. They may suggest review notes, follow-up questions, and human checks, but they do not identify root cause, confirm an issue, approve or certify a dataset, fix data, trust a dataset, or make legal, compliance, privacy, or governance verdicts.

## Artifacts

When validation passes, `--llm-notes` writes:

- `llm_safe_input_summary.json` — the bounded aggregate summary sent to the LLM.
- `llm_investigation_notes.json` — structured notes plus validation metadata.
- `llm_investigation_notes.md` — a human-readable secondary notes file.

`investigation_report.md` remains deterministic and primary.

## Validation and failure modes

The response must be valid JSON with the required notes keys. The workflow caps list sizes and string lengths, blocks raw-value markers and authoritative/verdict language, and avoids writing the raw model response when validation fails. If validation fails, `llm_investigation_notes.json` records `llm_status: failed_validation` with safe error summaries, and no successful Markdown notes are written.

If the optional `openai` package is missing, install the `llm` extra. If `OPENAI_API_KEY` is missing, the CLI exits cleanly with a user-facing error. The OpenAI path uses the Responses API without tools: no web search, file search, code interpreter, file uploads, function calling, MCP, or streaming requirement.
