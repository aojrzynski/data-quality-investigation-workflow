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

No LLM is used in the current implementation. Optional bounded LLM notes remain future work and must use only safe aggregate artifacts if added later.

## Human authority

The workflow helps reviewers investigate. It does not replace human judgment, approve datasets, certify datasets, or make legal/compliance/privacy/governance decisions. Human review remains the final authority.
