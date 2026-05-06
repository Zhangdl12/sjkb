"""素材分析看板的数据加载辅助函数。"""

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from app.core.loader import DataLoadError, load_excel_sheets
from app.dashboards.material_analysis.config import AppConfig


@dataclass(frozen=True)
class SourceTables:
    """素材分析看板使用的命名源表集合。"""

    creative: pd.DataFrame
    plan: pd.DataFrame
    sku: pd.DataFrame


def load_source_tables(
    file_source: str | Path | bytes | BinaryIO, config: AppConfig
) -> SourceTables:
    """加载素材分析所需的三张源工作表。"""

    sheets = load_excel_sheets(
        file_source,
        {
            "plan": config.plan_sheet,
            "creative": config.creative_sheet,
            "sku": config.sku_sheet,
        },
    )
    return SourceTables(
        creative=sheets["creative"],
        plan=sheets["plan"],
        sku=sheets["sku"],
    )
