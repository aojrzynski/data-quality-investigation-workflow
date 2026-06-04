"""Local CSV and Excel intake helpers.

The workflow is local-first: this module reads user-supplied files and returns
metadata needed by aggregate profiling without adding connectors.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from data_quality_investigation_workflow.errors import DatasetIntakeError

if TYPE_CHECKING:
    import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xlsm"}
EXCEL_EXTENSIONS = {".xlsx", ".xlsm"}


@dataclass(frozen=True)
class LoadedDataset:
    """In-memory representation of a loaded local dataset."""

    path: Path
    file_name: str
    file_extension: str
    sheet_name: str | None
    dataframe: pd.DataFrame
    row_count: int
    column_count: int
    column_names: list[str]


def load_dataset(path: Path, sheet: str | None = None) -> LoadedDataset:
    """Load a supported local dataset for aggregate profiling.

    CSV, XLSX, and XLSM files are supported. Raw rows stay in memory for the
    profiler and are not written by this module.
    """
    input_path = Path(path)
    extension = input_path.suffix.lower()

    if not input_path.exists():
        raise DatasetIntakeError(f"Input file does not exist: {input_path.as_posix()}")

    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise DatasetIntakeError(
            f"Unsupported input file extension '{extension or '<none>'}'. "
            f"Supported extensions are: {supported}."
        )

    if extension == ".csv":
        if sheet is not None:
            raise DatasetIntakeError("--sheet can only be used with Excel files, not CSV input.")
        import pandas as pd

        dataframe = pd.read_csv(input_path)
        sheet_name = None
    else:
        dataframe, sheet_name = _load_excel(input_path, sheet)

    return LoadedDataset(
        path=input_path,
        file_name=input_path.name,
        file_extension=extension,
        sheet_name=sheet_name,
        dataframe=dataframe,
        row_count=int(dataframe.shape[0]),
        column_count=int(dataframe.shape[1]),
        column_names=[str(column) for column in dataframe.columns],
    )


def _load_excel(path: Path, sheet: str | None) -> tuple[pd.DataFrame, str]:
    """Load an Excel worksheet, requiring --sheet for multi-sheet workbooks."""
    import pandas as pd

    try:
        excel_file = pd.ExcelFile(path, engine="openpyxl")
    except ImportError as error:
        if "openpyxl" in str(error):
            raise DatasetIntakeError(
                "Missing required dependency 'openpyxl'. Install the package with "
                "runtime dependencies before profiling Excel files."
            ) from error
        raise
    sheet_names = [str(name) for name in excel_file.sheet_names]

    if sheet is None:
        if len(sheet_names) > 1:
            available_sheets = ", ".join(sheet_names)
            raise DatasetIntakeError(
                "Excel workbook contains multiple sheets. Provide --sheet to choose one. "
                f"Available sheets: {available_sheets}."
            )
        sheet_name = sheet_names[0]
    else:
        if sheet not in sheet_names:
            available_sheets = ", ".join(sheet_names)
            raise DatasetIntakeError(
                f"Excel sheet '{sheet}' was not found. Available sheets: {available_sheets}."
            )
        sheet_name = sheet

    dataframe = pd.read_excel(excel_file, sheet_name=sheet_name, engine="openpyxl")
    return dataframe, sheet_name
