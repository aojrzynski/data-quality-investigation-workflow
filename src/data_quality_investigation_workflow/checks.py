"""Deterministic aggregate issue checks.

Checks record evidence-supported signals for review. They avoid raw records and
keep route-specific assumptions, such as daily date cadence, visible.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd
from pandas.api.types import is_numeric_dtype

from data_quality_investigation_workflow.intake import LoadedDataset

KEY_FALLBACK_TERMS = ["id", "key", "code", "number", "reference", "ref"]
DATE_FALLBACK_TERMS = ["date", "time", "timestamp", "period", "day", "month", "year"]
CATEGORY_FALLBACK_TERMS = ["status", "category", "type", "segment", "region"]

EXECUTED_BY_ROUTE = {
    "duplicate_key_investigation": {"duplicate_key_summary", "key_null_summary"},
    "null_increase_investigation": {"current_null_summary"},
    "date_gap_investigation": {"date_range_summary", "date_gap_summary"},
    "total_change_investigation": {"numeric_total_summary", "row_count_summary"},
    "schema_change_investigation": {"current_schema_summary"},
    "category_shift_investigation": {"categorical_shape_summary"},
    "general_investigation": {"general_profile_signal_summary"},
}

PLANNED_TO_EXECUTED = {
    "planned_duplicate_key_summary": "duplicate_key_summary",
    "planned_key_null_summary": "key_null_summary",
    "planned_current_null_summary": "current_null_summary",
    "planned_date_range_summary": "date_range_summary",
    "planned_missing_period_detection": "date_gap_summary",
    "planned_numeric_total_summary": "numeric_total_summary",
    "planned_current_schema_summary": "current_schema_summary",
    "planned_category_distribution_summary": "categorical_shape_summary",
    "planned_general_profile_review": "general_profile_signal_summary",
}


def run_route_checks(
    loaded_dataset: LoadedDataset,
    dataset_profile: dict[str, Any],
    investigation_plan: dict[str, Any],
    *,
    baseline_comparison: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run deterministic current-dataset and optional baseline checks."""
    route_name = str(investigation_plan.get("route", {}).get("route_name", ""))
    if route_name == "missing_issue_statement":
        return {
            "evidence_items": [],
            "checks_not_run": _checks_not_run(investigation_plan, set()),
            "checks_executed_count": 0,
            "reason": "No issue statement was supplied, so route-specific evidence checks were not executed.",
        }

    builders = {
        "duplicate_key_investigation": _duplicate_key_items,
        "null_increase_investigation": _null_items,
        "date_gap_investigation": _date_items,
        "total_change_investigation": _total_items,
        "schema_change_investigation": _schema_items,
        "category_shift_investigation": _category_items,
        "general_investigation": _general_items,
    }
    evidence_items = builders.get(route_name, _general_items)(
        loaded_dataset, dataset_profile, investigation_plan
    )
    if baseline_comparison is not None:
        evidence_items.extend(_baseline_items(route_name, baseline_comparison))
    executed = {str(item["check_id"]) for item in evidence_items if item.get("status") == "executed"}
    return {
        "evidence_items": _with_ids(evidence_items),
        "checks_not_run": _checks_not_run(investigation_plan, executed),
        "checks_executed_count": len(executed),
    }


