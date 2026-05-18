"""
标签检验表的数据处理逻辑。

三个核心函数对应三个标签页：
  - build_keyword_dataset()  → 关键词标签检验
  - build_audience_dataset() → 人群标签检验
  - build_sku_dataset()      → SKU 标签检验

本模块只负责把“业务数据源事实表”和“打标表”关联成树形表明细。
本轮标签检验表不计算 ROI、CPC、CTR 等分析指标，只按 SOP 直接汇总口径
保留广告费用字段：广告费用 = SUM(花费)。
"""
import pandas as pd

from app.dashboards.tag_validation.config import AppConfig
from app.dashboards.tag_validation.loader import (
    AudienceSourceTables,
    SkuSourceTables,
    SourceTables,
)


class DataProcessingError(Exception):
    """源数据无法加工成标签检验表时抛出的异常。"""


# ======================================================================
#  关键词标签检验
# ======================================================================

def build_keyword_dataset(
    tables: SourceTables | dict[str, pd.DataFrame], config: AppConfig
) -> pd.DataFrame:
    """把关键词数据源和关键词打标表加工成树形表所需的明细数据。

    Args:
        tables: 包含 keyword_fact 和 keyword_tag 两张 DataFrame 的对象或字典
        config: 标签检验表字段配置

    Returns:
        包含“词性分类 / 关键词 / 广告费用”的关键词明细 DataFrame
    """
    try:
        source_tables = _normalize_keyword_source_tables(tables)
        fact_df = source_tables.keyword_fact.copy()
        tag_df = source_tables.keyword_tag.copy()

        # 事实表关键词是关联键，先转成统一文本格式，避免数字型或空格导致匹配失败。
        fact_df[config.keyword_column] = fact_df[config.keyword_column].map(
            _normalize_text
        )
        # SOP 本轮采用直接汇总口径：广告费用来自事实表“花费”列。
        fact_df[config.display_keyword_cost_column] = pd.to_numeric(
            fact_df[config.keyword_cost_column], errors="coerce"
        ).fillna(0)

        # 打标表只保留关联键和分类列；先归一化再去重，避免 123 和 123.0 被当成两个标签。
        tag_df = tag_df[
            [config.keyword_column, config.keyword_category_column]
        ].copy()
        tag_df[config.keyword_column] = tag_df[config.keyword_column].map(
            _normalize_text
        )
        tag_df = tag_df.drop_duplicates(subset=[config.keyword_column])

        # 左连接保留事实表所有关键词，未打标关键词会在分类列被归入“(空白)”。
        merged_df = fact_df.merge(tag_df, on=config.keyword_column, how="left")
        merged_df[config.display_keyword_category_column] = merged_df[
            config.keyword_category_column
        ].map(_normalize_text)
        merged_df[config.display_keyword_category_column] = merged_df[
            config.display_keyword_category_column
        ].replace("", config.blank_category)

        return merged_df[
            [
                config.display_keyword_category_column,
                config.keyword_column,
                config.display_keyword_cost_column,
            ]
        ]
    except KeyError as exc:
        raise DataProcessingError(f"关键词数据缺少必要字段：{exc}") from exc
    except Exception as exc:
        raise DataProcessingError(f"关键词标签检验数据处理失败：{exc}") from exc


def _normalize_keyword_source_tables(
    tables: SourceTables | dict[str, pd.DataFrame],
) -> SourceTables:
    """把关键词源表输入归一化为 SourceTables 对象。

    Args:
        tables: SourceTables 实例，或包含 keyword_fact/keyword_tag 的字典

    Returns:
        关键词标签检验使用的 SourceTables 对象
    """
    if isinstance(tables, SourceTables):
        return tables
    return SourceTables(
        keyword_fact=tables["keyword_fact"],
        keyword_tag=tables["keyword_tag"],
    )


# ======================================================================
#  人群标签检验
# ======================================================================

def build_audience_dataset(
    tables: AudienceSourceTables | dict[str, pd.DataFrame], config: AppConfig
) -> pd.DataFrame:
    """把人群数据源和人群打标表加工成树形表所需的明细数据。

    Args:
        tables: 包含 audience_fact 和 audience_tag 两张 DataFrame 的对象或字典
        config: 标签检验表字段配置

    Returns:
        包含“人群分类 / 人群名称 / 广告费用”的人群明细 DataFrame
    """
    try:
        source_tables = _normalize_audience_source_tables(tables)
        fact_df = source_tables.audience_fact.copy()
        tag_df = source_tables.audience_tag.copy()

        # 人群名称是事实表和打标表的共同关联键，统一成文本后再做 merge。
        fact_df[config.audience_name_column] = fact_df[config.audience_name_column].map(
            _normalize_text
        )
        fact_df[config.display_audience_cost_column] = pd.to_numeric(
            fact_df[config.audience_cost_column], errors="coerce"
        ).fillna(0)

        # 打标表按人群名称去重，避免同一人群重复打标时放大事实表费用。
        tag_df = tag_df[
            [config.audience_name_column, config.audience_category_column]
        ].copy()
        tag_df[config.audience_name_column] = tag_df[config.audience_name_column].map(
            _normalize_text
        )
        tag_df = tag_df.drop_duplicates(subset=[config.audience_name_column])

        # 左连接保留事实表全部人群，未匹配人群分类统一落到“(空白)”。
        merged_df = fact_df.merge(tag_df, on=config.audience_name_column, how="left")
        merged_df[config.display_audience_category_column] = merged_df[
            config.audience_category_column
        ].map(_normalize_text)
        merged_df[config.display_audience_category_column] = merged_df[
            config.display_audience_category_column
        ].replace("", config.blank_category)

        return merged_df[
            [
                config.display_audience_category_column,
                config.audience_name_column,
                config.display_audience_cost_column,
            ]
        ]
    except KeyError as exc:
        raise DataProcessingError(f"人群数据缺少必要字段：{exc}") from exc
    except Exception as exc:
        raise DataProcessingError(f"人群标签检验数据处理失败：{exc}") from exc


