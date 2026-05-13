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
from typing import Literal

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
        control: 控件类型，默认多选，可选单选。
        default_latest: 单选时是否默认选择候选列表中的最后一个值。
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
    state_keys = _build_filter_state_keys(fields, key_prefix)
    reset_flag_key = f"{key_prefix}__reset_requested"
    if st.sidebar.button("恢复默认", key=f"{key_prefix}_reset_filters"):
        preserved_state = _build_preserved_single_select_state(
            fields,
            key_prefix,
            st.session_state,
        )
        _clear_filter_state_keys(state_keys, st.session_state)
        st.session_state.update(preserved_state)
        st.session_state[reset_flag_key] = True
        st.rerun()

    selections: dict[str, Any] = {}
    reset_requested = bool(st.session_state.get(reset_flag_key, False))

    # 按 group 分组，保持声明顺序
    grouped_fields: OrderedDict[str, list[FilterField]] = OrderedDict()#新建一个有序字典来存储分组后的筛选字段
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

            # 如果上次选择的值在当前数据中仍然有效，则沿用；否则回退到全选
            default = [value for value in _normalize_selected_values(previous_selection) if value in options]
            if not default and field.default_all: # 如果默认全选，且当前数据中不存在默认值，则回退到全选
                default = options
            if reset_requested:
                default = _resolve_reset_widget_value(options, field, previous_selection)
                st.session_state[state_key] = default

            # 渲染多选组件，key 参数让 Streamlit 自动管理 widget 状态
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
        selected_values = _normalize_selected_values(selections.get(field.column, []))
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


def _resolve_single_default(
    options: list[Any],
    previous_selection: Any,
    default_latest: bool,
) -> Any | None:
    """解析单选控件的默认值。"""
    if previous_selection in options:
        return previous_selection
    if not options:
        return None
    if default_latest:
        return options[-1]
    return options[0]


def _normalize_selected_values(selected_values: Any) -> list[Any]:
    """将单值/多值统一归一化为列表。"""
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
    """将多选结果归一化为真实筛选语义。

    默认全选的多选框，如果当前选择覆盖了全部候选项，
    应视为“未激活筛选”，而不是显式的全量过滤条件。
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
    """构造当前页面全部筛选控件的 session_state keys。"""
    return [f"{key_prefix}_{field.column}" for field in fields]


def _clear_filter_state_keys(
    state_keys: list[str],
    state: dict[str, Any],
) -> None:
    """只清理当前页面筛选相关的 state keys。"""
    for state_key in state_keys:
        state.pop(state_key, None)


def _build_preserved_single_select_state(
    fields: list[FilterField] | tuple[FilterField, ...],
    key_prefix: str,
    state: dict[str, Any],
) -> dict[str, Any]:
    """恢复默认时保留当前单选控件值。"""
    preserved_state: dict[str, Any] = {}
    for field in fields:
        if field.control != "single_select":
            continue
        state_key = f"{key_prefix}_{field.column}"
        if state_key in state:
            preserved_state[state_key] = state[state_key]
    return preserved_state


def _resolve_reset_widget_value(
    options: list[Any],
    field: FilterField,
    previous_selection: Any,
) -> Any:
    """恢复默认时，为当前控件解析应该写回的 widget 值。"""
    if field.control == "single_select":
        return _resolve_single_default(options, previous_selection, field.default_latest)
    if field.default_all:
        return options
    return []
