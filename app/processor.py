"""数据加工与筛选模块。

这里承接 data_loader 读入的原始表，负责把“多张业务表”加工成
“页面可直接使用的一张分析宽表”。同时也负责构建筛选器候选值和应用筛选条件。

设计原则：
1. 所有字段派生、merge、空值填充都放在这里；
2. UI 不关心底层清洗过程，只消费结果；
3. metrics 只关心计算，不参与数据修补。
"""

import numpy as np
import pandas as pd

from app.config import AppConfig
from app.data_loader import SourceTables


class DataProcessingError(Exception):
    """数据清洗或加工失败。"""


def build_analysis_dataset(tables: SourceTables, config: AppConfig) -> pd.DataFrame:
    """将原始三张表加工为可分析的宽表。

    核心步骤：
    1. 从创意表中识别“爱他美判断”；
    2. 关联计划类型映射表，补充渠道属性；
    3. 关联商品映射表，补充分类属性；
    4. 解析日期并派生 年 / 月 / 日 三个筛选字段。

    返回结果会被主流程缓存，因此这里尽量保证逻辑纯粹，不依赖 Streamlit UI 状态。
    """

    try:
        # 复制原始表，避免后续加工直接污染 data_loader 输出的对象。
        creative_df = tables.creative.copy()
        plan_df = tables.plan.copy()
        sku_df = tables.sku.copy()

        # 根据推广计划名做模糊匹配，生成业务需要的“爱他美判断”字段。
        # `na=False` 可以让空值直接视为不匹配，避免 contains 遇到 NaN 报错。
        is_aitamei = creative_df[config.campaign_column].astype(str).str.contains(
            config.aitamei_keyword, na=False
        )
        creative_df[config.aitamei_column] = np.where(
            is_aitamei, config.aitamei_value, config.other_aitamei
        )

        # 计划映射表里只保留 join 所需字段，并按计划类型去重，
        # 防止一对多映射把事实表重复放大。
        plan_df = plan_df[
            [
                config.plan_type_column,
                config.new_product_channel_column,
                config.channel_type_column,
            ]
        ].drop_duplicates(subset=[config.plan_type_column])

        # 为创意事实表补充渠道相关维度。
        creative_df = pd.merge(
            creative_df,
            plan_df,
            on=config.plan_type_column,
            how="left",
        )
        # 未匹配上的维度统一填充默认值，保证筛选器和透视表不会出现 NaN。
        creative_df[config.new_product_channel_column] = creative_df[
            config.new_product_channel_column
        ].fillna(config.unknown_channel)
        creative_df[config.channel_type_column] = creative_df[
            config.channel_type_column
        ].fillna(config.unknown_channel_type)

        # 基于 SKU 映射表补充商品分类。
        # 这里只选取必要字段，避免把无关列带进最终分析宽表。
        merged_df = pd.merge(
            creative_df,
            sku_df[[config.jd_sku_id_column, config.category_column]],
            left_on=config.sku_id_column,
            right_on=config.jd_sku_id_column,
            how="left",
        )
        merged_df[config.category_column] = merged_df[config.category_column].fillna(
            config.unknown_category
        )

        # 原始日期为 20250101 形式，这里统一解析成 datetime，
        # 再拆分出年、月，以及页面当前沿用的字符串格式“YYYY/M/D”。
        merged_df[config.date_column] = pd.to_datetime(
            merged_df[config.date_column].astype(str),
            format="%Y%m%d",
            errors="coerce",
        )
        merged_df[config.year_column] = merged_df[config.date_column].dt.year
        merged_df[config.month_column] = merged_df[config.date_column].dt.month
        # “日” 保持字符串而不是 datetime，目的是与原始页面展示与筛选行为一致。
        merged_df[config.day_column] = merged_df[config.date_column].apply(
            _format_day_value
        )

        return merged_df
    except KeyError as exc:
        raise DataProcessingError(
            f"数据缺少必要字段: {exc}. 请检查原表字段名是否与配置一致。"
        ) from exc
    except Exception as exc:
        raise DataProcessingError(
            f"数据处理报错: {exc}\n(请检查原表中是否存在 '日期', '推广计划', '跟单SKU ID' 等基础列名)"
        ) from exc


def build_filter_options(df: pd.DataFrame, config: AppConfig) -> dict[str, list]:
    """为页面筛选器构建每个维度的候选值列表。"""

    options: dict[str, list] = {}

    for column in config.filter_columns:
        if column not in df.columns:
            # 某些字段若因数据源变化暂时缺失，UI 仍然可以优雅降级。
            options[column] = []
            continue

        values = df[column].dropna().unique().tolist()
        if column in config.time_filter_columns:
            # 时间维度排序后更符合人的浏览习惯，业务维度保留原始出现顺序。
            values = sorted(values)
        options[column] = values

    return options


def apply_filters(
    df: pd.DataFrame, selections: dict[str, list], config: AppConfig
) -> pd.DataFrame:
    """按用户侧边栏选择逐维过滤数据。

    这里采用“有选择才过滤”的策略：
    - 若某维度为空列表，视为不过滤；
    - 若维度列不存在，也直接跳过，避免页面因字段缺失整体报错。
    """

    filtered_df = df.copy()

    for column in config.filter_columns:
        selected_values = selections.get(column, [])
        if selected_values and column in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[column].isin(selected_values)]

    return filtered_df


def _format_day_value(value: pd.Timestamp) -> str | float:
    """把日期格式化为原页面使用的 `YYYY/M/D` 字符串。

    返回 `np.nan` 是为了让上游 `dropna()` 等 Pandas 逻辑继续正常工作。
    """

    if pd.isna(value):
        return np.nan
    return f"{value.year}/{value.month}/{value.day}"
