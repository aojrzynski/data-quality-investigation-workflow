"""Safe aggregate dataset profiling.

Profiling turns a loaded local file into aggregate facts: row counts, column
counts, null counts, broad inferred kinds, and safe summary metrics. It excludes
raw rows, sampled records, top values, example values, row numbers, and distinct
value lists. Inferred kind is a practical hint for routing and checks, not a
semantic guarantee about what a column means.
"""

from __future__ import annotations

from collections import Counter
from typing import Any
import warnings

import pandas as pd
from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_float_dtype,
    is_integer_dtype,
    is_numeric_dtype,
    is_object_dtype,
    is_string_dtype,
)

from data_quality_investigation_workflow.intake import LoadedDataset

PROFILE_VERSION = "0.1"
SAFETY_NOTES = [
    "This profile contains aggregate summaries only.",
    "Raw rows, sampled records, example values, top values, and distinct value lists are not included.",
]


def build_dataset_profile(loaded_dataset: LoadedDataset) -> dict[str, Any]:
    """Build a raw-value-safe aggregate profile for a loaded dataset."""
    dataframe = loaded_dataset.dataframe
    column_names = loaded_dataset.column_names

    # The profile is the first evidence-adjacent artifact. It captures dataset
    # shape without writing examples, previews, or value lists.
    return {
        "artifact_type": "dataset_profile",
        "profile_version": PROFILE_VERSION,
        "source": {
            "file_name": loaded_dataset.file_name,
            "file_extension": loaded_dataset.file_extension,
            "sheet_name": loaded_dataset.sheet_name,
        },
        "dataset": {
            "row_count": loaded_dataset.row_count,
            "column_count": loaded_dataset.column_count,
            "column_names": column_names,
            "duplicate_column_names": _duplicate_column_names(column_names),
            "empty_column_names": _empty_column_names(column_names),
        },
        "columns": [
            _profile_column(
                dataframe.iloc[:, position], column_names[position], position
            )
            for position in range(loaded_dataset.column_count)
        ],
        "safety_notes": SAFETY_NOTES,
    }


def _profile_column(series: pd.Series, name: str, position: int) -> dict[str, Any]:
    """Build aggregate metrics for one column without raw values or previews."""
    row_count = int(len(series))
    non_null_count = int(series.notna().sum())
    null_count = row_count - non_null_count
    unique_count = int(series.nunique(dropna=True))
    duplicate_value_count = max(non_null_count - unique_count, 0)
    kind = _infer_kind(series)

    profile: dict[str, Any] = {
        "name": name,
        "position": position,
        "pandas_dtype": str(series.dtype),
        "inferred_kind": kind,
        "non_null_count": non_null_count,
        "null_count": null_count,
        "null_percentage": _percentage(null_count, row_count),
        "unique_count": unique_count,
        "unique_percentage": _percentage(unique_count, non_null_count),
        "duplicate_value_count": duplicate_value_count,
    }

    # Kind-specific sections add safe aggregate metrics only. The inferred kind
    # helps later checks choose columns, but it is not a semantic declaration.
    if kind in {"integer", "decimal"}:
        profile["numeric"] = _numeric_stats(series)
    elif kind == "datetime":
        profile["datetime"] = _datetime_stats(series)
    elif kind == "text":
        profile["text"] = _text_length_stats(series)

    return profile


def _infer_kind(series: pd.Series) -> str:
    """Infer a broad column kind used as a routing hint, not semantic truth."""
    if int(series.notna().sum()) == 0:
        return "empty"
    if is_bool_dtype(series):
        return "boolean"
    if is_integer_dtype(series):
        return "integer"
    if is_float_dtype(series):
        return "decimal"
    if is_datetime64_any_dtype(series):
        return "datetime"
    if is_numeric_dtype(series):
        return "decimal"

    if is_object_dtype(series) or is_string_dtype(series):
        datetime_summary = _parsed_datetimes(series)
        if datetime_summary is not None:
            parsed_non_null_count, _parsed = datetime_summary
            parse_success = _percentage(
                parsed_non_null_count, int(series.notna().sum())
            )
            if parse_success >= 80.0:
                return "datetime"
        return "text"

    return "mixed_or_unknown"


def _numeric_stats(series: pd.Series) -> dict[str, Any]:
    """Return bounded numeric aggregates without preserving individual values."""
    numeric = pd.to_numeric(series, errors="coerce")
    non_null_numeric = numeric.dropna()
    if non_null_numeric.empty:
        return {"min": None, "max": None, "mean": None}
    return {
        "min": _json_scalar(non_null_numeric.min()),
        "max": _json_scalar(non_null_numeric.max()),
        "mean": _json_scalar(non_null_numeric.mean()),
    }


def _datetime_stats(series: pd.Series) -> dict[str, Any]:
    """Return date range and parse counts without listing dates or rows."""
    parsed_summary = _parsed_datetimes(series)
    if parsed_summary is None:
        parsed_non_null_count = int(series.notna().sum())
        parsed = series.dropna()
    else:
        parsed_non_null_count, parsed = parsed_summary

    non_null_count = int(series.notna().sum())
    parsed = parsed.dropna()
    return {
        "parsed_non_null_count": parsed_non_null_count,
        "parse_success_percentage": _percentage(parsed_non_null_count, non_null_count),
        "min_date": _datetime_to_iso(parsed.min()) if not parsed.empty else None,
        "max_date": _datetime_to_iso(parsed.max()) if not parsed.empty else None,
    }


def _text_length_stats(series: pd.Series) -> dict[str, Any]:
    """Return text length aggregates without storing text values."""
    text_lengths = series.dropna().astype(str).str.len()
    if text_lengths.empty:
        return {"min_length": None, "max_length": None, "average_length": None}
    return {
        "min_length": int(text_lengths.min()),
        "max_length": int(text_lengths.max()),
        "average_length": _json_scalar(text_lengths.mean()),
    }


def _parsed_datetimes(series: pd.Series) -> tuple[int, pd.Series] | None:
    if is_datetime64_any_dtype(series):
        parsed = pd.to_datetime(series, errors="coerce")
        return int(parsed.notna().sum()), parsed

    non_null = series.dropna()
    if non_null.empty:
        return None

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed = pd.to_datetime(non_null, errors="coerce")
    return int(parsed.notna().sum()), parsed


def _percentage(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _duplicate_column_names(column_names: list[str]) -> list[str]:
    counts = Counter(column_names)
    return [name for name, count in counts.items() if count > 1]


def _empty_column_names(column_names: list[str]) -> list[str]:
    return [
        name
        for name in column_names
        if name.strip() == "" or name.startswith("Unnamed:")
    ]


def _json_scalar(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _datetime_to_iso(value: Any) -> str | None:
    if pd.isna(value):
        return None
    timestamp = pd.Timestamp(value)
    return timestamp.isoformat()
