"""Optional OpenAI client wrapper for bounded LLM notes.

The OpenAI import stays optional through the llm extra. Deterministic runs do
not need OpenAI credentials or the OpenAI package.
"""

from __future__ import annotations

import importlib
import os
from typing import Any

from data_quality_investigation_workflow.errors import WorkflowUserError

MISSING_OPENAI_PACKAGE_MESSAGE = (
    "Optional LLM notes require the 'openai' package. Install with the llm extra, "
    "for example: python -m pip install -e '.[dev,llm]'"
)
MISSING_OPENAI_KEY_MESSAGE = "OPENAI_API_KEY is required when --llm-notes is supplied."


class OpenAIResponsesNotesClient:
    """Small wrapper around the optional OpenAI Responses API path."""

    def __init__(self, *, timeout: float | None = None) -> None:
        try:
            openai_module = importlib.import_module("openai")
        except ImportError as error:
            raise WorkflowUserError(MISSING_OPENAI_PACKAGE_MESSAGE) from error
        if not os.environ.get("OPENAI_API_KEY"):
            raise WorkflowUserError(MISSING_OPENAI_KEY_MESSAGE)
        self._client = openai_module.OpenAI(timeout=timeout) if timeout else openai_module.OpenAI()

    def create_notes(
        self,
        *,
        model: str,
        prompt: str,
        max_output_tokens: int | None = None,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": model,
            "input": prompt,
        }
        if max_output_tokens is not None:
            kwargs["max_output_tokens"] = max_output_tokens
        response = self._client.responses.create(**kwargs)
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str):
            return output_text
        return _extract_response_text(response)


def _extract_response_text(response: Any) -> str:
    output = getattr(response, "output", None)
    if not output:
        return ""
    text_parts: list[str] = []
    for item in output:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if isinstance(text, str):
                text_parts.append(text)
    return "".join(text_parts)
