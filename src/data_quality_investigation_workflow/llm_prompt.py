"""Prompt builders for optional bounded LLM investigation notes."""

from __future__ import annotations

import json
from typing import Any

SYSTEM_INSTRUCTIONS = """You are helping produce optional reviewer notes for a data quality investigation. You must only use the supplied safe aggregate summary. Do not infer root cause. Do not identify root cause. Do not approve, certify, trust, fix, or make legal/compliance/privacy/governance verdicts. Do not ask for or mention raw rows. Do not invent evidence. Return only valid JSON with the required schema."""

OUTPUT_SCHEMA_INSTRUCTIONS = """Return JSON only. Do not include prose outside JSON. The JSON object must contain exactly these keys: review_summary (string), suggested_follow_up_questions (list of strings), suggested_human_checks (list of strings), communication_notes (list of strings), limitations_to_keep_visible (list of strings). Keep notes bounded, non-authoritative, and grounded only in the supplied safe aggregate summary."""


def build_llm_notes_prompt(safe_input_summary: dict[str, Any]) -> str:
    """Build the bounded user prompt from the deterministic safe input summary."""
    summary_json = json.dumps(safe_input_summary, indent=2, sort_keys=False)
    return "\n\n".join(
        [
            SYSTEM_INSTRUCTIONS,
            OUTPUT_SCHEMA_INSTRUCTIONS,
            "Safe aggregate input summary:",
            summary_json,
        ]
    )
