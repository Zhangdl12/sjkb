"""
标签检验表的树节点构造逻辑。

三个核心函数对应三个标签页：
  - build_keyword_tree_payload()  → 关键词树形（词性分类 → 关键词）
  - build_audience_tree_payload() → 人群树形（人群分类 → 人群名称）
  - build_sku_tree_payload()      → SKU树形（分类 → 投放产品SKU）

树形数据格式（AgGrid 要求）：
  每行有一个 "path" 列，用 "||" 作为路径分隔符：
    - 父节点：path = "品牌词"
    - 子节点：path = "品牌词||爱他美"

排序规则：
  - 父节点（分类）按费用降序
  - 每个分类下的子节点也按费用降序
"""
from dataclasses import dataclass

import pandas as pd

from app.dashboards.tag_validation.config import AppConfig


@dataclass(frozen=True)
class KeywordTreePayload:
    """关键词树形表渲染载荷。"""
    tree_df: pd.DataFrame


@dataclass(frozen=True)
class AudienceTreePayload:
    """人群树形表渲染载荷。"""
    tree_df: pd.DataFrame


@dataclass(frozen=True)
class SkuTreePayload:
    """SKU 树形表渲染载荷。"""
    tree_df: pd.DataFrame


# ======================================================================
#  通用树形构建器
# ======================================================================

def _build_tree_rows(
    detail_df: pd.DataFrame,
    category_col: str,
    item_col: str,
    cost_col: str,
    blank_label: str,
    child_value_cols: list[str] | None = None,
) -> pd.DataFrame:
    """通用的两级树形行数据构建函数。

    三个标签页的树形构造逻辑完全一致，提取公共逻辑避免重复。
    区别仅在于列名不同，由调用方传入。

    Args:
        detail_df: 明细数据（三列：分类/名称/费用）
        category_col: 分类列名
        item_col: 子节点列名
        cost_col: 费用列名
        blank_label: 空白分类占位文本
        child_value_cols: 仅子节点展示的附加列

    Returns:
        包含 path、cost_col 及附加列的 DataFrame
    """
    child_value_cols = child_value_cols or []
    grouped_child_value_cols = [
        column for column in child_value_cols if column != item_col
    ]

    # 按分类+名称汇总费用
    grouped = (
        detail_df.groupby([category_col, item_col], dropna=False)
        .agg(
            **{cost_col: (cost_col, "sum")},
            **{
                column: (column, "first")
                for column in grouped_child_value_cols
            },
        )
        .reset_index()
    )

    # 按分类汇总总费用并降序排列（决定第一级节点顺序）
    parent_df = (
        grouped.groupby(category_col, dropna=False)
        .agg(**{cost_col: (cost_col, "sum")})
        .reset_index()
        .sort_values(cost_col, ascending=False)
    )

    # 构建 AgGrid 树形行数据
    rows: list[dict[str, object]] = []
    for _, parent_row in parent_df.iterrows(): # iterrows 作用是迭代 DataFrame 的行 _— 迭代 DataFrame 的行,parent_row是每一行数据
        category = str(parent_row[category_col])
        parent_item = {
            "path": category,
            cost_col: float(parent_row[cost_col]),
        }
        for column in child_value_cols:
            parent_item[column] = ""
        rows.append(parent_item)

        child_df = grouped[
            grouped[category_col].astype(str) == category
        ].sort_values(cost_col, ascending=False)
        for _, child_row in child_df.iterrows():
            item_name = str(child_row[item_col]) or blank_label
            child_item = {
                "path": f"{category}||{item_name}",
                cost_col: float(child_row[cost_col]),
            }
            for column in child_value_cols:
                if column == item_col:
                    child_item[column] = item_name
                else:
                    child_item[column] = str(child_row[column]) if pd.notna(child_row[column]) else ""
            rows.append(child_item)

    return pd.DataFrame(rows)


# ======================================================================
#  关键词树形构造
# ======================================================================

def build_keyword_tree_payload(
    df: pd.DataFrame,
    group_by: list[str],
    config: AppConfig,
) -> KeywordTreePayload:
    """构造两级关键词树形表数据（词性分类 → 关键词）。"""
    _ = group_by

    if df.empty:
        return KeywordTreePayload(
            tree_df=pd.DataFrame(
                columns=[
                    "path",
                    config.display_keyword_cost_column,
                    config.keyword_column,
                ]
            )
        )

    tree_df = _build_tree_rows(
        df,
        category_col=config.display_keyword_category_column,
        item_col=config.keyword_column,
        cost_col=config.display_keyword_cost_column,
        blank_label=config.blank_category,
        child_value_cols=[config.keyword_column],
    )
    return KeywordTreePayload(tree_df=tree_df)


# ======================================================================
#  人群树形构造
# ======================================================================

def build_audience_tree_payload(
    df: pd.DataFrame,
    group_by: list[str],
    config: AppConfig,
) -> AudienceTreePayload:
    """构造两级人群树形表数据（人群分类 → 人群名称）。"""
    _ = group_by

    if df.empty:
        return AudienceTreePayload(
            tree_df=pd.DataFrame(
                columns=[
                    "path",
                    config.display_audience_cost_column,
                    config.audience_name_column,
                ]
            )
        )

    tree_df = _build_tree_rows(
        df,
        category_col=config.display_audience_category_column,
        item_col=config.audience_name_column,
        cost_col=config.display_audience_cost_column,
        blank_label=config.blank_category,
        child_value_cols=[config.audience_name_column],
    )
    return AudienceTreePayload(tree_df=tree_df)


# ======================================================================
#  SKU 树形构造
# ======================================================================

def build_sku_tree_payload(
    df: pd.DataFrame,
    group_by: list[str],
    config: AppConfig,
) -> SkuTreePayload:
    """构造两级 SKU 树形表数据（分类 → 投放产品SKU）。"""
    _ = group_by

    if df.empty:
        return SkuTreePayload(
            tree_df=pd.DataFrame(
                columns=[
                    "path",
                    config.display_sku_cost_column,
                    config.sku_fact_id_column,
                    config.sku_name_column,
                ]
            )
        )

    tree_df = _build_tree_rows(
        df,
        category_col=config.display_sku_category_column,
        item_col=config.sku_fact_id_column,
        cost_col=config.display_sku_cost_column,
        blank_label=config.blank_category,
        child_value_cols=[config.sku_fact_id_column, config.sku_name_column],
    )
    return SkuTreePayload(tree_df=tree_df)