def _duplicate_key_items(
    loaded_dataset: LoadedDataset, dataset_profile: dict[str, Any], plan: dict[str, Any]
) -> list[dict[str, Any]]:
    columns = _candidate_names(plan) or _name_matches(loaded_dataset.column_names, KEY_FALLBACK_TERMS)
    row_count = loaded_dataset.row_count
    duplicate_counts: list[int] = []
    null_counts: list[int] = []
    duplicate_columns: list[str] = []
    null_columns: list[str] = []
    for name in columns:
        series = _series(loaded_dataset, name)
        if series is None:
            continue
        non_null = series.dropna()
        duplicate_count = max(int(non_null.shape[0]) - int(non_null.nunique(dropna=True)), 0)
        null_count = int(series.isna().sum())
        duplicate_counts.append(duplicate_count)
        null_counts.append(null_count)
        if duplicate_count > 0:
            duplicate_columns.append(name)
        if null_count > 0:
            null_columns.append(name)
    max_dup = max(duplicate_counts, default=0)
    max_null = max(null_counts, default=0)
    return [
        {
            "check_id": "duplicate_key_summary",
            "check_name": "Duplicate key summary",
            "status": "executed",
            "signal": "present" if duplicate_columns else "absent",
            "signal_strength": "medium" if duplicate_columns else "low",
            "summary": "At least one candidate key column has duplicate non-null values." if duplicate_columns else "No duplicate non-null values were detected in candidate key columns.",
            "related_columns": duplicate_columns,
            "metrics": {
                "candidate_column_count": len(columns),
                "columns_with_duplicate_non_null_values": len(duplicate_columns),
                "max_duplicate_value_count": max_dup,
                "max_duplicate_value_percentage": _percentage(max_dup, row_count),
            },
            "limitations": _standard_limitations("Duplicate values are counted as aggregates only."),
        },
        {
            "check_id": "key_null_summary",
            "check_name": "Key null summary",
            "status": "executed",
            "signal": "present" if null_columns else "absent",
            "signal_strength": "medium" if null_columns else "low",
            "summary": "At least one candidate key column contains null values." if null_columns else "No null values were detected in candidate key columns.",
            "related_columns": null_columns,
            "metrics": {
                "candidate_column_count": len(columns),
                "columns_with_null_values": len(null_columns),
                "max_null_count": max_null,
                "max_null_percentage": _percentage(max_null, row_count),
            },
            "limitations": _standard_limitations("Null values are counted as aggregates only."),
        },
    ]


