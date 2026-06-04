"""Safe aggregate current-vs-baseline comparison builders.

A baseline comparison answers a plain question: does the current file look
different from a previous or expected file in aggregate ways a reviewer should
inspect? This module compares row counts, schema shape, nulls, numeric totals,
date ranges, category shape, and duplicate signals.

The comparison is intentionally not a final finding. It writes aggregate signals
only and excludes raw rows, example values, category labels, duplicated values,
and missing date lists so the baseline artifact can be reviewed safely.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from data_quality_investigation_workflow.intake import LoadedDataset

BASELINE_PROFILE_FILENAME = "baseline_profile.json"
BASELINE_COMPARISON_FILENAME = "baseline_comparison.json"
COMPARISON_VERSION = "0.1"
DETAIL_LIMIT = 20
KEY_FALLBACK_TERMS = ["id", "key", "code", "number", "reference", "ref"]

SAFETY_NOTES = [
    "This comparison contains aggregate summaries only.",
    (
        "Raw rows, sampled records, example values, top values, distinct value lists, "
        "duplicated values, category labels, and raw failing records are not included."
    ),
]

LIMITATIONS = [
    "Baseline comparison records aggregate comparison signals only.",
    "The comparison does not identify root cause.",
    "The comparison does not create final findings.",
    "Date gap comparison assumes a daily cadence and does not write missing date lists.",
]

AUTHORITY_BOUNDARY = [
    "Baseline comparison signals are not final findings.",
    "Baseline comparison signal is not final evidence of root cause.",
    "Human review remains the final authority.",
]


def build_baseline_comparison(
    *,
    current_dataset: LoadedDataset,
    baseline_dataset: LoadedDataset,
    current_profile: dict[str, Any],
    baseline_profile: dict[str, Any],
    dataset_profile_path: Path,
    baseline_profile_path: Path,
    baseline_comparison_path: Path,
) -> dict[str, Any]:
    """Build a raw-value-safe aggregate current-vs-baseline comparison."""
    current_columns = current_profile.get("columns", [])
    baseline_columns = baseline_profile.get("columns", [])
    shared_column_names = _shared_column_names(current_profile, baseline_profile)

    return {
        "artifact_type": "baseline_comparison",
        "comparison_version": COMPARISON_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "current": _source_metadata(current_dataset),
        "baseline": _source_metadata(baseline_dataset),
        "row_count_comparison": _row_count_comparison(
            current_dataset, baseline_dataset
        ),
        "column_count_comparison": _column_count_comparison(
            current_dataset, baseline_dataset
        ),
        "schema_comparison": _schema_comparison(current_profile, baseline_profile),
        "null_comparison": _null_comparison(current_profile, baseline_profile),
        "numeric_comparison": _numeric_comparison(
            current_dataset, baseline_dataset, current_columns, baseline_columns
        ),
        "date_comparison": _date_comparison(
            current_dataset, baseline_dataset, current_columns, baseline_columns
        ),
        "category_shape_comparison": _category_shape_comparison(
            current_dataset, baseline_dataset, current_columns, baseline_columns
        ),
        "duplicate_comparison": _duplicate_comparison(
            current_dataset, baseline_dataset
        ),
        "general_summary": _general_summary(current_profile, baseline_profile),
        "comparison_signal_count": _comparison_signal_count(
            current_profile, baseline_profile
        ),
        "compared_column_count": len(shared_column_names),
        "safety_notes": SAFETY_NOTES,
        "limitations": LIMITATIONS,
        "artifacts": {
            "dataset_profile": dataset_profile_path.as_posix(),
            "baseline_profile": baseline_profile_path.as_posix(),
            "baseline_comparison": baseline_comparison_path.as_posix(),
        },
        "authority_boundary": AUTHORITY_BOUNDARY,
    }


def write_baseline_comparison(
    *,
    output_dir: str | Path,
    current_dataset: LoadedDataset,
    baseline_dataset: LoadedDataset,
    current_profile: dict[str, Any],
    baseline_profile: dict[str, Any],
    dataset_profile_path: Path,
    baseline_profile_path: Path,
) -> Path:
    """Write a safe aggregate baseline comparison artifact."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    comparison_path = output_path / BASELINE_COMPARISON_FILENAME
    comparison = build_baseline_comparison(
        current_dataset=current_dataset,
        baseline_dataset=baseline_dataset,
        current_profile=current_profile,
        baseline_profile=baseline_profile,
        dataset_profile_path=dataset_profile_path,
        baseline_profile_path=baseline_profile_path,
        baseline_comparison_path=comparison_path,
    )
    comparison_path.write_text(
        json.dumps(comparison, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return comparison_path


def _source_metadata(dataset: LoadedDataset) -> dict[str, Any]:
    return {
        "file_name": dataset.file_name,
        "file_extension": dataset.file_extension,
        "sheet_name": dataset.sheet_name,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
    }


def _row_count_comparison(
    current_dataset: LoadedDataset, baseline_dataset: LoadedDataset
) -> dict[str, Any]:
    delta = current_dataset.row_count - baseline_dataset.row_count
    return {
        "current_row_count": current_dataset.row_count,
        "baseline_row_count": baseline_dataset.row_count,
        "delta": delta,
        "delta_percentage": _percentage(delta, baseline_dataset.row_count),
    }


def _column_count_comparison(
    current_dataset: LoadedDataset, baseline_dataset: LoadedDataset
) -> dict[str, Any]:
    delta = current_dataset.column_count - baseline_dataset.column_count
    return {
        "current_column_count": current_dataset.column_count,
        "baseline_column_count": baseline_dataset.column_count,
        "delta": delta,
        "delta_percentage": _percentage(delta, baseline_dataset.column_count),
    }


def _schema_comparison(
    current_profile: dict[str, Any], baseline_profile: dict[str, Any]
) -> dict[str, Any]:
    current_dataset = current_profile.get("dataset", {})
    baseline_dataset = baseline_profile.get("dataset", {})
    current_names = [str(name) for name in current_dataset.get("column_names", [])]
    baseline_names = [str(name) for name in baseline_dataset.get("column_names", [])]
    shared = sorted(set(current_names) & set(baseline_names))
    kind_deltas = _kind_changes(current_profile, baseline_profile, shared)
    # Column-name deltas are bounded so the artifact stays readable and does not
    # become a large schema dump for wide files.
    return {
        "current_column_count": int(current_dataset.get("column_count", 0)),
        "baseline_column_count": int(baseline_dataset.get("column_count", 0)),
        "added_columns": sorted(set(current_names) - set(baseline_names))[
            :DETAIL_LIMIT
        ],
        "removed_columns": sorted(set(baseline_names) - set(current_names))[
            :DETAIL_LIMIT
        ],
        "shared_column_count": len(shared),
        "duplicate_column_name_count_current": len(
            current_dataset.get("duplicate_column_names", [])
        ),
        "duplicate_column_name_count_baseline": len(
            baseline_dataset.get("duplicate_column_names", [])
        ),
        "empty_column_name_count_current": len(
            current_dataset.get("empty_column_names", [])
        ),
        "empty_column_name_count_baseline": len(
            baseline_dataset.get("empty_column_names", [])
        ),
        "inferred_kind_changes": kind_deltas[:DETAIL_LIMIT],
        "inferred_kind_change_count": len(kind_deltas),
    }


def _null_comparison(
    current_profile: dict[str, Any], baseline_profile: dict[str, Any]
) -> dict[str, Any]:
    current_by_name = _columns_by_name(current_profile)
    baseline_by_name = _columns_by_name(baseline_profile)
    deltas = []
    for name in sorted(set(current_by_name) & set(baseline_by_name)):
        current = current_by_name[name]
        baseline = baseline_by_name[name]
        current_percentage = float(current.get("null_percentage", 0.0))
        baseline_percentage = float(baseline.get("null_percentage", 0.0))
        delta_percentage = round(current_percentage - baseline_percentage, 2)
        deltas.append(
            {
                "column_name": name,
                "current_null_count": int(current.get("null_count", 0)),
                "baseline_null_count": int(baseline.get("null_count", 0)),
                "current_null_percentage": current_percentage,
                "baseline_null_percentage": baseline_percentage,
                "delta_percentage": delta_percentage,
            }
        )
    non_zero_deltas = [delta for delta in deltas if delta["delta_percentage"] != 0]
    # Keep only the largest aggregate changes. The list contains column names and
    # counts, never raw cell values.
    detail_deltas = sorted(
        non_zero_deltas,
        key=lambda delta: abs(float(delta["delta_percentage"])),
        reverse=True,
    )[:DETAIL_LIMIT]
    return {
        "columns_compared": len(deltas),
        "columns_with_higher_null_percentage": sum(
            1 for delta in deltas if delta["delta_percentage"] > 0
        ),
        "columns_with_lower_null_percentage": sum(
            1 for delta in deltas if delta["delta_percentage"] < 0
        ),
        "max_null_percentage_delta": max(
            (abs(float(delta["delta_percentage"])) for delta in deltas),
            default=0.0,
        ),
        "column_deltas": detail_deltas,
    }


def _numeric_comparison(
    current_dataset: LoadedDataset,
    baseline_dataset: LoadedDataset,
    current_columns: list[dict[str, Any]],
    baseline_columns: list[dict[str, Any]],
) -> dict[str, Any]:
    current_numeric = _columns_with_kinds(current_columns, {"integer", "decimal"})
    baseline_numeric = _columns_with_kinds(baseline_columns, {"integer", "decimal"})
    shared = sorted(current_numeric & baseline_numeric)
    deltas = []
    for name in shared:
        current_total = _numeric_total(current_dataset, name)
        baseline_total = _numeric_total(baseline_dataset, name)
        delta = round(current_total - baseline_total, 2)
        deltas.append(
            {
                "column_name": name,
                "current_total": round(current_total, 2),
                "baseline_total": round(baseline_total, 2),
                "delta": delta,
                "delta_percentage": _percentage(delta, baseline_total),
            }
        )
    non_zero = [delta for delta in deltas if delta["delta"] != 0]
    return {
        "columns_compared": len(shared),
        "columns_with_total_delta": len(non_zero),
        "max_absolute_total_delta": max(
            (abs(float(delta["delta"])) for delta in deltas),
            default=0.0,
        ),
        "column_deltas": sorted(
            non_zero,
            key=lambda delta: abs(float(delta["delta"])),
            reverse=True,
        )[:DETAIL_LIMIT],
    }


def _date_comparison(
    current_dataset: LoadedDataset,
    baseline_dataset: LoadedDataset,
    current_columns: list[dict[str, Any]],
    baseline_columns: list[dict[str, Any]],
) -> dict[str, Any]:
    current_dates = _columns_with_kinds(current_columns, {"datetime"})
    baseline_dates = _columns_with_kinds(baseline_columns, {"datetime"})
    shared = sorted(current_dates & baseline_dates)
    deltas = []
    for name in shared:
        current_summary = _date_summary(current_dataset, name)
        baseline_summary = _date_summary(baseline_dataset, name)
        missing_delta = (
            current_summary["missing_daily_period_count"]
            - baseline_summary["missing_daily_period_count"]
        )
        range_changed = (
            current_summary["min_date"] != baseline_summary["min_date"]
            or current_summary["max_date"] != baseline_summary["max_date"]
        )
        deltas.append(
            {
                "column_name": name,
                "current_min_date": current_summary["min_date"],
                "current_max_date": current_summary["max_date"],
                "baseline_min_date": baseline_summary["min_date"],
                "baseline_max_date": baseline_summary["max_date"],
                "current_missing_daily_period_count": current_summary[
                    "missing_daily_period_count"
                ],
                "baseline_missing_daily_period_count": baseline_summary[
                    "missing_daily_period_count"
                ],
                "missing_daily_period_delta": missing_delta,
                "range_changed": range_changed,
            }
        )
    changed = [
        delta
        for delta in deltas
        if delta["range_changed"] or delta["missing_daily_period_delta"] != 0
    ]
    # Date comparison reports ranges and missing-period counts only. It does not
    # write the actual missing dates, which could reveal business activity.
    return {
        "columns_compared": len(shared),
        "columns_with_range_change": sum(
            1 for delta in deltas if delta["range_changed"]
        ),
        "columns_with_missing_daily_period_delta": sum(
            1 for delta in deltas if delta["missing_daily_period_delta"] != 0
        ),
        "daily_cadence_assumption": True,
        "column_deltas": changed[:DETAIL_LIMIT],
    }


def _category_shape_comparison(
    current_dataset: LoadedDataset,
    baseline_dataset: LoadedDataset,
    current_columns: list[dict[str, Any]],
    baseline_columns: list[dict[str, Any]],
) -> dict[str, Any]:
    current_names = _category_column_names(current_columns, current_dataset.row_count)
    baseline_names = _category_column_names(
        baseline_columns, baseline_dataset.row_count
    )
    current_by_name = {str(column.get("name")): column for column in current_columns}
    baseline_by_name = {str(column.get("name")): column for column in baseline_columns}
    shared = sorted(current_names & baseline_names)
    deltas = []
    for name in shared:
        current_unique = int(current_by_name[name].get("unique_count", 0))
        baseline_unique = int(baseline_by_name[name].get("unique_count", 0))
        current_pct = _percentage(current_unique, current_dataset.row_count)
        baseline_pct = _percentage(baseline_unique, baseline_dataset.row_count)
        unique_delta = current_unique - baseline_unique
        deltas.append(
            {
                "column_name": name,
                "current_unique_count": current_unique,
                "baseline_unique_count": baseline_unique,
                "unique_count_delta": unique_delta,
                "current_unique_percentage": current_pct,
                "baseline_unique_percentage": baseline_pct,
                "unique_percentage_delta": round(current_pct - baseline_pct, 2),
                "current_high_cardinality_signal": current_pct > 50.0,
                "baseline_high_cardinality_signal": baseline_pct > 50.0,
            }
        )
    non_zero = [
        delta
        for delta in deltas
        if delta["unique_count_delta"] != 0
        or delta["current_high_cardinality_signal"]
        != delta["baseline_high_cardinality_signal"]
    ]
    # Category comparison uses shape only. Category labels and top values are
    # deliberately excluded because they are often sensitive business values.
    return {
        "columns_compared": len(shared),
        "columns_with_unique_count_delta": sum(
            1 for delta in deltas if delta["unique_count_delta"] != 0
        ),
        "max_unique_count_delta": max(
            (abs(int(delta["unique_count_delta"])) for delta in deltas),
            default=0,
        ),
        "columns_with_high_cardinality_signal_delta": sum(
            1
            for delta in deltas
            if delta["current_high_cardinality_signal"]
            != delta["baseline_high_cardinality_signal"]
        ),
        "column_deltas": sorted(
            non_zero,
            key=lambda delta: abs(int(delta["unique_count_delta"])),
            reverse=True,
        )[:DETAIL_LIMIT],
    }


def _duplicate_comparison(
    current_dataset: LoadedDataset, baseline_dataset: LoadedDataset
) -> dict[str, Any]:
    current_candidates = _candidate_key_columns(current_dataset.column_names)
    baseline_candidates = _candidate_key_columns(baseline_dataset.column_names)
    shared = sorted(set(current_candidates) & set(baseline_candidates))
    deltas = []
    for name in shared:
        current_count = _duplicate_count(current_dataset, name)
        baseline_count = _duplicate_count(baseline_dataset, name)
        delta = current_count - baseline_count
        deltas.append(
            {
                "column_name": name,
                "current_duplicate_count": current_count,
                "baseline_duplicate_count": baseline_count,
                "duplicate_count_delta": delta,
            }
        )
    non_zero = [delta for delta in deltas if delta["duplicate_count_delta"] != 0]
    # Duplicate comparison counts repeated values but never writes which values
    # repeated. The evidence remains useful without exposing identifiers.
    return {
        "candidate_columns_compared": len(shared),
        "columns_with_higher_duplicate_count": sum(
            1 for delta in deltas if delta["duplicate_count_delta"] > 0
        ),
        "columns_with_lower_duplicate_count": sum(
            1 for delta in deltas if delta["duplicate_count_delta"] < 0
        ),
        "max_duplicate_count_delta": max(
            (abs(int(delta["duplicate_count_delta"])) for delta in deltas),
            default=0,
        ),
        "column_deltas": sorted(
            non_zero,
            key=lambda delta: abs(int(delta["duplicate_count_delta"])),
            reverse=True,
        )[:DETAIL_LIMIT],
    }


def _general_summary(
    current_profile: dict[str, Any], baseline_profile: dict[str, Any]
) -> dict[str, Any]:
    current_dataset = current_profile.get("dataset", {})
    baseline_dataset = baseline_profile.get("dataset", {})
    current_kinds = _kind_counts(current_profile)
    baseline_kinds = _kind_counts(baseline_profile)
    current_null_cells = _total_null_cells(current_profile)
    baseline_null_cells = _total_null_cells(baseline_profile)
    return {
        "row_count_delta": int(current_dataset.get("row_count", 0))
        - int(baseline_dataset.get("row_count", 0)),
        "column_count_delta": int(current_dataset.get("column_count", 0))
        - int(baseline_dataset.get("column_count", 0)),
        "total_null_cell_delta": current_null_cells - baseline_null_cells,
        "numeric_column_count_delta": _numeric_kind_count(current_kinds)
        - _numeric_kind_count(baseline_kinds),
        "datetime_column_count_delta": current_kinds.get("datetime", 0)
        - baseline_kinds.get("datetime", 0),
        "text_column_count_delta": current_kinds.get("text", 0)
        - baseline_kinds.get("text", 0),
        "duplicate_column_name_count_delta": len(
            current_dataset.get("duplicate_column_names", [])
        )
        - len(baseline_dataset.get("duplicate_column_names", [])),
        "empty_column_name_count_delta": len(
            current_dataset.get("empty_column_names", [])
        )
        - len(baseline_dataset.get("empty_column_names", [])),
    }


def _comparison_signal_count(
    current_profile: dict[str, Any], baseline_profile: dict[str, Any]
) -> int:
    schema = _schema_comparison(current_profile, baseline_profile)
    nulls = _null_comparison(current_profile, baseline_profile)
    return (
        len(schema["added_columns"])
        + len(schema["removed_columns"])
        + int(schema["inferred_kind_change_count"])
        + int(nulls["columns_with_higher_null_percentage"])
        + int(nulls["columns_with_lower_null_percentage"])
    )


def _columns_by_name(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(column.get("name")): column for column in profile.get("columns", [])}


def _shared_column_names(
    current_profile: dict[str, Any], baseline_profile: dict[str, Any]
) -> list[str]:
    return sorted(
        set(_columns_by_name(current_profile)) & set(_columns_by_name(baseline_profile))
    )


def _kind_changes(
    current_profile: dict[str, Any], baseline_profile: dict[str, Any], shared: list[str]
) -> list[dict[str, str]]:
    current_by_name = _columns_by_name(current_profile)
    baseline_by_name = _columns_by_name(baseline_profile)
    changes = []
    for name in shared:
        current_kind = str(
            current_by_name[name].get("inferred_kind", "mixed_or_unknown")
        )
        baseline_kind = str(
            baseline_by_name[name].get("inferred_kind", "mixed_or_unknown")
        )
        if current_kind != baseline_kind:
            changes.append(
                {
                    "column_name": name,
                    "current_inferred_kind": current_kind,
                    "baseline_inferred_kind": baseline_kind,
                }
            )
    return changes


def _columns_with_kinds(columns: list[dict[str, Any]], kinds: set[str]) -> set[str]:
    return {
        str(column.get("name"))
        for column in columns
        if column.get("inferred_kind") in kinds
    }


def _category_column_names(columns: list[dict[str, Any]], row_count: int) -> set[str]:
    names = set()
    for column in columns:
        name = str(column.get("name", ""))
        kind = str(column.get("inferred_kind", ""))
        unique_percentage = _percentage(int(column.get("unique_count", 0)), row_count)
        if kind in {"text", "boolean"} and unique_percentage <= 50.0:
            names.add(name)
    return names


def _numeric_total(dataset: LoadedDataset, name: str) -> float:
    series = _series(dataset, name)
    if series is None:
        return 0.0
    return float(pd.to_numeric(series, errors="coerce").sum())


def _date_summary(dataset: LoadedDataset, name: str) -> dict[str, Any]:
    series = _series(dataset, name)
    if series is None:
        return {"min_date": None, "max_date": None, "missing_daily_period_count": 0}
    dates = pd.to_datetime(series.dropna(), errors="coerce").dropna()
    if dates.empty:
        return {"min_date": None, "max_date": None, "missing_daily_period_count": 0}
    normalized = dates.dt.normalize() if hasattr(dates.dt, "normalize") else dates
    min_date = normalized.min()
    max_date = normalized.max()
    expected = pd.date_range(min_date, max_date, freq="D")
    missing_count = max(int(len(expected)) - int(normalized.nunique()), 0)
    return {
        "min_date": min_date.date().isoformat(),
        "max_date": max_date.date().isoformat(),
        "missing_daily_period_count": missing_count,
    }


def _candidate_key_columns(column_names: list[str]) -> list[str]:
    return [
        name
        for name in column_names
        if any(term in name.casefold() for term in KEY_FALLBACK_TERMS)
    ]


def _duplicate_count(dataset: LoadedDataset, name: str) -> int:
    series = _series(dataset, name)
    if series is None:
        return 0
    non_null = series.dropna()
    return max(int(non_null.shape[0]) - int(non_null.nunique(dropna=True)), 0)


def _series(dataset: LoadedDataset, name: str) -> pd.Series | None:
    if name not in dataset.dataframe.columns:
        return None
    selected = dataset.dataframe[name]
    if isinstance(selected, pd.DataFrame):
        return selected.iloc[:, 0]
    return selected


def _kind_counts(profile: dict[str, Any]) -> Counter[str]:
    return Counter(
        str(column.get("inferred_kind", "mixed_or_unknown"))
        for column in profile.get("columns", [])
    )


def _numeric_kind_count(kinds: Counter[str]) -> int:
    return kinds.get("integer", 0) + kinds.get("decimal", 0)


def _total_null_cells(profile: dict[str, Any]) -> int:
    return sum(
        int(column.get("null_count", 0)) for column in profile.get("columns", [])
    )


def _percentage(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 0.0
    return round((float(numerator) / float(denominator)) * 100, 2)
