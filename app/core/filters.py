"""
通用侧边栏筛选能力。

提供 Streamlit 侧边栏的联动筛选器系统，核心规则如下：
1. 当前筛选器的候选项来自“前序筛选条件已生效后的数据”。
2. 多选筛选器默认全选时，若当前选择覆盖全部候选项，则视为未激活筛选。
3. 单选筛选器支持声明默认值；点击“恢复默认”后必须回到声明的默认值。
"""

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd
import streamlit as st


@dataclass(frozen=True)
class FilterField:
    """定义单个筛选控件的展示和默认行为。

    Args:
        column: DataFrame 中对应的列名。
        label: 侧边栏显示名称；未提供时直接使用列名。
        group: 分组名称；同组字段会显示在同一段落中。
        sort_values: 是否对候选值排序。
        default_all: 多选控件首次加载或重置时是否默认全选。
        control: 控件类型，支持多选和单选。
        default_latest: 单选控件是否默认选择候选列表中的最后一个值。
    """

    column: str
    label: str | None = None
    group: str = "筛选条件"
    sort_values: bool = False
    default_all: bool = True
    control: Literal["multiselect", "single_select"] = "multiselect"
    default_latest: bool = False


def render_sidebar_filters(
    df: pd.DataFrame,
    fields: list[FilterField] | tuple[FilterField, ...],
    title: str = "维度筛选器",
    key_prefix: str = "dashboard_filter",
) -> dict[str, list[Any]]:
    """渲染侧边栏筛选器并返回当前筛选结果。

    Args:
        df: 原始数据集，尚未应用筛选条件。
        fields: 筛选字段定义，声明顺序决定联动顺序。
        title: 侧边栏标题。
        key_prefix: 当前页面的 state 前缀，用于隔离不同页面的筛选状态。

    Returns:
        形如 `{列名: 已选值列表或单值}` 的筛选结果字典，可直接传给 `apply_filters()`。
    """

    st.sidebar.header(title)
    state_keys = _build_filter_state_keys(fields, key_prefix)
    reset_flag_key = f"{key_prefix}__reset_requested"

    if st.sidebar.button("恢复默认", key=f"{key_prefix}_reset_filters"):
        # 只清理当前页面的筛选状态；后续 rerun 时按字段声明重新回填默认值。
        _clear_filter_state_keys(state_keys, st.session_state)
        st.session_state[reset_flag_key] = True
        st.rerun()

    selections: dict[str, Any] = {}
    reset_requested = bool(st.session_state.get(reset_flag_key, False))

    grouped_fields: OrderedDict[str, list[FilterField]] = OrderedDict()
    for field in fields:
        grouped_fields.setdefault(field.group, []).append(field)

    for group_name, group_fields in grouped_fields.items():
        st.sidebar.subheader(group_name)
        for field in group_fields:
            # 当前字段的候选项只基于前序字段已生效后的数据生成，保持现有单向联动语义。
            filtered_df = apply_filters(df, selections, fields)
            options = _extract_options(filtered_df, field.column, field.sort_values)

            state_key = f"{key_prefix}_{field.column}"
            previous_selection = st.session_state.get(
                state_key,
                [] if field.control == "multiselect" else None,
            )

            if field.control == "single_select":
                if reset_requested:
                    default = _resolve_reset_widget_value(options, field, previous_selection)
                    st.session_state[state_key] = default
                else:
                    default = _resolve_single_default(options, previous_selection, field.default_latest)

                if not options:
                    st.sidebar.selectbox(
                        field.label or field.column,
                        options=["无可选项"],
                        index=0,
                        key=state_key,
                        disabled=True,
                    )
                    selections[field.column] = []
                    continue

                default_index = options.index(default) if default in options else 0
                selections[field.column] = st.sidebar.selectbox(
                    field.label or field.column,
                    options=options,
                    index=default_index,
                    key=state_key,
                )
                continue

            default = [value for value in _normalize_selected_values(previous_selection) if value in options]
            if not default and field.default_all:
                default = options
            if reset_requested:
                default = _resolve_reset_widget_value(options, field, previous_selection)
                st.session_state[state_key] = default

            selected_values = st.sidebar.multiselect(
                field.label or field.column,
                options=options,
                default=default,
                key=state_key,
            )
            selections[field.column] = _normalize_filter_selection(
                selected_values,
                options,
                field,
            )

    if reset_requested:
        st.session_state[reset_flag_key] = False

    return selections


