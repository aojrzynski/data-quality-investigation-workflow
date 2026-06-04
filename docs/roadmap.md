# Roadmap

This roadmap describes the intended pull request sequence for building the Data Quality Investigation Workflow. It is deliberately high level so each PR can stay focused and reviewable.

## Planned PR sequence

- **PR #1: repo scaffold and trace stub — implemented**
  Added the Python package scaffold, `dq-investigate` CLI entry point, scaffold trace artifact, tests, CI, README, and this roadmap.

- **PR #2: dataset intake and safe profiling — implemented**
  Added local CSV/XLSX/XLSM dataset intake, optional Excel sheet selection, safe aggregate `dataset_profile.json`, and profiled-run trace metadata without writing raw rows to artifacts or sending raw rows to any external service.

- **PR #3: issue intake and investigation case file — current / implemented**
  Adds `investigation_case.json` as the issue-led case file foundation, records whether input was supplied, references dataset profile and trace artifacts when available, and preserves the no-classification/no-investigation boundary.

- **PR #4: investigation planning and route selection**
  Add a planning layer that maps supported issue types to investigation routes without running checks yet.

- **PR #5: deterministic checks and evidence ledger**
  Add deterministic checks for selected issue routes and record results in an evidence ledger.

- **PR #6: baseline comparison support**
  Add support for comparing the current dataset against a supplied baseline or previous run artifact.

- **PR #7: hypothesis tracker and findings builder**
  Add hypothesis tracking and a findings artifact that separates confirmed, not confirmed, and still unclear items.

- **PR #8: Markdown report and deeper docs**
  Add a human-readable investigation report and expand usage documentation.

- **PR #9: optional bounded LLM investigation notes**
  Add optional LLM-generated notes over safe evidence only. LLM output will not be treated as authoritative.

- **PR #10: source comment/docstring pass**
  Review code comments and docstrings for clarity after the main workflow pieces are in place.
