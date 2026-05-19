"""页面级状态控件辅助能力。"""

from collections.abc import Sequence
from typing import Any, Literal

import streamlit as st


def render_page_radio(
    label: str,
    options: Sequence[Any],
    key: str,
    default: Any,
    horizontal: bool = False,
    label_visibility: Literal["visible", "hidden", "collapsed"] = "visible",
) -> Any:
    """渲染需要跨 rerun 保持选择的页面主单选控件。

    Args:
        label: 单选控件展示给用户的标题。
        options: 单选控件候选项，顺序即页面展示顺序。
        key: Streamlit widget 使用的稳定 state key。
        default: 当前页面首次进入或旧状态失效时使用的默认选项。
        horizontal: 是否使用横向单选布局。
        label_visibility: Streamlit 标签展示策略。

    Returns:
        用户当前选中的单选项。
    """

    option_list = list(options)
    selected_value = _resolve_page_radio_value(option_list, key, default, st.session_state)
    selected_index = option_list.index(selected_value)

    selected_value = st.radio(
        label,
        option_list,
        index=selected_index,
        horizontal=horizontal,
        label_visibility=label_visibility,
        key=key,
    )
    # Streamlit 的 widget key 可能在某些中途 rerun 场景被清理；额外保存一份非 widget 状态，
    # 让后续页面重跑时可以恢复用户刚才选择的页面主视图。
    st.session_state[_build_page_radio_memory_key(key)] = selected_value
    return selected_value


def ensure_page_radio_state(
    options: Sequence[Any],
    key: str,
    default: Any,
    state: dict[str, Any],
) -> Any:
    """确保页面主 radio 的 widget 状态和持久状态保持一致。

    Args:
        options: 当前 radio 的有效候选项。
        key: Streamlit widget 使用的稳定 state key。
        default: 当前页面声明的默认选项。
        state: 待读写的 session state；测试中可传入普通字典。

    Returns:
        本轮应写回 widget state 的选中值。
    """

    selected_value = _resolve_page_radio_value(options, key, default, state)
    memory_key = _build_page_radio_memory_key(key)

    # 同步 widget key 和持久 key：widget key 负责驱动 st.radio，持久 key 负责抵抗中途 rerun 清理。
    state[key] = selected_value
    state[memory_key] = selected_value
    return selected_value


def _resolve_page_radio_value(
    options: Sequence[Any],
    key: str,
    default: Any,
    state: dict[str, Any],
) -> Any:
    """解析页面主 radio 本轮应展示的选中值。

    Args:
        options: 当前 radio 的有效候选项。
        key: Streamlit widget 使用的稳定 state key。
        default: 当前页面声明的默认选项。
        state: 待读取的 session state。

    Returns:
        经过 widget 状态、持久状态和默认值优先级解析后的选中值。
    """

    option_list = list(options)
    if not option_list:
        raise ValueError("页面主 radio 至少需要一个候选项")

    fallback_value = default if default in option_list else option_list[0]
    memory_key = _build_page_radio_memory_key(key)
    current_value = state.get(key)
    memory_value = state.get(memory_key)

    if current_value in option_list:
        return current_value
    if memory_value in option_list:
        return memory_value
    return fallback_value


def _build_page_radio_memory_key(key: str) -> str:
    """构造页面主 radio 的持久状态 key。

    Args:
        key: Streamlit widget 使用的稳定 state key。

    Returns:
        与 widget key 对应、但不会被 radio widget 直接占用的持久状态 key。
    """

    return f"{key}__persistent_value"
