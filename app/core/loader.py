"""Generic Excel loading helpers."""

from collections.abc import Mapping, Sequence
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd
import streamlit as st


class DataLoadError(Exception):
    """Raised when workbook data cannot be loaded."""


def load_excel_sheets(
    file_source: str | Path | bytes | BinaryIO,
    sheet_mapping: Mapping[str, str] | Sequence[str],
) -> dict[str, pd.DataFrame]:
    """Load one or more named sheets from an Excel source."""

    excel_source = _normalize_excel_source(file_source)
    mapping = _normalize_sheet_mapping(sheet_mapping)

    try:
        excel_file = pd.ExcelFile(excel_source)
        return {
            alias: excel_file.parse(sheet_name)
            for alias, sheet_name in mapping.items()
        }
    except Exception as exc:
        raise DataLoadError(f"读取 Excel 数据失败: {exc}") from exc


@st.cache_data(show_spinner=False)
def load_shared_workbook(
    file_bytes: bytes,
    source_name: str,
    source_token: str,
) -> dict[str, pd.DataFrame]:
    """Load and cache all sheets from the shared workbook."""

    _ = source_name
    _ = source_token

    try:
        excel_file = pd.ExcelFile(BytesIO(file_bytes))
        return {
            sheet_name: excel_file.parse(sheet_name)
            for sheet_name in excel_file.sheet_names
        }
    except Exception as exc:
        raise DataLoadError(f"读取共享 Excel 数据失败: {exc}") from exc


def select_required_sheets(
    workbook: dict[str, pd.DataFrame],
    sheet_mapping: Mapping[str, str] | Sequence[str],
) -> dict[str, pd.DataFrame]:
    """Select required sheets from a preloaded workbook by alias mapping."""

    mapping = _normalize_sheet_mapping(sheet_mapping)
    missing_sheets = [
        sheet_name for sheet_name in mapping.values() if sheet_name not in workbook
    ]
    if missing_sheets:
        raise DataLoadError(f"缺少必需的工作表: {', '.join(missing_sheets)}")

    return {
        alias: workbook[sheet_name].copy()
        for alias, sheet_name in mapping.items()
    }


def _normalize_excel_source(file_source: str | Path | bytes | BinaryIO):
    """Normalize a path, upload, or stream into a pandas-readable source."""

    if isinstance(file_source, (str, Path)):
        path = Path(file_source)
        if not path.exists():
            raise DataLoadError(f"找不到文件 `{path.name}`，请确认文件名和路径。")
        return path

    if isinstance(file_source, bytes):
        return BytesIO(file_source)

    if hasattr(file_source, "seek"):
        file_source.seek(0)
        return file_source

    raise DataLoadError("不支持的数据源类型，请上传 Excel 文件或传入本地路径。")


def _normalize_sheet_mapping(
    sheet_mapping: Mapping[str, str] | Sequence[str],
) -> dict[str, str]:
    """Normalize sheet definitions into an alias-to-sheet-name mapping."""

    if isinstance(sheet_mapping, Mapping):
        return dict(sheet_mapping)

    return {sheet_name: sheet_name for sheet_name in sheet_mapping}
