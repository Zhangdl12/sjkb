"""广告数据汇总处理器。

处理器是页面层的稳定入口，具体多来源归一化逻辑放在 source_normalizer 中，
避免页面直接了解各 Excel sheet 的字段差异。
"""
import pandas as pd

from app.dashboards.ad_summary.config import AppConfig
from app.dashboards.ad_summary.source_normalizer import (
    DataProcessingError,
    build_normalized_detail,
)


def build_ad_summary_dataset(
    tables: dict[str, pd.DataFrame],
    config: AppConfig,
) -> pd.DataFrame:
    """构建广告数据汇总数据集。

    Args:
        tables: 业务数据源和打标文件读取后的 DataFrame 字典。
        config: 广告汇总配置对象，提供工作表、字段和展示列名。

    Returns:
        统一字段后的明细数据，供筛选器和周期汇总模块使用。

    Raises:
        DataProcessingError: 缺少必要字段或加工失败时抛出。
    """
    return build_normalized_detail(tables, config)