def _null_items(loaded_dataset: LoadedDataset, _profile: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    columns = _candidate_names(plan) or loaded_dataset.column_names
    row_count = loaded_dataset.row_count
    null_counts = [_null_count(loaded_dataset, name) for name in columns]
    max_null = max(null_counts, default=0)
    total_nulls = sum(null_counts)
    columns_with_nulls = sum(1 for count in null_counts if count > 0)
    return [{
        "check_id": "current_null_summary",
        "check_name": "Current null summary",
        "status": "executed",
        "signal": "present" if total_nulls else "absent",
        "signal_strength": "medium" if total_nulls else "low",
        "summary": "The current dataset contains null values in assessed columns. A baseline is required for current-vs-baseline increase evidence." if total_nulls else "No null values were detected in assessed columns. A baseline is required for current-vs-baseline increase evidence.",
        "related_columns": [name for name in columns if _null_count(loaded_dataset, name) > 0],
        "metrics": {
            "assessed_column_count": len(columns),
            "columns_with_nulls": columns_with_nulls,
            "max_null_count": max_null,
            "max_null_percentage": _percentage(max_null, row_count),
            "total_null_cells": total_nulls,
            "total_cells_assessed": row_count * len(columns),
        },
        "limitations": _standard_limitations("No baseline comparison was supplied for this current-dataset-only evidence item."),
    }]


def _date_items(loaded_dataset: LoadedDataset, profile: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    columns = _candidate_names(plan) or _profile_kind_names(profile, {"datetime"}) or _name_matches(loaded_dataset.column_names, DATE_FALLBACK_TERMS)
    parsed = []
    for name in columns:
        series = _series(loaded_dataset, name)
        if series is None:
            continue
        dates = pd.to_datetime(series.dropna(), errors="coerce").dropna()
        if not dates.empty:
            parsed.append((name, dates.dt.normalize() if hasattr(dates.dt, "normalize") else dates))
    min_dates = [dates.min() for _name, dates in parsed]
    max_dates = [dates.max() for _name, dates in parsed]
    observed_unique = sum(int(dates.nunique()) for _name, dates in parsed)
    missing_total = 0
    expected_total = 0
    for _name, dates in parsed:
        min_date = dates.min()
        max_date = dates.max()
        expected = pd.date_range(min_date, max_date, freq="D")
        expected_total += int(len(expected))
        missing_total += max(int(len(expected)) - int(dates.nunique()), 0)
    min_date_text = min(min_dates).date().isoformat() if min_dates else None
    max_date_text = max(max_dates).date().isoformat() if max_dates else None
    metrics = {
        "assessed_date_column_count": len(columns),
        "parsed_date_column_count": len(parsed),
        "min_date": min_date_text,
        "max_date": max_date_text,
        "observed_unique_date_count": observed_unique,
        "expected_daily_date_count": expected_total,
        "missing_daily_period_count": missing_total,
    }
    return [
        {
            "check_id": "date_range_summary",
            "check_name": "Date range summary",
            "status": "executed",
            "signal": "present" if parsed else "unclear",
            "signal_strength": "low",
            "summary": "Date ranges were summarized for parsed candidate date columns." if parsed else "No parseable candidate date columns were available for date range evidence.",
            "related_columns": [name for name, _dates in parsed],
            "metrics": metrics,
            "limitations": _standard_limitations("Dates are recorded only as aggregate range evidence."),
        },
        {
            "check_id": "date_gap_summary",
            "check_name": "Date gap summary",
            "status": "executed",
            "signal": "present" if missing_total else "absent",
            "signal_strength": "medium" if missing_total else "low",
            "summary": "A daily-cadence aggregate gap signal is present. Missing date lists are not written." if missing_total else "No daily-cadence aggregate gap was detected in parsed candidate date columns.",
            "related_columns": [name for name, _dates in parsed],
            "metrics": metrics,
            "limitations": _standard_limitations("Daily cadence is assumed only for planning evidence."),
        },
    ]


def _total_items(loaded_dataset: LoadedDataset, profile: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    columns = [name for name in (_candidate_names(plan) or _profile_kind_names(profile, {"integer", "decimal"})) if _is_numeric(loaded_dataset, name)]
    totals = []
    for name in columns:
        series = _series(loaded_dataset, name)
        if series is not None:
            totals.append(float(pd.to_numeric(series, errors="coerce").sum()))
    metrics = {
        "assessed_numeric_column_count": len(columns),
        "numeric_columns_with_totals": len(totals),
        "min_column_total": round(min(totals), 2) if totals else None,
        "max_column_total": round(max(totals), 2) if totals else None,
    }
    return [
        {
            "check_id": "numeric_total_summary",
            "check_name": "Numeric total summary",
            "status": "executed",
            "signal": "present" if totals else "unclear",
            "signal_strength": "low",
            "summary": "Current numeric totals were summarized as aggregate signals. A baseline is required for current-vs-baseline total comparison evidence.",
            "related_columns": columns[:5],
            "metrics": metrics,
            "limitations": _standard_limitations("No baseline comparison was supplied for this current-dataset-only evidence item."),
        },
        {
            "check_id": "row_count_summary",
            "check_name": "Row count summary",
            "status": "executed",
            "signal": "present",
            "signal_strength": "low",
            "summary": "Current row count was recorded as an aggregate signal. A baseline is required for current-vs-baseline row count comparison evidence.",
            "related_columns": [],
            "metrics": {"row_count": loaded_dataset.row_count},
            "limitations": _standard_limitations("No baseline comparison was supplied for this current-dataset-only evidence item."),
        },
    ]


def _schema_items(_loaded_dataset: LoadedDataset, profile: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    dataset = profile.get("dataset", {})
    kinds = Counter(str(column.get("inferred_kind", "mixed_or_unknown")) for column in profile.get("columns", []))
    return [{
        "check_id": "current_schema_summary",
        "check_name": "Current schema summary",
        "status": "executed",
        "signal": "present",
        "signal_strength": "low",
        "summary": "Current schema metadata was summarized. A baseline is required for current-vs-baseline schema comparison evidence.",
        "related_columns": _candidate_names(plan),
        "metrics": {
            "column_count": int(dataset.get("column_count", 0)),
            "duplicate_column_name_count": len(dataset.get("duplicate_column_names", [])),
            "empty_column_name_count": len(dataset.get("empty_column_names", [])),
            "inferred_kind_counts": dict(sorted(kinds.items())),
            "candidate_column_count": len(_candidate_names(plan)),
        },
        "limitations": _standard_limitations("No baseline comparison was supplied for this current-dataset-only evidence item."),
    }]


def _category_items(loaded_dataset: LoadedDataset, profile: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    columns = _candidate_names(plan) or _likely_category_names(profile, loaded_dataset.row_count)
    unique_counts = []
    for name in columns:
        series = _series(loaded_dataset, name)
        if series is not None:
            unique_counts.append(int(series.nunique(dropna=True)))
    max_unique = max(unique_counts, default=0)
    max_unique_percentage = _percentage(max_unique, loaded_dataset.row_count)
    return [{
        "check_id": "categorical_shape_summary",
        "check_name": "Categorical shape summary",
        "status": "executed",
        "signal": "present" if columns else "unclear",
        "signal_strength": "low",
        "summary": "Current categorical shape was summarized without category labels. A baseline is required for current-vs-baseline category shape evidence.",
        "related_columns": columns,
        "metrics": {
            "assessed_categorical_column_count": len(columns),
            "columns_assessed_count": len(columns),
            "max_unique_count": max_unique,
            "max_unique_percentage": max_unique_percentage,
            "any_candidate_categorical_column_has_high_cardinality": max_unique_percentage > 50.0,
        },
        "limitations": _standard_limitations("Category labels and distributions are not written."),
    }]


def _general_items(_loaded_dataset: LoadedDataset, profile: dict[str, Any], _plan: dict[str, Any]) -> list[dict[str, Any]]:
    dataset = profile.get("dataset", {})
    columns = profile.get("columns", [])
    kinds = Counter(str(column.get("inferred_kind", "mixed_or_unknown")) for column in columns)
    total_nulls = sum(int(column.get("null_count", 0)) for column in columns)
    columns_with_nulls = sum(1 for column in columns if int(column.get("null_count", 0)) > 0)
    return [{
        "check_id": "general_profile_signal_summary",
        "check_name": "General profile signal summary",
        "status": "executed",
        "signal": "present",
        "signal_strength": "low",
        "summary": "Safe aggregate profile signals were summarized. This does not prove the reported issue exists.",
        "related_columns": [],
        "metrics": {
            "row_count": int(dataset.get("row_count", 0)),
            "column_count": int(dataset.get("column_count", 0)),
            "total_null_cells": total_nulls,
            "columns_with_nulls": columns_with_nulls,
            "numeric_column_count": kinds.get("integer", 0) + kinds.get("decimal", 0),
            "datetime_column_count": kinds.get("datetime", 0),
            "text_column_count": kinds.get("text", 0),
            "duplicate_column_name_count": len(dataset.get("duplicate_column_names", [])),
            "empty_column_name_count": len(dataset.get("empty_column_names", [])),
        },
        "limitations": _standard_limitations("This check records profile metadata only."),
    }]


def _baseline_items(route_name: str, comparison: dict[str, Any]) -> list[dict[str, Any]]:
    builders = {
        "duplicate_key_investigation": _baseline_duplicate_items,
        "null_increase_investigation": _baseline_null_items,
        "date_gap_investigation": _baseline_date_items,
        "total_change_investigation": _baseline_total_items,
        "schema_change_investigation": _baseline_schema_items,
        "category_shift_investigation": _baseline_category_items,
        "general_investigation": _baseline_general_items,
    }
    return builders.get(route_name, _baseline_general_items)(comparison)


def _baseline_duplicate_items(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    duplicate = comparison.get("duplicate_comparison", {})
    return [{
        "check_id": "baseline_duplicate_comparison",
        "check_name": "Baseline duplicate comparison",
        "status": "executed",
        "signal": "present" if duplicate.get("columns_with_higher_duplicate_count", 0) else "absent",
        "signal_strength": "medium" if duplicate.get("columns_with_higher_duplicate_count", 0) else "low",
        "summary": "Duplicate aggregate comparison signal present; current candidate-key duplicate aggregates are higher than baseline for at least one column." if duplicate.get("columns_with_higher_duplicate_count", 0) else "Duplicate aggregate comparison signal was recorded; current candidate-key duplicate aggregates are not higher than baseline.",
        "related_columns": _delta_columns(duplicate),
        "metrics": {
            "candidate_columns_compared": int(duplicate.get("candidate_columns_compared", 0)),
            "columns_with_higher_duplicate_count": int(duplicate.get("columns_with_higher_duplicate_count", 0)),
            "max_duplicate_count_delta": int(duplicate.get("max_duplicate_count_delta", 0)),
            "column_deltas": duplicate.get("column_deltas", []),
        },
        "limitations": _baseline_limitations("Duplicated values are not written."),
    }]


def _baseline_null_items(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    nulls = comparison.get("null_comparison", {})
    return [{
        "check_id": "baseline_null_comparison",
        "check_name": "Baseline null comparison",
        "status": "executed",
        "signal": "present" if nulls.get("columns_with_higher_null_percentage", 0) else "absent",
        "signal_strength": "medium" if nulls.get("columns_with_higher_null_percentage", 0) else "low",
        "summary": "Null aggregate comparison signal present; current null percentage is higher than baseline for at least one assessed column." if nulls.get("columns_with_higher_null_percentage", 0) else "Null aggregate comparison signal was recorded; current null percentages are not higher than baseline for assessed columns.",
        "related_columns": _delta_columns(nulls),
        "metrics": {
            "columns_compared": int(nulls.get("columns_compared", 0)),
            "columns_with_higher_null_percentage": int(nulls.get("columns_with_higher_null_percentage", 0)),
            "columns_with_lower_null_percentage": int(nulls.get("columns_with_lower_null_percentage", 0)),
            "max_null_percentage_delta": float(nulls.get("max_null_percentage_delta", 0.0)),
            "column_deltas": nulls.get("column_deltas", []),
        },
        "limitations": _baseline_limitations("This comparison does not claim final issue confirmation."),
    }]


def _baseline_date_items(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    dates = comparison.get("date_comparison", {})
    return [{
        "check_id": "baseline_date_comparison",
        "check_name": "Baseline date comparison",
        "status": "executed",
        "signal": "present" if dates.get("columns_with_missing_daily_period_delta", 0) else "absent",
        "signal_strength": "medium" if dates.get("columns_with_missing_daily_period_delta", 0) else "low",
        "summary": "Date aggregate comparison signal was recorded using an explicit daily-cadence assumption.",
        "related_columns": _delta_columns(dates),
        "metrics": {
            "columns_compared": int(dates.get("columns_compared", 0)),
            "columns_with_range_change": int(dates.get("columns_with_range_change", 0)),
            "columns_with_missing_daily_period_delta": int(dates.get("columns_with_missing_daily_period_delta", 0)),
            "daily_cadence_assumption": bool(dates.get("daily_cadence_assumption", True)),
            "column_deltas": dates.get("column_deltas", []),
        },
        "limitations": _baseline_limitations("Daily cadence is assumed; missing date lists are not written."),
    }]


def _baseline_total_items(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    numeric = comparison.get("numeric_comparison", {})
    rows = comparison.get("row_count_comparison", {})
    return [{
        "check_id": "baseline_total_comparison",
        "check_name": "Baseline total and row-count comparison",
        "status": "executed",
        "signal": "present" if numeric.get("columns_with_total_delta", 0) or rows.get("delta", 0) else "absent",
        "signal_strength": "medium" if numeric.get("columns_with_total_delta", 0) or rows.get("delta", 0) else "low",
        "summary": "Numeric and row-count aggregate comparison signal was recorded; this is not a final finding that totals changed.",
        "related_columns": _delta_columns(numeric),
        "metrics": {
            "current_row_count": int(rows.get("current_row_count", 0)),
            "baseline_row_count": int(rows.get("baseline_row_count", 0)),
            "row_count_delta": int(rows.get("delta", 0)),
            "numeric_columns_compared": int(numeric.get("columns_compared", 0)),
            "columns_with_total_delta": int(numeric.get("columns_with_total_delta", 0)),
            "max_absolute_total_delta": float(numeric.get("max_absolute_total_delta", 0.0)),
            "column_deltas": numeric.get("column_deltas", []),
        },
        "limitations": _baseline_limitations("Numeric totals are aggregate sums only."),
    }]


def _baseline_schema_items(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    schema = comparison.get("schema_comparison", {})
    return [{
        "check_id": "baseline_schema_comparison",
        "check_name": "Baseline schema comparison",
        "status": "executed",
        "signal": "present" if schema.get("added_columns") or schema.get("removed_columns") or schema.get("inferred_kind_change_count", 0) else "absent",
        "signal_strength": "medium" if schema.get("added_columns") or schema.get("removed_columns") else "low",
        "summary": "Schema aggregate comparison signal was recorded using column names and inferred-kind metadata only.",
        "related_columns": list(schema.get("added_columns", [])) + list(schema.get("removed_columns", [])),
        "metrics": {
            "current_column_count": int(schema.get("current_column_count", 0)),
            "baseline_column_count": int(schema.get("baseline_column_count", 0)),
            "added_columns": schema.get("added_columns", []),
            "removed_columns": schema.get("removed_columns", []),
            "shared_column_count": int(schema.get("shared_column_count", 0)),
            "inferred_kind_change_count": int(schema.get("inferred_kind_change_count", 0)),
            "inferred_kind_changes": schema.get("inferred_kind_changes", []),
        },
        "limitations": _baseline_limitations("Schema comparison does not claim root cause."),
    }]


def _baseline_category_items(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    category = comparison.get("category_shape_comparison", {})
    return [{
        "check_id": "baseline_category_shape_comparison",
        "check_name": "Baseline category shape comparison",
        "status": "executed",
        "signal": "present" if category.get("columns_with_unique_count_delta", 0) else "absent",
        "signal_strength": "medium" if category.get("columns_with_unique_count_delta", 0) else "low",
        "summary": "Category shape aggregate comparison signal was recorded without category labels or distributions.",
        "related_columns": _delta_columns(category),
        "metrics": {
            "columns_compared": int(category.get("columns_compared", 0)),
            "columns_with_unique_count_delta": int(category.get("columns_with_unique_count_delta", 0)),
            "max_unique_count_delta": int(category.get("max_unique_count_delta", 0)),
            "columns_with_high_cardinality_signal_delta": int(category.get("columns_with_high_cardinality_signal_delta", 0)),
            "column_deltas": category.get("column_deltas", []),
        },
        "limitations": _baseline_limitations("Category labels and full category distributions are not written."),
    }]


def _baseline_general_items(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    general = comparison.get("general_summary", {})
    return [{
        "check_id": "baseline_general_summary",
        "check_name": "Baseline general comparison summary",
        "status": "executed",
        "signal": "present",
        "signal_strength": "low",
        "summary": "General current vs baseline aggregate comparison signal was recorded and requires human review.",
        "related_columns": [],
        "metrics": general,
        "limitations": _baseline_limitations("General comparison is not route-specific final evidence."),
    }]


def _delta_columns(section: dict[str, Any]) -> list[str]:
    return [str(delta.get("column_name")) for delta in section.get("column_deltas", []) if delta.get("column_name")]


def _baseline_limitations(extra: str) -> list[str]:
    return [
        extra,
        "Baseline comparison signal is not final evidence of root cause.",
        "Human review remains required.",
        "Raw rows, sampled records, value lists, category labels, and raw failing records are not written to the artifact.",
    ]


def _checks_not_run(plan: dict[str, Any], executed: set[str]) -> list[dict[str, str]]:
    not_run = []
    for check in plan.get("planned_checks", []):
        planned_id = str(check.get("check_id", ""))
        executed_id = PLANNED_TO_EXECUTED.get(planned_id)
        if executed_id in executed:
            continue
        if check.get("requires_baseline"):
            reason = "Baseline comparison was not available or not route-executable in this run."
        else:
            reason = "This planned review requires later evidence interpretation and is not implemented in the current run."
        not_run.append({"check_id": planned_id, "reason": reason})
    return not_run


def _candidate_names(plan: dict[str, Any]) -> list[str]:
    return [str(column.get("name")) for column in plan.get("dataset_context", {}).get("candidate_columns", []) if column.get("name")]


def _name_matches(names: list[str], terms: list[str]) -> list[str]:
    return [name for name in names if any(term in name.casefold() for term in terms)]


def _profile_kind_names(profile: dict[str, Any], kinds: set[str]) -> list[str]:
    return [str(column.get("name")) for column in profile.get("columns", []) if str(column.get("inferred_kind")) in kinds]


def _likely_category_names(profile: dict[str, Any], row_count: int) -> list[str]:
    names = []
    for column in profile.get("columns", []):
        name = str(column.get("name", ""))
        kind = str(column.get("inferred_kind", ""))
        unique_count = int(column.get("unique_count", 0))
        if any(term in name.casefold() for term in CATEGORY_FALLBACK_TERMS) or (kind == "text" and _percentage(unique_count, row_count) <= 50.0):
            names.append(name)
    return names


def _series(loaded_dataset: LoadedDataset, name: str) -> pd.Series | None:
    if name not in loaded_dataset.dataframe.columns:
        return None
    selected = loaded_dataset.dataframe[name]
    if isinstance(selected, pd.DataFrame):
        return selected.iloc[:, 0]
    return selected


def _null_count(loaded_dataset: LoadedDataset, name: str) -> int:
    series = _series(loaded_dataset, name)
    return int(series.isna().sum()) if series is not None else 0


def _is_numeric(loaded_dataset: LoadedDataset, name: str) -> bool:
    series = _series(loaded_dataset, name)
    return bool(series is not None and is_numeric_dtype(series))


def _percentage(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 0.0
    return round((float(numerator) / float(denominator)) * 100, 2)


def _standard_limitations(extra: str) -> list[str]:
    return [
        extra,
        "Raw rows, sampled records, value lists, and raw failing records are not written to the artifact.",
        "This check does not identify root cause.",
        "Human review remains required before interpreting this signal.",
    ]


def _with_ids(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"evidence_id": f"ev-{index:03d}", **item} for index, item in enumerate(items, start=1)]
