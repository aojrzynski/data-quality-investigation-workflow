"""User-facing errors for expected workflow failures.

Expected problems, such as missing local files or invalid flag combinations,
should become clean CLI messages instead of stack traces. Custom exceptions let
the command-line layer distinguish user-correctable issues from unexpected
programming errors.
"""

from __future__ import annotations


class WorkflowUserError(Exception):
    """Base class for expected errors that should not show stack traces."""


class DatasetIntakeError(WorkflowUserError):
    """Raised when a local dataset cannot be loaded as requested."""