def _normalize_audience_source_tables(
    tables: AudienceSourceTables | dict[str, pd.DataFrame],
) -> AudienceSourceTables:
    """把人群源表输入归一化为 AudienceSourceTables 对象。

    Args:
        tables: AudienceSourceTables 实例，或包含 audience_fact/audience_tag 的字典

    Returns:
        人群标签检验使用的 AudienceSourceTables 对象
    """
    if isinstance(tables, AudienceSourceTables):
        return tables
    return AudienceSourceTables(
        audience_fact=tables["audience_fact"],
        audience_tag=tables["audience_tag"],
    )


# ======================================================================
#  SKU 标签检验
# ======================================================================

def build_sku_dataset(
    tables: SkuSourceTables | dict[str, pd.DataFrame], config: AppConfig
) -> pd.DataFrame:
    """把站内外数据源和商品打标表加工成 SKU 树形表所需的明细数据。

    与关键词/人群不同：关联键在两张表中列名不同。
    事实表使用“跟单SKU ID”，商品打标表使用“京东skuID”，左连接时需要分别指定
    left_on 和 right_on。

    Args:
        tables: 包含 sku_fact 和 sku_tag 两张 DataFrame 的对象或字典
        config: 标签检验表字段配置

    Returns:
        包含“新分类 / 跟单SKU ID / 广告费用 / 商品名称”的 SKU 明细 DataFrame
    """
    try:
        source_tables = _normalize_sku_source_tables(tables)
        fact_df = source_tables.sku_fact.copy()
        tag_df = source_tables.sku_tag.copy()

        # ----- 步骤 1: 事实表 —— 文本归一化 + 费用转数值 -----
        fact_df[config.sku_fact_id_column] = fact_df[config.sku_fact_id_column].map(
            _normalize_text
        )
        fact_df[config.display_sku_cost_column] = pd.to_numeric(
            fact_df[config.sku_cost_column], errors="coerce"
        ).fillna(0)

        # ----- 步骤 2: 商品打标表 —— 文本归一化 + 去重 -----
        # 商品打标表只保留 SKU、分类和商品名，避免其他辅助列进入后续树表。
        tag_df = tag_df[
            [
                config.sku_match_id_column,
                config.sku_category_column,
                config.sku_name_column,
            ]
        ].copy()
        tag_df[config.sku_match_id_column] = tag_df[config.sku_match_id_column].map(
            _normalize_text
        )
        tag_df = tag_df.drop_duplicates(subset=[config.sku_match_id_column])
        tag_df[config.sku_category_column] = tag_df[config.sku_category_column].map(
            _normalize_text
        )
        tag_df[config.sku_name_column] = tag_df[config.sku_name_column].map(
            _normalize_text
        )

        # ----- 步骤 3: 左连接 —— 用两个不同的列名关联 -----
        # 关键区别：left_on（站内外数据源.跟单SKU ID）← right_on（商品打标.京东skuID）。
        merged_df = fact_df.merge(
            tag_df,
            left_on=config.sku_fact_id_column,
            right_on=config.sku_match_id_column,
            how="left",
        )

        # ----- 步骤 4: 分类和商品名称填充 -----
        merged_df[config.display_sku_category_column] = merged_df[
            config.sku_category_column
        ].map(_normalize_text)
        merged_df[config.display_sku_category_column] = merged_df[
            config.display_sku_category_column
        ].replace("", config.blank_category)
        merged_df[config.sku_name_column] = merged_df[config.sku_name_column].map(
            _normalize_text
        )

        # ----- 步骤 5: 只保留渲染需要的四列 -----
        return merged_df[
            [
                config.display_sku_category_column,
                config.sku_fact_id_column,
                config.display_sku_cost_column,
                config.sku_name_column,
            ]
        ]
    except KeyError as exc:
        raise DataProcessingError(f"SKU数据缺少必要字段：{exc}") from exc
    except Exception as exc:
        raise DataProcessingError(f"SKU标签检验数据处理失败：{exc}") from exc


def _normalize_sku_source_tables(
    tables: SkuSourceTables | dict[str, pd.DataFrame],
) -> SkuSourceTables:
    """把 SKU 源表输入归一化为 SkuSourceTables 对象。

    Args:
        tables: SkuSourceTables 实例，或包含 sku_fact/sku_tag 的字典

    Returns:
        SKU 标签检验使用的 SkuSourceTables 对象
    """
    if isinstance(tables, SkuSourceTables):
        return tables
    return SkuSourceTables(
        sku_fact=tables["sku_fact"],
        sku_tag=tables["sku_tag"],
    )


# ======================================================================
#  通用工具函数
# ======================================================================

def _normalize_text(value: object) -> str:
    """统一文本字段格式。

    处理三件事：
      1. pd.isna 检查，空值返回 ""
      2. strip() 去除前后空格
      3. 去除 ".0" 后缀，如 "12345.0" 转为 "12345"

    Args:
        value: 任意来源的单元格值

    Returns:
        归一化后的文本；空值返回空字符串
    """
    if pd.isna(value):
        return ""

    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text
