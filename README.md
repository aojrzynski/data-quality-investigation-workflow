# Data Quality Investigation Workflow

> Given a suspected data quality issue, what should we check, what evidence do we have, and what should a human review next?

Data Quality Investigation Workflow is a local-first Python CLI for issue-led data quality investigations. It takes an issue statement, can optionally read current and baseline local datasets, creates safe aggregate JSON artifacts, and writes a deterministic Markdown report. Optional LLM notes are disabled by default and are secondary to the deterministic artifacts. Human review remains the final authority.

## The problem

Data quality investigations often start with a practical concern, such as:

- customer IDs started duplicating;
- nulls increased in an important field;
- totals changed between extracts;
- dates have unexpected gaps;
- the schema changed;
- category patterns shifted.

The hard part is not only spotting a signal. It is keeping the investigation reproducible, safe to inspect, and clear about what still needs human review.

## What this project does

For each run, the workflow can:

1. record the investigation case;
2. profile the current dataset if supplied;
3. profile a baseline dataset if supplied;
4. choose a planning route from deterministic rules;
5. compare current and baseline aggregates if a baseline is supplied;
6. run deterministic aggregate checks;
7. record evidence;
8. turn evidence into cautious hypotheses;
9. summarize review-oriented findings;
10. write a deterministic Markdown report;
11. optionally write bounded LLM notes if explicitly requested.

The result is review material, not an automated decision.

## What to open first

After a run, start here:

- Open `investigation_report.md` first for a human-readable summary.
- Open `investigation_trace.json` to see what was written and what stage ran.
- Open `evidence_ledger.json` for deterministic evidence.
- Open `hypothesis_tracker.json` and `investigation_findings.json` for interpretation aids.
- Open `llm_investigation_notes.md` only if `--llm-notes` was explicitly used.

## Why deterministic evidence matters

The same inputs should produce the same evidence-supported signal. The evidence should be inspectable without relying on model wording, hidden state, or raw record samples.

This workflow writes aggregate artifacts before narrative summaries. Later artifacts refer back to evidence IDs and hypothesis IDs instead of copying raw payloads around. Raw rows are not written into artifacts.

## Why not just ask an LLM?

No LLM is used unless you explicitly pass `--llm-notes`.

The default path is deterministic and local. Optional LLM notes are downstream of the deterministic artifacts and use only `llm_safe_input_summary.json`. The LLM does not see raw rows. Its output is non-authoritative and does not approve, certify, trust, fix, identify root cause, or confirm the issue.

## Quick start

```bash
python -m pip install -e ".[dev]"
dq-investigate --help
dq-investigate --version
python -m data_quality_investigation_workflow.cli --help
```

## Example commands

Deterministic runs do not require `OPENAI_API_KEY`.

Plan-only run:

```bash
dq-investigate --issue "Customer IDs have started duplicating" --output-dir outputs/plan_run
```

