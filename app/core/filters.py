"""
通用侧边栏筛选能力。

提供 Streamlit 侧边栏的联动多选筛选器系统。

核心设计：下游选项随上游选择动态收敛
  - 用户在第 1 个筛选器中选择"A"后，第 2 个筛选器只显示数据中"列1=A"的那些行的列2可选值
  - 以此类推，保证用户看到的选项组合始终是数据中实际存在的

使用方式（在看板页面中）：
  filter_fields = (
      FilterField("年", group="时间维度", sort_values=True),
      FilterField("渠道类型", group="业务维度"),
  )
  selections = render_sidebar_filters(df, filter_fields)  # 渲染侧边栏
  filtered_df = apply_filters(df, selections, filter_fields)  # 应用筛选
"""
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st


@dataclass(frozen=True)
class FilterField:
    """单个侧边栏筛选控件的定义。

    Attributes:
        column: DataFrame 中对应的列名
        label: 侧边栏显示的标签，默认与 column 相同
        group: 分组名称。同一 group 的筛选器会归在一个 subheader 下，
               不同 group 之间用分割线隔开。
        sort_values: 是否对下拉选项排序（数字列建议 True，文本列建议 False）
        default_all: 是否默认全选。为 True 时初次进入页面会自动选中全部选项。
    """
    column: str
    label: str | None = None
    group: str = "筛选条件"
    sort_values: bool = False
    default_all: bool = True


def build_filter_options(
    df: pd.DataFrame,
    fields: list[FilterField] | tuple[FilterField, ...],
) -> dict[str, list[Any]]:
    """为所有筛选字段构建可选值列表（通常在 render_sidebar_filters 内部使用）。"""
    return {
        field.column: _extract_options(df, field.column, field.sort_values)
        for field in fields
    }


def render_sidebar_filters(
    df: pd.DataFrame,
    fields: list[FilterField] | tuple[FilterField, ...],
    title: str = "维度筛选器",
    key_prefix: str = "dashboard_filter",
) -> dict[str, list[Any]]:
    """在侧边栏中按分组渲染多选筛选器，并动态收敛下游选项。

    这是看板页面的主要入口。每个筛选器渲染时，会先用前面筛选器的已选值过滤数据，
    然后从过滤后的数据中提取可选值 —— 实现"下游选项随上游收敛"。

    Args:
        df: 当前的数据集（尚未应用筛选）
        fields: 筛选字段列表，按声明顺序依次渲染
        title: 侧边栏顶部标题
        key_prefix: session_state 键前缀，多页面时用于区分不同看板的筛选状态

    Returns:
        {列名: [已选值列表]} 字典，可直接传给 apply_filters()
    """
    st.sidebar.header(title)
    selections: dict[str, list[Any]] = {}

    # 按 group 分组，保持声明顺序
    grouped_fields: OrderedDict[str, list[FilterField]] = OrderedDict()
    for field in fields:
        grouped_fields.setdefault(field.group, []).append(field)

    for group_name, group_fields in grouped_fields.items():
        st.sidebar.subheader(group_name)
        for field in group_fields:
            # 关键：每次渲染筛选器前，先用已有的 selections 过滤数据
            # 这样当前筛选器的可选值就只来自"前面筛选条件已匹配的行"
            filtered_df = apply_filters(df, selections, fields)
            options = _extract_options(filtered_df, field.column, field.sort_values)

            # 从 session_state 恢复用户上次的选择（页面 rerun 时保留）
            state_key = f"{key_prefix}_{field.column}"
            previous_selection = st.session_state.get(state_key, [])

            # 如果上次选择的值在当前数据中仍然有效，则沿用；否则回退到全选
            default = [value for value in previous_selection if value in options]
            if not default and field.default_all:
                default = options

            # 渲染多选组件，key 参数让 Streamlit 自动管理 widget 状态
            selections[field.column] = st.sidebar.multiselect(
                field.label or field.column,
                options=options,
                default=default,
                key=state_key,
            )

    return selections


def apply_filters(
    df: pd.DataFrame,
    selections: dict[str, list[Any]],
    fields: list[FilterField] | tuple[FilterField, ...],
) -> pd.DataFrame:
    """按 FilterField 声明顺序，依次应用当前激活的筛选条件。

    筛选之间是 AND 关系：某个列选了多个值 → 该列的 OR；不同列之间 → AND。

    Args:
        df: 待筛选的 DataFrame
        selections: render_sidebar_filters 的返回值
        fields: 筛选字段列表（决定筛选的应用顺序）

    Returns:
        筛选后的 DataFrame 副本
    """
    filtered_df = df.copy()
    for field in fields:
        selected_values = selections.get(field.column, [])
        # 只有在用户确实选择了部分值（且列存在）时才过滤
        if selected_values and field.column in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[field.column].isin(selected_values)]
    return filtered_df


def _extract_options(df: pd.DataFrame, column: str, sort_values: bool) -> list[Any]:
    """内部函数：提取某个列的唯一切可选值列表。

    Args:
        df: 数据 DataFrame
        column: 列名
        sort_values: 是否排序

    Returns:
        唯一值列表。如果列不存在则返回空列表。
    """
    if column not in df.columns:
        return []

    values = df[column].dropna().unique().tolist()
    if sort_values:
        values = sorted(values)
    return values
