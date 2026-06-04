# Roadmap

This repository now represents a finished v1 scope for the local-first Data Quality Investigation Workflow.

## Implemented v1 scope

PR #1 through PR #9 built the main workflow:

- CLI entry point and output directory handling;
- local CSV/Excel intake;
- safe aggregate dataset profiling;
- investigation case file;
- deterministic issue classification and planning;
- safe aggregate baseline comparison;
- deterministic evidence ledger;
- hypothesis tracker;
- investigation findings;
- deterministic Markdown report;
- optional bounded LLM notes;
- concise investigation trace.

## Current non-goals

The v1 workflow does not include:

- database, cloud, or SaaS connectors;
- remediation or data fixing;
- root-cause decisions;
- final dataset approval;
- legal, compliance, privacy, or governance verdicts;
- generated code execution;
- raw-row prompts or raw-row artifacts.

## Possible future ideas

These are future ideas only. They are not implemented in v1.

- Richer deterministic issue-routing rules.
- Configurable date cadence instead of the current daily-cadence assumption.
- A policy/config file for thresholds.
- More baseline comparison options.
- Optional export formats.
- Database connectors only if safe, explicit, local-first where possible, and clearly configured.

Future work should keep the same boundaries: deterministic evidence first, safe aggregate artifacts, optional non-authoritative LLM notes, and human review as the final authority.
