from __future__ import annotations

import pytest

from data_quality_investigation_workflow.issue_classifier import classify_issue


@pytest.mark.parametrize(
    ("issue", "expected_type", "expected_route"),
    [
        ("Customer IDs have started duplicating", "duplicate_key", "duplicate_key_investigation"),
        ("Nulls increased in the customer email field", "null_increase", "null_increase_investigation"),
        ("There is a missing date in the daily feed", "date_gap", "date_gap_investigation"),
        ("Status values spiked for one region", "category_shift", "category_shift_investigation"),
        ("The report total dropped yesterday", "total_change", "total_change_investigation"),
        ("A required column missing from the file", "schema_change", "schema_change_investigation"),
        ("Something looks wrong in the extract", "general_suspected_issue", "general_investigation"),
        (None, "missing_issue_statement", "missing_issue_statement"),
    ],
)
def test_classify_issue_maps_supported_issue_types(
    issue: str | None, expected_type: str, expected_route: str
) -> None:
    classification = classify_issue(issue)

    assert classification["issue_type"] == expected_type
    assert classification["selected_route"] == expected_route


def test_classify_issue_uses_documented_precedence() -> None:
    classification = classify_issue("Duplicate IDs and a missing column appeared")

    assert classification["issue_type"] == "schema_change"
    assert classification["selected_route"] == "schema_change_investigation"
    assert "missing column" in classification["matched_terms"]
