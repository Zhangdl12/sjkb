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
from app.dashboards.channel_analysis import ui as channel_ui
from app.dashboards.channel_analysis.config import AppConfig
from app.dashboards.channel_analysis.service import (
    CHANNEL_ANALYSIS_PAYLOAD_CACHE_VERSION,
    ChannelAnalysisPayload,
    build_channel_analysis_payload,
    build_filter_summary,
    load_channel_analysis_dataset,
    load_channel_analysis_payload,
)


def build_filter_fields(config: AppConfig) -> tuple[FilterField, ...]:
    """构造渠道分析侧边栏筛选器。"""
    return (
        FilterField(config.year_column, group="时间", sort_values=True, control="single_select", default_latest=True),
        FilterField(config.quarter_label_column, group="时间", sort_values=True),
        FilterField(config.month_label_column, group="时间", sort_values=True),
        FilterField(config.week_label_column, group="时间", sort_values=True),
        FilterField(config.day_label_column, label="日期", group="时间", sort_values=True),
        FilterField(config.channel_type_column, group="业务"),
        FilterField(config.new_channel_column, group="业务"),
        FilterField(config.plan_aggregate_column, label="计划聚合", group="业务"),
        FilterField(config.brand_column, group="业务"),
        FilterField(config.line_column, group="业务"),
        FilterField(config.sku_product_name_column, label="商品名称", group="业务"),
    )


def build_display_tables(
    df: pd.DataFrame,
    config: AppConfig,
) -> ChannelAnalysisPayload:
    """生成分类汇总视图的展示载荷。

    Args:
        df: 已应用筛选条件的渠道分析明细。
        config: 渠道分析配置。

    Returns:
        分类汇总视图的最终表载荷。该函数保留给测试和旧调用方使用。
    """
    return build_channel_analysis_payload(
        {"dataset": df},
        {},
        build_filter_fields(config),
        "分类汇总",
        config,
    )


def main() -> None:
    config = AppConfig()
    st.set_page_config(page_title="渠道分析", page_icon="📈", layout="wide")
    st.title("渠道分析")
    st.caption("按渠道打标和商品打标汇总广告渠道表现。")

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

    with st.spinner("正在读取并归一化渠道分析数据，请稍候..."):
        df = load_channel_analysis_dataset(
            source_bytes,
            source_name,
            source_token,
            tag_bytes,
            tag_source_name,
            tag_source_token,
        )

    filter_fields = build_filter_fields(config)
    selections = render_sidebar_filters(df, filter_fields, key_prefix="渠道分析")
    view_type = render_page_radio(
        "选择渠道分析视图",
        ["分类汇总", "时间渠道"],
        key="channel_analysis_view_radio",
        default="分类汇总",
        horizontal=True,
        label_visibility="collapsed",
    )
    payload = load_channel_analysis_payload(
        source_bytes,
        source_name,
        source_token,
        tag_bytes,
        tag_source_name,
        tag_source_token,
        build_filter_summary(selections),
        view_type,
        CHANNEL_ANALYSIS_PAYLOAD_CACHE_VERSION,
    )
    if _payload_is_empty(payload, view_type):
        channel_ui.render_empty_state()
        return

    if view_type == "分类汇总":
        channel_ui.render_channel_tree_table(
            "新产品渠道 > 月",
            payload.channel_df,
            config,
            "channel_analysis_channel_tree_grid_v6",
        )
        channel_ui.render_category_tree_table(
            "品线分类 > 商品名称 > 新产品渠道 > 月",
            payload.category_df,
            config,
            "channel_analysis_category_tree_grid_v5",
        )
        channel_ui.render_total_table(payload.total_df, config)
    else:
        channel_ui.render_time_tree_table("月 / 日 / 新产品渠道", payload.time_df, config, "channel_analysis_time_tree_grid_v3")


def _payload_is_empty(payload: ChannelAnalysisPayload, view_type: str) -> bool:
    """判断当前视图载荷是否为空。

    Args:
        payload: 服务层返回的最终表载荷。
        view_type: 当前用户选择的视图。

    Returns:
        当前视图没有任何可渲染数据时返回 True。
    """
    if view_type == "分类汇总":
        return payload.channel_df.empty and payload.category_df.empty and payload.total_df.empty
    return payload.time_df.empty


if __name__ == "__main__":
    main()