def apply_filters(
    df: pd.DataFrame,
    selections: dict[str, Any],
    fields: list[FilterField] | tuple[FilterField, ...],
) -> pd.DataFrame:
    """按字段声明顺序对数据应用 AND 筛选。

    Args:
        df: 待筛选数据集。
        selections: 当前筛选结果字典。
        fields: 筛选字段定义，决定应用顺序。

    Returns:
        应用筛选后的 DataFrame 副本。
    """

    filtered_df = df.copy()
    for field in fields:
        selected_values = _normalize_selected_values(selections.get(field.column, []))
        if selected_values and field.column in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[field.column].isin(selected_values)]
    return filtered_df


def _extract_options(df: pd.DataFrame, column: str, sort_values: bool) -> list[Any]:
    """提取字段候选值列表。

    Args:
        df: 当前候选数据集。
        column: 目标列名。
        sort_values: 是否排序。

    Returns:
        去重后的候选值列表；列不存在时返回空列表。
    """

    if column not in df.columns:
        return []

    values = df[column].dropna().unique().tolist()
    if sort_values:
        values = sorted(values)
    return values


def _resolve_single_default(
    options: list[Any],
    previous_selection: Any,
    default_latest: bool,
) -> Any | None:
    """解析单选控件应使用的默认值。

    Args:
        options: 当前可选项列表。
        previous_selection: 历史选中值；仍然有效时优先沿用。
        default_latest: 是否默认选择最后一个候选项。

    Returns:
        用于 selectbox 的默认值；无候选项时返回 None。
    """

    if previous_selection in options:
        return previous_selection
    if not options:
        return None
    if default_latest:
        return options[-1]
    return options[0]


def _normalize_selected_values(selected_values: Any) -> list[Any]:
    """把单值或多值统一转换为列表。"""

    if selected_values is None:
        return []
    if isinstance(selected_values, list):
        return selected_values
    return [selected_values]


def _normalize_filter_selection(
    selected_values: list[Any],
    options: list[Any],
    field: FilterField,
) -> list[Any]:
    """把多选结果归一化为真实筛选语义。

    Args:
        selected_values: 当前控件选中值。
        options: 当前控件候选值。
        field: 当前字段定义。

    Returns:
        若为默认全选且用户仍选中全部候选项，则返回空列表表示“未激活筛选”；
        其他情况返回原始选中结果。
    """

    normalized_values = _normalize_selected_values(selected_values)
    if (
        field.control == "multiselect"
        and field.default_all
        and options
        and len(normalized_values) == len(options)
        and set(normalized_values) == set(options)
    ):
        return []
    return normalized_values


def _build_filter_state_keys(
    fields: list[FilterField] | tuple[FilterField, ...],
    key_prefix: str,
) -> list[str]:
    """构造当前页面所有筛选控件对应的 state key 列表。"""

    return [f"{key_prefix}_{field.column}" for field in fields]


def _clear_filter_state_keys(
    state_keys: list[str],
    state: dict[str, Any],
) -> None:
    """清理当前页面对应的筛选状态。"""

    for state_key in state_keys:
        state.pop(state_key, None)


def _resolve_reset_widget_value(
    options: list[Any],
    field: FilterField,
    previous_selection: Any,
) -> Any:
    """解析控件在“恢复默认”时应写回的值。

    Args:
        options: 当前候选项列表。
        field: 当前字段定义。
        previous_selection: 恢复前的旧值；单选重置时不会沿用，仅保留参数签名稳定。

    Returns:
        供 Streamlit widget 写回 state 的默认值。
    """

    if field.control == "single_select":
        # 恢复默认时必须回到字段声明的默认值，不能保留旧选择。
        return _resolve_single_default(options, None, field.default_latest)
    if field.default_all:
        return options
    return []
