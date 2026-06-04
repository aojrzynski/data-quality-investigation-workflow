from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("pandas")

from data_quality_investigation_workflow.intake import load_dataset  # noqa: E402
from data_quality_investigation_workflow.profiling import build_dataset_profile  # noqa: E402

FORBIDDEN_KEYS = {
    "raw_rows",
    "sample_rows",
    "sampled_rows",
    "first_rows",
    "last_rows",
    "example_values",
    "examples",
    "top_values",
    "distinct_values",
    "value_preview",
    "value_previews",
    "raw_failing_records",
}


def test_build_dataset_profile_contains_safe_aggregate_summaries() -> None:
    loaded = load_dataset(Path("examples/customer_quality_snapshot.csv"))

    profile = build_dataset_profile(loaded)

    assert profile["artifact_type"] == "dataset_profile"
    assert profile["profile_version"] == "0.1"
    assert profile["source"] == {
        "file_name": "customer_quality_snapshot.csv",
        "file_extension": ".csv",
        "sheet_name": None,
    }
    assert profile["dataset"]["row_count"] == 12
    assert profile["dataset"]["column_count"] == 6
    assert len(profile["columns"]) == 6

    customer_id = _column(profile, "customer_id")
    assert customer_id["non_null_count"] == 12
    assert customer_id["null_count"] == 0
    assert customer_id["unique_count"] == 11
    assert customer_id["duplicate_value_count"] == 1

    email = _column(profile, "email")
    assert email["null_count"] == 2
    assert email["unique_count"] == 10
    assert "text" in email
    assert "average_length" in email["text"]

    lifetime_value = _column(profile, "lifetime_value")
    assert lifetime_value["inferred_kind"] == "decimal"
    assert lifetime_value["numeric"]["min"] == 0.0
    assert lifetime_value["numeric"]["max"] == 510.1
    assert lifetime_value["numeric"]["mean"] > 0

    signup_date = _column(profile, "signup_date")
    assert signup_date["inferred_kind"] == "datetime"
    assert signup_date["datetime"]["parsed_non_null_count"] == 12
    assert signup_date["datetime"]["min_date"].startswith("2026-05-20")


def test_dataset_profile_does_not_include_raw_rows_or_value_previews() -> None:
    loaded = load_dataset(Path("examples/customer_quality_snapshot.csv"))
    profile = build_dataset_profile(loaded)

    assert _find_forbidden_keys(profile) == []
    serialized = json.dumps(profile)
    assert "avery@example.test" not in serialized
    assert "CUST-001" not in serialized


def _column(profile: dict[str, Any], name: str) -> dict[str, Any]:
    return next(column for column in profile["columns"] if column["name"] == name)


def _find_forbidden_keys(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS:
                found.append(key)
            found.extend(_find_forbidden_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_find_forbidden_keys(child))
    return found
