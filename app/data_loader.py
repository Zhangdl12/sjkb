"""原始数据读取模块。

这个模块只负责“把 Excel 读进来”，不参与任何业务清洗。这样可以保证：
1. 数据读取失败与业务处理失败能被明确区分；
2. 后续若数据源从 Excel 切到 CSV / 数据库，只需要优先替换这里；
3. processor 可以假定自己拿到的是 DataFrame，而不用关心文件 I/O 细节。
"""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from app.config import AppConfig


class DataLoadError(Exception):
    """读取原始数据失败。"""


@dataclass(frozen=True) 
class SourceTables:
    """承载三张原始工作表的数据对象。"""

    creative: pd.DataFrame
    plan: pd.DataFrame
    sku: pd.DataFrame


def load_source_tables(
    file_source: str | Path | bytes | BinaryIO, config: AppConfig
) -> SourceTables:
    """读取看板所需的三张 Excel 工作表。"""

    excel_source = _normalize_excel_source(file_source)

    try:
        excel_file = pd.ExcelFile(excel_source)
        plan_df = excel_file.parse(config.plan_sheet)
        creative_df = excel_file.parse(config.creative_sheet)
        sku_df = excel_file.parse(config.sku_sheet)
    except Exception as exc:
        raise DataLoadError(f"读取 Excel 数据失败: {exc}") from exc

    return SourceTables(creative=creative_df, plan=plan_df, sku=sku_df)


def _normalize_excel_source(file_source: str | Path | bytes | BinaryIO):
    """将本地路径或上传的 Excel 数据源归一化为 pandas 可读对象。"""

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
