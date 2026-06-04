"""User-facing errors for expected workflow failures."""

from __future__ import annotations


class WorkflowUserError(Exception):
    """Base class for expected errors that should not show stack traces."""


class DatasetIntakeError(WorkflowUserError):
    """Raised when a local dataset cannot be loaded as requested."""
