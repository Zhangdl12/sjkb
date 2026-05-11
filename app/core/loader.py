"""
通用 Excel 加载能力。

提供两个层级的数据加载：

1. load_shared_workbook() — 从共享数据源加载整个工作簿
   - 用 @st.cache_data 缓存，键为 (file_bytes, source_name, source_token)
   - source_token 是文件字节的 md5 哈希，保证相同文件只解析一次
   - 是看板页面的主要入口

2. select_required_sheets() — 从已加载的工作簿中按别名提取指定工作表
   - 接收 load_shared_workbook 的返回值
   - 按 {别名: 工作表名} 映射提取，验证必需工作表是否存在
   - 返回 {别名: DataFrame} 供后续加工

辅助函数：
  load_excel_sheets() — 独立的 Excel 读取函数（备用，不依赖 session_state）
"""
from collections.abc import Mapping, Sequence
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd
import streamlit as st


class DataLoadError(Exception):
    """工作簿数据加载失败时抛出的异常。

    在 run_dashboard_page 中被捕获并显示为 st.error。
    """


def load_excel_sheets(
    file_source: str | Path | bytes | BinaryIO,
    sheet_mapping: Mapping[str, str] | Sequence[str],
) -> dict[str, pd.DataFrame]:
    """从 Excel 数据源中读取一个或多个指定工作表（独立函数，不依赖缓存）。

    Args:
        file_source: Excel 文件来源，可以是文件路径、字节数据或文件对象
        sheet_mapping: 工作表定义
            - 字典 {"别名": "工作表名"} → 返回 {别名: DataFrame}
            - 列表 ["工作表名"] → 返回 {工作表名: DataFrame}

    Returns:
        {别名或工作表名: DataFrame} 字典
    """
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
    """加载并缓存共享工作簿中的全部工作表。

    这是看板页面的主要入口。结果被 Streamlit 缓存，只要 source_token
    （文件字节的 md5）不变，重复调用不会重新解析 Excel。

    Args:
        file_bytes: Excel 文件的原始字节（来自 session_state）
        source_name: 文件名（仅用于缓存标识，不参与实际读取）
        source_token: 文件 md5 哈希（用作缓存键，保证文件内容变化时自动刷新）

    Returns:
        {工作表名: DataFrame} 字典，包含 Excel 中的所有工作表
    """
    _ = source_name  # 参数保留用于缓存键，实际不参与读取逻辑
    _ = source_token

    try:
        # BytesIO 将字节数据包装成文件对象，供 pd.ExcelFile 读取
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
    """按别名映射从已加载工作簿中选出当前看板需要的工作表。

    验证必需的工作表是否存在，不存在则抛出 DataLoadError。

    Args:
        workbook: load_shared_workbook 的返回值
        sheet_mapping: {别名: 工作表名} 或 [工作表名]

    Returns:
        {别名: DataFrame} 字典，DataFrame 是 .copy() 后的副本
    """
    mapping = _normalize_sheet_mapping(sheet_mapping)
    missing_sheets = [
        sheet_name for sheet_name in mapping.values() if sheet_name not in workbook
    ]
    if missing_sheets:
        raise DataLoadError(f"缺少必需的工作表: {', '.join(missing_sheets)}")

    return {
        alias: workbook[sheet_name].copy()  # .copy() 防止后续操作影响缓存中的原表
        for alias, sheet_name in mapping.items()
    }


def _normalize_excel_source(file_source: str | Path | bytes | BinaryIO):
    """内部函数：把路径、上传文件或流对象归一化为 pandas 可读取的数据源。"""
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
    """内部函数：把工作表定义归一化为"别名 → 工作表名"的映射。

    - 传入 {"plan": "计划类型匹配表"} → 原样返回
    - 传入 ["计划类型匹配表"] → 转为 {"计划类型匹配表": "计划类型匹配表"}
    """
    if isinstance(sheet_mapping, Mapping):
        return dict(sheet_mapping)

    return {sheet_name: sheet_name for sheet_name in sheet_mapping}