Current dataset + issue run:

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --output-dir outputs/customer_report_run
```

Recommended current + baseline demo:

```bash
dq-investigate --input examples/customer_quality_snapshot.csv --baseline examples/customer_quality_snapshot_baseline.csv --issue "Nulls increased in the customer email field" --output-dir outputs/baseline_report_run
```

Excel current + baseline run:

```bash
dq-investigate --input path/to/current.xlsx --sheet Current --baseline path/to/baseline.xlsx --baseline-sheet Baseline --issue "The report total dropped unexpectedly" --output-dir outputs/excel_report_run
```

Optional LLM notes run:

```bash
python -m pip install -e ".[dev,llm]"
export OPENAI_API_KEY="..."
dq-investigate --input examples/customer_quality_snapshot.csv --issue "Customer IDs have started duplicating" --llm-notes --output-dir outputs/customer_llm_notes_run
```

PowerShell API key setup:

```powershell
$env:OPENAI_API_KEY="..."
```

## Output artifacts

| Artifact | When written | Purpose |
| --- | --- | --- |
| `investigation_case.json` | Every successful run | Records the issue, inputs, artifact paths, workflow status, scope, and authority boundaries. |
| `dataset_profile.json` | When `--input` is supplied and loaded | Records aggregate current-dataset profile details such as row counts, column counts, null counts, schema metadata, and type summaries. |
| `baseline_profile.json` | When `--baseline` is supplied and loaded | Records the same safe aggregate profile details for the baseline dataset. |
| `investigation_plan.json` | Every successful run | Records deterministic issue classification, selected route, candidate columns, planned checks, and limitations. |
| `baseline_comparison.json` | When current and baseline datasets are supplied | Records aggregate current-vs-baseline comparison signals. |
| `evidence_ledger.json` | When an input dataset is supplied | Records deterministic aggregate evidence items and checks not run. |
| `hypothesis_tracker.json` | When input and issue are supplied | Maps evidence IDs into cautious hypotheses for human review. |
| `investigation_findings.json` | When input and issue are supplied | Summarizes evidence-supported signals, unclear items, and suggested human checks. |
| `investigation_report.md` | When input and issue are supplied | Gives a human-readable deterministic summary of the investigation artifacts. |
| `llm_safe_input_summary.json` | Only with `--llm-notes` | Summarizes deterministic artifacts into a bounded aggregate-only input for optional LLM notes. |
| `llm_investigation_notes.json` | Only with `--llm-notes` | Records validated optional LLM notes or validation errors. |
| `llm_investigation_notes.md` | Only with `--llm-notes` and valid LLM output | Renders optional LLM notes for easier reading. |
| `investigation_trace.json` | Every successful run | Records concise run metadata, stage, status, and artifact paths. |

The JSON artifacts are intentionally separate. They make it easier to inspect each stage, compare runs, and see what the Markdown report was based on.

## Safety boundaries

Allowed:

- column names;
- aggregate counts;
- percentages;
- evidence IDs;
- hypothesis IDs;
- artifact paths;
- human review prompts.

Not included:

- raw rows;
- sampled rows;
- example values;
- top values;
- distinct value lists;
- duplicated values;
- category labels;
- row numbers;
- raw failing records;
- generated code.

## Authority boundary

The tool does not:

- identify root cause;
- confirm the issue as final;
- approve, fix, certify, or trust a dataset;
- say a dataset is production-ready;
- make legal, compliance, privacy, or governance verdicts;
- replace human review.

## Project structure

```text
src/data_quality_investigation_workflow/
├── cli.py                 # command-line entry point and artifact sequence
├── intake.py              # local CSV/Excel loading
├── profiling.py           # aggregate dataset profiling
├── issue_classifier.py    # deterministic issue routing hints
├── planning.py            # investigation plan artifact
├── baseline.py            # aggregate current-vs-baseline comparison
├── checks.py              # deterministic aggregate checks
├── evidence.py            # evidence ledger artifact
├── hypotheses.py          # cautious hypotheses from evidence IDs
├── findings.py            # review-oriented finding summaries
├── reporting.py           # deterministic Markdown report
├── llm_notes.py           # optional bounded LLM notes artifacts
└── trace.py               # concise run trace
```

## Run tests

```bash
python -m pip install -e ".[dev]"
python -m compileall src tests
python -m pytest -q
python -m ruff check .
```

Tests do not call a real LLM and do not require `OPENAI_API_KEY`.

## Limitations and non-goals

- Local files only.
- No database, cloud, or SaaS connectors.
- No remediation or data fixing.
- No root-cause decision.
- No final approval or production-readiness decision.
- No full governance process.
- Simple deterministic keyword route selection.
- Date-gap checks assume daily cadence where relevant.

## Further reading

- [Architecture](docs/architecture.md)
- [Design principles](docs/design_principles.md)
- [Artifacts](docs/artifacts.md)
- [Example commands](docs/example_commands.md)
- [Safety boundaries](docs/safety_boundaries.md)
- [Demo workflow](docs/demo_workflow.md)
- [Optional LLM notes](docs/llm_notes.md)
- [Roadmap](docs/roadmap.md)
