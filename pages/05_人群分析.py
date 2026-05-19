import pandas as pd
import streamlit as st

from app.core.filters import FilterField, render_sidebar_filters
from app.core.page_state import render_page_radio
from app.core.shared_source import (
    get_shared_source_bytes,
    get_shared_source_name,
    get_shared_source_token,
    get_tag_source_bytes,
    get_tag_source_name,
    get_tag_source_token,
    has_shared_source,
    has_tag_source,
)
from app.dashboards.audience_analysis import ui as audience_ui
from app.dashboards.audience_analysis.config import AppConfig
from app.dashboards.audience_analysis.service import (
    AUDIENCE_ANALYSIS_PAYLOAD_CACHE_VERSION,
    AudienceAnalysisPayload,
    build_audience_analysis_payload,
    build_filter_fields as service_build_filter_fields,
    build_filter_summary,
    load_audience_analysis_dataset,
    load_audience_analysis_payload,
)


def build_filter_fields(config: AppConfig, df: pd.DataFrame | None = None) -> tuple[FilterField, ...]:
    """构造人群分析侧边栏筛选器。

    Args:
        config: 人群分析字段配置。
        df: 可选人群分析明细，用于隐藏没有有效值的店铺特殊字段。

    Returns:
        筛选字段声明元组。
    """

    return service_build_filter_fields(config, df)


def build_display_tables(df: pd.DataFrame, config: AppConfig) -> AudienceAnalysisPayload:
    """生成人群分类视图的展示载荷。

    Args:
        df: 已应用筛选条件的人群分析明细。
        config: 人群分析字段配置。

    Returns:
        人群分类视图展示载荷。
    """

    return build_audience_analysis_payload(
        {"dataset": df},
        {},
        build_filter_fields(config),
        "人群分类",
        config,
    )


def main() -> None:
    """人群分析 Streamlit 页面入口。

    Args:
        无。

    Returns:
        None。
    """

    config = AppConfig()
    st.set_page_config(page_title="人群分析", page_icon="📊", layout="wide")
    st.title("人群分析")
    st.caption("取人群数据源，并通过人群、渠道和商品打标展示人群投放表现。")

    if not has_shared_source():
        st.warning("请先在首页上传共享 Excel 数据源。")
        st.stop()
    if not has_tag_source():
        st.warning("请先在首页上传打标文件。")
        st.stop()

    source_name = get_shared_source_name() or ""
    tag_source_name = get_tag_source_name() or ""
    source_bytes = get_shared_source_bytes() or b""
    tag_bytes = get_tag_source_bytes() or b""
    source_token = get_shared_source_token() or ""
    tag_source_token = get_tag_source_token() or ""
    st.caption(f"当前共享数据源：`{source_name}`")
    st.caption(f"当前打标文件：`{tag_source_name}`")

    with st.spinner("正在读取人群分析数据，请稍候..."):
        df = load_audience_analysis_dataset(
            source_bytes,
            source_name,
            source_token,
            tag_bytes,
            tag_source_name,
            tag_source_token,
        )

    filter_fields = build_filter_fields(config, df)
    selections = render_sidebar_filters(df, filter_fields, key_prefix="人群分析")
    view_type = render_page_radio(
        "选择人群分析视图",
        ["人群分类", "时间渠道"],
        key="audience_analysis_view_radio",
        default="人群分类",
        horizontal=True,
        label_visibility="collapsed",
    )
    payload = load_audience_analysis_payload(
        source_bytes,
        source_name,
        source_token,
        tag_bytes,
        tag_source_name,
        tag_source_token,
        build_filter_summary(selections),
        view_type,
        AUDIENCE_ANALYSIS_PAYLOAD_CACHE_VERSION,
    )
    if _payload_is_empty(payload, view_type):
        audience_ui.render_empty_state()
        return

    if view_type == "人群分类":
        audience_ui.render_classification_table(
            "人群分类 > 人群名称 > 月",
            payload.classification_df,
            "audience_analysis_classification_tree_grid_v2_month",
        )
        audience_ui.render_total_table(payload.total_df)
    else:
        audience_ui.render_time_table(
            "人群分类 > 人群名称 > 周 > 日",
            payload.time_df,
            "audience_analysis_time_tree_grid",
        )


def _payload_is_empty(payload: AudienceAnalysisPayload, view_type: str) -> bool:
    """判断当前视图载荷是否为空。

    Args:
        payload: 服务层返回的最终展示载荷。
        view_type: 当前用户选择的视图。

    Returns:
        当前视图没有任何可展示数据时返回 True。
    """

    if view_type == "人群分类":
        return payload.classification_df.empty and payload.total_df.empty
    return payload.time_df.empty


if __name__ == "__main__":
    main()
