"""
素材分析看板的数据加工逻辑。

核心函数 build_analysis_dataset() 负责将 3 张源工作表合并为一张分析宽表。

加工步骤（按顺序执行）：
  1. 爱他美判断：检查"推广计划"列是否包含"爱他美"关键词 → 生成"爱他美判断"列
  2. 渠道关联：用"计划类型"关联计划类型匹配表 → 补充"新产品渠道"和"渠道类型"
  3. 商品关联：用"跟单SKU ID"关联商品匹配表的"京东skuID" → 补充"分类"
  4. 日期解析：将"日期"列（%Y%m%d 格式）转为 datetime → 派生年/月/日三列
  5. 空值填充：匹配不到的渠道、分类等用"未知*"常量填充

异常处理：
  - KeyError → 报告缺少必要字段
  - 其他异常 → 报告数据处理失败的通用错误
"""
import numpy as np
import pandas as pd

from app.dashboards.material_analysis.config import AppConfig
from app.dashboards.material_analysis.loader import SourceTables


class DataProcessingError(Exception):
    """源数据无法加工成分析宽表时抛出的异常（在页面中被捕获并显示为 st.error）。"""


def build_analysis_dataset(
    tables: SourceTables | dict[str, pd.DataFrame], config: AppConfig
) -> pd.DataFrame:
    """把上传工作簿加工成素材分析使用的宽表。

    Args:
        tables: 已加载的源表，包含 creative/plan/sku 三个 DataFrame
        config: 看板列名配置

    Returns:
        合并后的分析宽表 DataFrame（包含原始列 + 派生列）
    """
    try:
        # 归一化输入格式，统一为 SourceTables 对象
        source_tables = _normalize_source_tables(tables)
        creative_df = source_tables.creative.copy()
        plan_df = source_tables.plan.copy()
        sku_df = source_tables.sku.copy()

        # ----- 步骤 1: 爱他美品牌标记 -----
        # 如果"推广计划"列包含"爱他美"字符串 → 标记为"爱他美抢量"，否则"其他"
        is_aitamei = creative_df[config.campaign_column].astype(str).str.contains(
            config.aitamei_keyword,
            na=False,# 忽略空值 
        )
        creative_df[config.aitamei_column] = np.where(# 生成"爱他美判断"列
            is_aitamei,
            config.aitamei_value,
            config.other_aitamei,
        )

        # ----- 步骤 2: 渠道信息关联 -----
        # 从计划类型匹配表中提取"计划类型→渠道类型+新产品渠道"的映射
        # drop_duplicates 保证每个计划类型只有一条渠道信息
        plan_df = plan_df[
            [
                config.plan_type_column,
                config.new_product_channel_column,
                config.channel_type_column,
            ]
        ].drop_duplicates(subset=[config.plan_type_column])

        # 左连接：保留所有创意数据行，匹配不到的渠道填"未知*"
        creative_df = pd.merge(
            creative_df,
            plan_df,
            on=config.plan_type_column,
            how="left",
        )
        creative_df[config.new_product_channel_column] = creative_df[
            config.new_product_channel_column
        ].fillna(config.unknown_channel)
        creative_df[config.channel_type_column] = creative_df[
            config.channel_type_column
        ].fillna(config.unknown_channel_type)

        # ----- 步骤 3: 商品分类关联 -----
        # 用创意的"跟单SKU ID"关联商品匹配表的"京东skuID"
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

        # ----- 步骤 4: 日期解析与派生 -----
        # 原始日期格式为 %Y%m%d（如 "20231201"），errors="coerce" 让解析失败的值变为 NaT
        merged_df[config.date_column] = pd.to_datetime(
            merged_df[config.date_column].astype(str),
            format="%Y%m%d",
            errors="coerce",
        )
        merged_df[config.year_column] = merged_df[config.date_column].dt.year
        merged_df[config.month_column] = merged_df[config.date_column].dt.month
        # 日期格式化为 "年/月/日" 字符串，便于筛选器展示
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
            "数据处理报错: "
            f"{exc}\n(请检查原表中是否存在 '日期'、'推广计划'、'跟单SKU ID' 等基础列名)"
        ) from exc


def _normalize_source_tables(
    tables: SourceTables | dict[str, pd.DataFrame],
) -> SourceTables:
    """兼容 SourceTables 对象和通用字典映射两种输入。

    页面通过 select_required_sheets 传入字典，但 loader 模块可能传入 SourceTables。
    """
    if isinstance(tables, SourceTables):
        return tables

    return SourceTables(
        creative=tables["creative"],
        plan=tables["plan"],
        sku=tables["sku"],
    )


def _format_day_value(value: pd.Timestamp) -> str | float:
    """把 Timestamp 格式化为筛选使用的 "YYYY/M/D" 字符串。

    NaT（无效日期）返回 NaN，在筛选器中自动归入空值选项。
    """
    if pd.isna(value):
        return np.nan
    return f"{value.year}/{value.month}/{value.day}"
