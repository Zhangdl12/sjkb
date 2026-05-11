"""
素材分析看板的数据加载辅助函数。

SourceTables 是命名元组式的 dataclass，封装了本看板需要的三张工作表。
processor.py 通过 SourceTables 访问各表，比用字典字符串键更类型安全。
"""
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from app.core.loader import load_excel_sheets
from app.dashboards.material_analysis.config import AppConfig


@dataclass(frozen=True)
class SourceTables:
    """素材分析看板使用的命名源表集合。

    将 3 张 DataFrame 按语义命名，避免在代码中散落字符串键名。
    """
    creative: pd.DataFrame  # 数据中心-创意数据
    plan: pd.DataFrame      # 计划类型匹配表
    sku: pd.DataFrame       # 商品匹配表
