# Data Quality Investigation Workflow

> Given a suspected data quality issue, what should we check, what evidence do we have, and what should a human review next?

Data Quality Investigation Workflow is a local-first command-line tool for investigating a reported data quality concern.

A reviewer gives it an issue statement, such as “customer IDs have started duplicating” or “nulls increased in the email field”. The tool can then read a local current dataset, and optionally a local baseline dataset, and produce review material that explains what was checked, what aggregate evidence was found, and what still needs a human decision.

It does not fix the data. It does not prove root cause. It does not approve or certify a dataset. It helps structure the investigation so the reviewer has clearer evidence and better next questions. Human review remains the final authority.

> [!NOTE]
> **Part of the Data Agent Suite.**
> 
> This repo is one of 10 local-first data/AI agents built around practical data workflows, deterministic evidence, bounded LLM use, and review-ready artifacts.
> 
> The full ordered list of agents is included near the bottom of this README.
> 
> See the full suite overview: [Data Agent Suite](https://aojrzynski.github.io/agents/)

## The problem

Data quality issues often begin as reports or suspicions. Someone notices that a report total dropped, customer IDs duplicated, dates are missing, or an important field has more blanks than expected.

At that point, the team needs to investigate. A suspected issue is not the same thing as confirmed evidence. The concern may be real, partly real, caused by an upstream change, caused by a reporting change, or not visible in the current file at all.

A good investigation needs to keep several things separate:

- what was reported;
- what the current data shows;
- what changed compared with a baseline;
- what evidence supports the concern;
- what is still unclear;
- what a human should check next.

The hard part is keeping that review structured without exposing raw rows unnecessarily or letting generated text become the decision.

## What this project does

For each run, the workflow:

1. Records the reported issue as an investigation case.
2. Profiles the current file using safe aggregate counts.
3. Profiles a baseline file if supplied.
4. Chooses a simple investigation route using deterministic keyword rules.
5. Compares current and baseline aggregate signals when possible.
6. Runs deterministic checks related to the selected route.
7. Records aggregate evidence in an evidence ledger.
8. Maps evidence into cautious hypotheses.
9. Summarizes review-oriented findings.
10. Writes a Markdown report for humans.
11. Optionally writes bounded LLM notes only when explicitly requested.

The output is review material, not a verdict. The artifacts help a person understand what to inspect next.

## What to open first

After a run, start here:

- Open `investigation_report.md` first for a human-readable summary.
- Open `investigation_trace.json` to see what was written and what stage ran.
- Open `evidence_ledger.json` for deterministic evidence.
- Open `hypothesis_tracker.json` and `investigation_findings.json` for interpretation aids.
- Open `llm_investigation_notes.md` only if `--llm-notes` was explicitly used.

## Why deterministic evidence matters

Deterministic means the same inputs should produce the same outputs. This matters because reviewers need repeatable evidence, not a different answer each time the tool runs.

The workflow records aggregate signals such as row counts, null percentages, duplicate counts, schema differences, date range signals, and current-vs-baseline differences. It writes those signals before it writes narrative summaries.

Later summaries refer back to evidence IDs and hypothesis IDs instead of copying raw payloads around. This makes the investigation easier to check, challenge, and rerun. Raw rows are not written into artifacts.

## Why not just ask an LLM?

An LLM may be useful for wording, cautious summaries, or follow-up questions. But it should not be the source of evidence.

An LLM should not see raw dataset rows by default. It should not decide whether the issue is real, why it happened, whether the dataset is safe, or whether it is approved.

This tool therefore builds deterministic artifacts first. Optional LLM notes are disabled by default, require explicit `--llm-notes`, use only `llm_safe_input_summary.json`, and are non-authoritative. No LLM is used unless you explicitly pass `--llm-notes`.

## Why there are several artifacts

Each artifact represents one stage of the investigation. This is deliberate so reviewers can inspect the chain from reported issue, to profile, to plan, to evidence, to hypotheses, to findings, to report.

The Markdown report is the easiest file to read first. The JSON files are there so the evidence, artifact references, and trace are inspectable. The trace shows what ran and what was written without duplicating full evidence payloads or report text.

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

---

> [!NOTE]
> **Data Agent Suite**  
> This repo is part of the **Data Agent Suite**: 10 local-first data/AI agents focused on practical data workflows, deterministic evidence, bounded LLM use, and review-ready artifacts.
> 
> See the full suite overview: [Data Agent Suite](https://aojrzynski.github.io/agents/)
>
> 1. [Data Quality Triage Agent](https://github.com/aojrzynski/data-quality-triage-agent)
> 2. [Data Reconciliation Agent](https://github.com/aojrzynski/data-reconciliation-agent)
> 3. [Data Dictionary Agent](https://github.com/aojrzynski/data-dictionary-agent)
> 4. [Data Contract Review Agent](https://github.com/aojrzynski/data-contract-review-agent)
> 5. [Sensitive Field Review Agent](https://github.com/aojrzynski/sensitive-field-review-agent)
> 6. [Data Test Suggestion Agent](https://github.com/aojrzynski/data-test-suggestion-agent)
> 7. [Dataset Onboarding Reviewer Workflow](https://github.com/aojrzynski/dataset-onboarding-reviewer-workflow)
> 8. **Data Quality Investigation Workflow**
> 9. [Project Evidence Review Agent](https://github.com/aojrzynski/project-evidence-review-agent)
> 10. [Data Migration Readiness Review Agent](https://github.com/aojrzynski/data-migration-readiness-review-agent)
