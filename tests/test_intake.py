from __future__ import annotations

from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

from data_quality_investigation_workflow.errors import DatasetIntakeError  # noqa: E402
from data_quality_investigation_workflow.intake import load_dataset  # noqa: E402

EXAMPLE_CSV = Path("examples/customer_quality_snapshot.csv")


def test_load_dataset_loads_example_csv() -> None:
    loaded = load_dataset(EXAMPLE_CSV)

    assert loaded.file_name == "customer_quality_snapshot.csv"
    assert loaded.file_extension == ".csv"
    assert loaded.sheet_name is None
    assert loaded.row_count == 12
    assert loaded.column_count == 6
    assert loaded.column_names == [
        "customer_id",
        "email",
        "signup_date",
        "status",
        "region",
        "lifetime_value",
    ]


def test_load_dataset_loads_excel_with_sheet(tmp_path: Path) -> None:
    workbook_path = tmp_path / "customers.xlsx"
    dataframe = pd.DataFrame({"customer_id": ["CUST-001", "CUST-002"], "value": [1, 2]})
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name="Customers", index=False)

    loaded = load_dataset(workbook_path, sheet="Customers")

    assert loaded.sheet_name == "Customers"
    assert loaded.row_count == 2
    assert loaded.column_count == 2


def test_load_dataset_requires_sheet_for_multi_sheet_excel(tmp_path: Path) -> None:
    workbook_path = tmp_path / "customers.xlsx"
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        pd.DataFrame({"id": [1]}).to_excel(writer, sheet_name="Customers", index=False)
        pd.DataFrame({"id": [2]}).to_excel(writer, sheet_name="Archive", index=False)

    with pytest.raises(DatasetIntakeError, match="multiple sheets"):
        load_dataset(workbook_path)


def test_load_dataset_rejects_sheet_for_csv() -> None:
    with pytest.raises(DatasetIntakeError, match="only be used with Excel"):
        load_dataset(EXAMPLE_CSV, sheet="Sheet1")


def test_load_dataset_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(DatasetIntakeError, match="does not exist"):
        load_dataset(tmp_path / "missing.csv")


def test_load_dataset_rejects_unsupported_extension(tmp_path: Path) -> None:
    unsupported = tmp_path / "customers.json"
    unsupported.write_text("[]", encoding="utf-8")

    with pytest.raises(DatasetIntakeError, match="Unsupported input file extension"):
        load_dataset(unsupported)
