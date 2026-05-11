"""
标签检验表的数据处理逻辑。

三个核心函数对应三个标签页：
  - build_keyword_dataset()  → 关键词标签检验
  - build_audience_dataset() → 人群标签检验
  - build_sku_dataset()      → SKU标签检验

SKU 与关键词/人群的不同之处：
  关联键在两张表中列名不同（投放产品SKU ← 京东skuID），
  其余加工逻辑完全一致：
    1. 文本归一化：去空格、去 ".0" 后缀
    2. 费用转数值
    3. 左连接匹配表补充分类
    4. 空白分类标记为"(空白)"
"""
import pandas as pd
import streamlit as st

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

@st.cache_data(show_spinner=False)
def build_keyword_dataset(
    tables: SourceTables | dict[str, pd.DataFrame], config: AppConfig
) -> pd.DataFrame:
    """把关键词事实表和匹配表加工成树形表所需的明细数据。"""
    try:
        source_tables = _normalize_keyword_source_tables(tables)
        fact_df = source_tables.keyword_fact.copy()
        match_df = source_tables.keyword_match.copy()

        fact_df[config.keyword_column] = fact_df[config.keyword_column].map(
            _normalize_text
        )
        fact_df[config.display_keyword_cost_column] = pd.to_numeric(
            fact_df[config.keyword_cost_column], errors="coerce"
        ).fillna(0)

        match_df = match_df[
            [config.keyword_column, config.keyword_category_column]
        ].drop_duplicates(subset=[config.keyword_column])
        match_df[config.keyword_column] = match_df[config.keyword_column].map(
            _normalize_text
        )

        merged_df = fact_df.merge(match_df, on=config.keyword_column, how="left")
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
    if isinstance(tables, SourceTables):
        return tables
    return SourceTables(
        keyword_match=tables["keyword_match"],
        keyword_fact=tables["keyword_fact"],
    )


# ======================================================================
#  人群标签检验
# ======================================================================

@st.cache_data(show_spinner=False)
def build_audience_dataset(
    tables: AudienceSourceTables | dict[str, pd.DataFrame], config: AppConfig
) -> pd.DataFrame:
    """把人群事实表和匹配表加工成树形表所需的明细数据。"""
    try:
        source_tables = _normalize_audience_source_tables(tables)
        fact_df = source_tables.audience_fact.copy()
        match_df = source_tables.audience_match.copy()

        fact_df[config.audience_name_column] = fact_df[config.audience_name_column].map(
            _normalize_text
        )
        fact_df[config.display_audience_cost_column] = pd.to_numeric(
            fact_df[config.audience_cost_column], errors="coerce"
        ).fillna(0)

        match_df = match_df[
            [config.audience_name_column, config.audience_category_column]
        ].drop_duplicates(subset=[config.audience_name_column])
        match_df[config.audience_name_column] = match_df[config.audience_name_column].map(
            _normalize_text
        )

        merged_df = fact_df.merge(match_df, on=config.audience_name_column, how="left")
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
    if isinstance(tables, AudienceSourceTables):
        return tables
    return AudienceSourceTables(
        audience_match=tables["audience_match"],
        audience_fact=tables["audience_fact"],
    )


# ======================================================================
#  SKU 标签检验
# ======================================================================

@st.cache_data(show_spinner=False)
def build_sku_dataset(
    tables: SkuSourceTables | dict[str, pd.DataFrame], config: AppConfig
) -> pd.DataFrame:
    """把产品事实表和商品匹配表加工成 SKU 树形表所需的明细数据。

    与关键词/人群不同：关联键在两张表中列名不同——
      事实表用「投放产品SKU」，匹配表用「京东skuID」，
      左连接时需要分别指定 left_on 和 right_on。

    Args:
        tables: 包含 sku_match 和 sku_fact 两个 DataFrame
        config: 看板列名配置

    Returns:
        包含三列的数据集：[SKU未分类, 投放产品SKU, SKU费用]
    """
    try:
        source_tables = _normalize_sku_source_tables(tables)
        fact_df = source_tables.sku_fact.copy()
        match_df = source_tables.sku_match.copy()

        # ----- 步骤 1: 事实表 —— 文本归一化 + 费用转数值 -----
        fact_df[config.sku_fact_id_column] = fact_df[config.sku_fact_id_column].map(
            _normalize_text
        )
        fact_df[config.display_sku_cost_column] = pd.to_numeric(
            fact_df[config.sku_cost_column], errors="coerce"
        ).fillna(0)

        # ----- 步骤 2: 匹配表 —— 文本归一化 + 去重 -----
        match_df = match_df[
            [
                config.sku_match_id_column,
                config.sku_category_column,
                config.sku_name_column,
            ]
        ].drop_duplicates(subset=[config.sku_match_id_column])
        match_df[config.sku_match_id_column] = match_df[config.sku_match_id_column].map(
            _normalize_text
        )
        match_df[config.sku_category_column] = match_df[config.sku_category_column].map(
            _normalize_text
        )
        match_df[config.sku_name_column] = match_df[config.sku_name_column].map(
            _normalize_text
        )

        # ----- 步骤 3: 左连接 —— 用两个不同的列名关联 -----
        # 关键区别：left_on（事实表.投放产品SKU）← right_on（匹配表.京东skuID）
        merged_df = fact_df.merge(
            match_df,
            left_on=config.sku_fact_id_column,
            right_on=config.sku_match_id_column,
            how="left",
        )

        # ----- 步骤 4: 分类填充 -----
        merged_df[config.display_sku_category_column] = merged_df[
            config.sku_category_column
        ].fillna("").replace("", config.blank_category)
        merged_df[config.sku_name_column] = merged_df[config.sku_name_column].fillna("")

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
    """把字典形式的 sku 源表转为类型安全的 SkuSourceTables 对象。"""
    if isinstance(tables, SkuSourceTables):
        return tables
    return SkuSourceTables(
        sku_match=tables["sku_match"],
        sku_fact=tables["sku_fact"],
    )


# ======================================================================
#  通用工具函数
# ======================================================================

def _normalize_text(value: object) -> str:
    """统一文本字段格式。

    处理三件事：
      1. pd.isna 检查 → 空值返回 ""
      2. .strip() 去除前后空格
      3. 去除 ".0" 后缀（如 "12345.0" → "12345"）
    """
    if pd.isna(value):
        return ""

    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text
