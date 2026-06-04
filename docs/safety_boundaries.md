# Safety boundaries

Data Quality Investigation Workflow is designed around deterministic aggregate artifacts and human review.

## Not included

The current implementation does not write or send:

- raw rows;
- sampled rows;
- first rows or last rows;
- example values;
- top values;
- distinct value lists;
- raw failing records;
- duplicated values;
- category labels;
- full category distributions;
- row numbers;
- generated code;
- LLM prompts or LLM output.

It also does not decide:

- root cause;
- legal verdicts;
- compliance verdicts;
- privacy verdicts;
- governance verdicts;
- dataset approval, certification, trust, or production readiness.

## Allowed content

The artifacts may include:

- column names;
- row counts;
- column counts;
- aggregate counts;
- aggregate percentages;
- inferred data kinds;
- safe schema metadata;
- evidence IDs;
- hypothesis IDs;
- signal IDs;
- recommended human review checks.

## LLM boundary

No LLM is used unless `--llm-notes` is explicitly supplied. Optional bounded LLM notes use only safe aggregate artifacts and remain separate from deterministic evidence generation.

## Human authority

The workflow helps reviewers investigate. It does not replace human judgment, approve datasets, certify datasets, or make legal/compliance/privacy/governance decisions. Human review remains the final authority.

## Optional LLM notes safety

`--llm-notes` is explicit opt-in and disabled by default. The LLM receives only `llm_safe_input_summary.json`, built from deterministic safe aggregate artifacts. It is not given raw rows, sampled rows, example values, top values, distinct value lists, duplicated values, category labels, full distributions, row numbers, or raw failing records. LLM output is validated before successful notes are written and remains non-authoritative. It must not identify root cause, confirm an issue, approve, certify, fix, trust, or make legal, compliance, privacy, or governance verdicts. No LLM tools, file uploads, web search, file search, code interpreter, function calling, or MCP are used.
