"""
会话级 Excel 按需加载辅助函数。

本模块把“从 session_state 取当前文件三件套”和“按需读取 sheet/列”封装起来，
页面层只需要传入 sheet 映射和列映射，避免在每个页面重复调用
get_shared_source_bytes/name/token。
"""
from collections.abc import Mapping, Sequence

import pandas as pd

from app.core.loader import load_shared_sheets
from app.core.shared_source import (
    get_shared_source_bytes,
    get_shared_source_name,
    get_shared_source_token,
    get_tag_source_bytes,
    get_tag_source_name,
    get_tag_source_token,
)


def load_current_source_sheets(
    sheet_mapping: Mapping[str, str] | Sequence[str],
    usecols_mapping: Mapping[str, list[str] | str] | None = None,
) -> dict[str, pd.DataFrame]:
    """按需读取当前会话中的业务数据源工作表。

    Args:
        sheet_mapping: {别名: 工作表名} 或工作表名列表
        usecols_mapping: 可选的列读取范围，键支持别名或真实工作表名

    Returns:
        {别名: DataFrame} 字典，包含请求的业务数据源工作表
    """
    return load_shared_sheets(
        get_shared_source_bytes(),
        get_shared_source_name(),
        get_shared_source_token(),
        sheet_mapping,
        usecols_mapping,
    )


def load_current_tag_sheets(
    sheet_mapping: Mapping[str, str] | Sequence[str],
    usecols_mapping: Mapping[str, list[str] | str] | None = None,
) -> dict[str, pd.DataFrame]:
    """按需读取当前会话中的打标工作表。

    Args:
        sheet_mapping: {别名: 工作表名} 或工作表名列表
        usecols_mapping: 可选的列读取范围，键支持别名或真实工作表名

    Returns:
        {别名: DataFrame} 字典，包含请求的打标工作表
    """
    return load_shared_sheets(
        get_tag_source_bytes(),
        get_tag_source_name(),
        get_tag_source_token(),
        sheet_mapping,
        usecols_mapping,
    )
