"""多页面看板的通用运行器。"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st

from app.core.filters import FilterField, apply_filters, render_sidebar_filters
from app.core.loader import load_shared_workbook, select_required_sheets
from app.core.shared_source import (
    get_shared_source_bytes,
    get_shared_source_name,
    get_shared_source_token,
    has_shared_source,
)


@dataclass(frozen=True)
class DashboardPageConfig:
    """单个看板页面的配置契约。"""

    page_title: str
    page_icon: str
    page_header: str
    page_description: str
    required_sheets: Mapping[str, str] | Sequence[str]
    filter_fields: Sequence[FilterField]
    default_pivot_group_by: Sequence[str]
    context: Any
    build_dataset: Callable[[dict[str, pd.DataFrame], Any], pd.DataFrame]
    build_metrics: Callable[[pd.DataFrame, Any], Any]
    build_pivot_table: Callable[[pd.DataFrame, list[str], Any], pd.DataFrame]
    render_summary: Callable[[Any], None]
    render_pivot_table: Callable[[pd.DataFrame], None]
    render_detail_section: Callable[[pd.DataFrame], None]
    render_empty_state: Callable[[], None]


def run_dashboard_page(config: DashboardPageConfig) -> None:
    """基于共享上传工作簿运行一个看板页面。"""

    st.set_page_config(
        page_title=config.page_title,
        page_icon=config.page_icon,
        layout="wide",
    )
    st.title(config.page_header)
    st.caption(config.page_description)

    if not has_shared_source():
        st.warning("请先在首页上传共享数据源，然后再进入当前看板。")
        st.stop()

    source_name = get_shared_source_name()
    source_bytes = get_shared_source_bytes()
    source_token = get_shared_source_token()

    st.caption(f"当前共享数据源：`{source_name}`")

    try:
        workbook = load_shared_workbook(source_bytes, source_name, source_token)
        tables = select_required_sheets(workbook, config.required_sheets)
        df = config.build_dataset(tables, config.context)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    selections = render_sidebar_filters(
        df,
        tuple(config.filter_fields),
        key_prefix=config.page_title,
    )
    filtered_df = apply_filters(df, selections, tuple(config.filter_fields))

    if filtered_df.empty:
        config.render_empty_state()
        return

    summary_metrics = config.build_metrics(filtered_df, config.context)
    pivot_df = config.build_pivot_table(
        filtered_df,
        list(config.default_pivot_group_by),
        config.context,
    )

    config.render_summary(summary_metrics)
    config.render_pivot_table(pivot_df)
    config.render_detail_section(filtered_df)
