"""通用 Excel 加载能力。"""

from collections.abc import Mapping, Sequence
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd
import streamlit as st


class DataLoadError(Exception):
    """工作簿数据加载失败时抛出的异常。"""


def load_excel_sheets(
    file_source: str | Path | bytes | BinaryIO,
    sheet_mapping: Mapping[str, str] | Sequence[str],
) -> dict[str, pd.DataFrame]:
    """从 Excel 数据源中读取一个或多个指定工作表。"""

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
    """加载并缓存共享工作簿中的全部工作表。"""

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
    """按别名映射从已加载工作簿中选出当前看板需要的工作表。"""

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
    """把路径、上传文件或流对象归一化为 pandas 可读取的数据源。"""

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
    """把工作表定义归一化为“别名 -> 工作表名”的映射。"""

    if isinstance(sheet_mapping, Mapping):
        return dict(sheet_mapping)

    return {sheet_name: sheet_name for sheet_name in sheet_mapping}
