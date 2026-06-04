"""Deterministic issue classification for investigation planning."""

from __future__ import annotations

from typing import Any

CLASSIFICATION_METHOD = "deterministic_keyword_rules"
CLASSIFICATION_PRECEDENCE = [
    "schema_change",
    "duplicate_key",
    "null_increase",
    "date_gap",
    "total_change",
    "category_shift",
    "general_suspected_issue",
]

ISSUE_PATTERNS = {
    "schema_change": [
        "schema",
        "column missing",
        "missing column",
        "new column",
        "removed column",
        "field missing",
        "missing field",
        "header changed",
    ],
    "duplicate_key": [
        "duplicate",
        "duplicated",
        "duplicating",
        "repeating",
        "repeated",
        "same id",
        "duplicate id",
        "duplicate key",
    ],
    "null_increase": [
        "null",
        "nulls",
        "blank",
        "missing value",
        "empty field",
        "blank more often",
        "missing email",
        "increased nulls",
    ],
    "date_gap": [
        "gap",
        "missing date",
        "missing day",
        "date gap",
        "no records for date",
        "no records for one day",
        "missing period",
    ],
    "total_change": [
        "total",
        "sum",
        "dropped",
        "increased",
        "decreased",
        "report total",
        "count changed",
        "row count changed",
        "volume changed",
    ],
    "category_shift": [
        "category",
        "status",
        "segment",
        "region",
        "value spiked",
        "spiked",
        "disappeared",
        "distribution",
        "mix changed",
    ],
}

ROUTE_NAMES = {
    "duplicate_key": "duplicate_key_investigation",
    "null_increase": "null_increase_investigation",
    "date_gap": "date_gap_investigation",
    "category_shift": "category_shift_investigation",
    "total_change": "total_change_investigation",
    "schema_change": "schema_change_investigation",
    "general_suspected_issue": "general_investigation",
    "missing_issue_statement": "missing_issue_statement",
}

ROUTE_REASONS = {
    "duplicate_key": "The issue statement suggests duplicate identifiers or key values.",
    "null_increase": "The issue statement suggests missing, blank, empty, or null values.",
    "date_gap": "The issue statement suggests missing dates, periods, or time gaps.",
    "category_shift": "The issue statement suggests a category, status, segment, region, or distribution shift.",
    "total_change": "The issue statement suggests a changed count, volume, sum, or total.",
    "schema_change": "The issue statement suggests a changed schema, column, field, or header.",
    "general_suspected_issue": "The issue statement does not match a supported PR #4 route keyword pattern.",
    "missing_issue_statement": "No issue statement was supplied, so meaningful route selection is not ready.",
}

CLASSIFICATION_LIMITATIONS = [
    "Keyword classification is a planning aid only.",
    "The issue type is not evidence that the issue exists.",
]


def classify_issue(issue_statement: str | None) -> dict[str, Any]:
    """Classify an issue statement using deterministic keyword precedence."""
    if issue_statement is None or issue_statement.strip() == "":
        return {
            "statement": issue_statement,
            "provided": False,
            "classification_status": "missing_issue_statement",
            "issue_type": "missing_issue_statement",
            "matched_terms": [],
            "classification_method": CLASSIFICATION_METHOD,
            "classification_limitations": CLASSIFICATION_LIMITATIONS,
            "selected_route": ROUTE_NAMES["missing_issue_statement"],
        }

    normalized = issue_statement.casefold()
    matched_by_type = {
        issue_type: [term for term in ISSUE_PATTERNS[issue_type] if term in normalized]
        for issue_type in ISSUE_PATTERNS
    }
    for issue_type in CLASSIFICATION_PRECEDENCE:
        if issue_type == "general_suspected_issue" or matched_by_type.get(issue_type):
            return {
                "statement": issue_statement,
                "provided": True,
                "classification_status": "classified_for_planning",
                "issue_type": issue_type,
                "matched_terms": matched_by_type.get(issue_type, []),
                "classification_method": CLASSIFICATION_METHOD,
                "classification_limitations": CLASSIFICATION_LIMITATIONS,
                "selected_route": ROUTE_NAMES[issue_type],
            }

    raise AssertionError("classification precedence should always return a route")
