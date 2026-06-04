# Roadmap

This roadmap describes the intended pull request sequence for building the Data Quality Investigation Workflow. It is deliberately high level so each PR can stay focused and reviewable.

## Planned PR sequence

- **PR #1: repo scaffold and trace stub — implemented**
  Added the Python package scaffold, `dq-investigate` CLI entry point, scaffold trace artifact, tests, CI, README, and this roadmap.

- **PR #2: dataset intake and safe profiling — implemented**
  Added local CSV/XLSX/XLSM dataset intake, optional Excel sheet selection, safe aggregate `dataset_profile.json`, and profiled-run trace metadata without writing raw rows to artifacts or sending raw rows to any external service.

- **PR #3: issue intake and investigation case file — implemented**
  Added `investigation_case.json` as the issue-led case file foundation, records whether input was supplied, references dataset profile and trace artifacts when available, and preserved the no-investigation/no-findings boundary before planning classification was added.

- **PR #4: investigation planning and route selection — implemented**
  Added deterministic issue classification for planning purposes only, selected planned routes, and wrote `investigation_plan.json` without running checks.

- **PR #5: deterministic checks and evidence ledger — implemented**
  Added deterministic current-dataset checks for selected issue routes and recorded aggregate-only results in `evidence_ledger.json`.

- **PR #6: baseline comparison support — implemented**
  Added support for comparing the current dataset against a supplied baseline dataset with aggregate-only baseline comparison evidence.

- **PR #7: hypothesis tracker and findings builder — implemented**
  Added `hypothesis_tracker.json` and `investigation_findings.json` for input + issue runs, mapping deterministic evidence IDs into cautious route-specific hypotheses and review-oriented finding summaries.

- **PR #8: Markdown report and deeper docs — current / implemented**
  Added `investigation_report.md` for input + issue runs and expanded README/docs for architecture, artifacts, commands, safety boundaries, and demo usage.

- **PR #9: optional bounded LLM investigation notes — future**
  Optional bounded LLM-generated notes over safe evidence only. LLM output must not be treated as authoritative.

- **PR #10: source comment/docstring pass — future**
  Review code comments and docstrings for clarity after the main workflow pieces are in place.
