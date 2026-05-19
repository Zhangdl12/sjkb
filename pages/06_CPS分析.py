import pandas as pd
import streamlit as st

from app.core.filters import FilterField, render_sidebar_filters
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
from app.dashboards.cps_analysis import ui as cps_ui
from app.dashboards.cps_analysis.config import AppConfig
from app.dashboards.cps_analysis.service import (
    CPS_ANALYSIS_PAYLOAD_CACHE_VERSION,
    CpsAnalysisPayload,
    build_cps_analysis_payload,
    build_filter_fields as service_build_filter_fields,
    build_filter_summary,
    load_cps_analysis_dataset,
    load_cps_analysis_payload,
)


def build_filter_fields(config: AppConfig) -> tuple[FilterField, ...]:
    """构造 CPS 分析侧边栏筛选器。

    Args:
        config: CPS 分析字段配置。

    Returns:
        筛选字段声明元组。
    """
    return service_build_filter_fields(config)


def build_display_tables(
    df: pd.DataFrame,
    config: AppConfig,
) -> CpsAnalysisPayload:
    """生成 CPS 分析展示载荷。

    Args:
        df: 已应用筛选条件的 CPS 分析明细。
        config: CPS 分析字段配置。

    Returns:
        CPS 分析页面最终展示载荷。
    """
    return build_cps_analysis_payload(
        {"dataset": df},
        {},
        build_filter_fields(config),
        config,
    )


def main() -> None:
    """CPS 分析 Streamlit 页面入口。

    Args:
        无。

    Returns:
        None。
    """
    config = AppConfig()
    st.set_page_config(page_title="CPS分析", page_icon="📌", layout="wide")
    st.title("CPS分析")
    st.caption("仅取 CPS 数据源，并通过商品打标把商品编号匹配为商品名称。")

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

    with st.spinner("正在读取 CPS 分析数据，请稍候..."):
        df = load_cps_analysis_dataset(
            source_bytes,
            source_name,
            source_token,
            tag_bytes,
            tag_source_name,
            tag_source_token,
        )

    filter_fields = build_filter_fields(config)
    selections = render_sidebar_filters(df, filter_fields, key_prefix="CPS分析")
    payload = load_cps_analysis_payload(
        source_bytes,
        source_name,
        source_token,
        tag_bytes,
        tag_source_name,
        tag_source_token,
        build_filter_summary(selections),
        CPS_ANALYSIS_PAYLOAD_CACHE_VERSION,
    )
    if payload.tree_df.empty:
        cps_ui.render_empty_state()
        return

    cps_ui.render_cps_tree_table(
        "团长 > 日期 > 产品",
        payload.tree_df,
        "cps_analysis_tree_grid_v1",
    )


if __name__ == "__main__":
    main()
