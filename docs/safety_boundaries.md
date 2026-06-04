# Safety boundaries

The workflow is designed to produce safe aggregate review material. It is not designed to copy raw data into artifacts, prompts, or reports.

## What is allowed

Artifacts may include:

- column names;
- aggregate counts;
- percentages;
- inferred data kinds;
- evidence IDs;
- hypothesis IDs;
- artifact paths;
- human review prompts.

These are enough to describe an evidence-supported signal without exposing row-level records.

## What is not included

Artifacts and optional LLM prompts do not include:

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

## Why top values and examples are avoided

Top values, example values, and category labels can reveal real people, customers, accounts, locations, or business terms. Even when they look harmless, they are still row-derived values. The workflow avoids them so review material stays aggregate-only.

## Optional LLM boundary

No LLM is used unless `--llm-notes` is supplied. When it is supplied, the model receives only `llm_safe_input_summary.json`. That summary is built from deterministic aggregate artifacts and is validated before use.

## Authority boundary

The safety boundary does not make the tool a compliance system. The workflow does not identify root cause, approve a dataset, certify a dataset, make legal or privacy verdicts, or replace human review.
