import streamlit as st

from app.core.filters import FilterField, apply_filters, render_sidebar_filters
from app.core.loader import load_shared_workbook, select_required_sheets
from app.core.shared_source import (
    get_shared_source_bytes,
    get_shared_source_name,
    get_shared_source_token,
    has_shared_source,
)
from app.dashboards.ad_summary.config import AppConfig
from app.dashboards.ad_summary.metrics import build_period_summary
from app.dashboards.ad_summary.processor import build_ad_summary_dataset
from app.dashboards.ad_summary.ui import render_empty_state, render_summary_table


def main() -> None:
    config = AppConfig()
    st.set_page_config(page_title="广告数据汇总", page_icon="📊", layout="wide")
    st.title("广告数据汇总")
    st.caption("按季度、月、周、日四个维度汇总广告与店铺经营数据。")

    if not has_shared_source():
        st.warning("请先在首页上传共享 Excel 数据源。")
        st.stop()

    st.caption(f"当前共享数据源：`{get_shared_source_name()}`")
    workbook = load_shared_workbook(
        get_shared_source_bytes(),
        get_shared_source_name(),
        get_shared_source_token(),
    )
    tables = select_required_sheets(workbook, config.required_sheets)
    df = build_ad_summary_dataset(tables, config)

    filter_fields = (
        FilterField(config.year_column, group="时间", sort_values=True),
        FilterField(config.month_label_column, group="时间", sort_values=True),
        FilterField(config.week_label_column, group="时间", sort_values=True),
        FilterField(config.quarter_label_column, group="时间", sort_values=True),
        FilterField(config.channel_type_column, group="业务"),
        FilterField(config.brand_column, group="业务"),
        FilterField(config.category_column, group="业务"),
        FilterField(config.product_name_column, label="商品名称", group="业务"),
        FilterField(config.day_label_column, label="Date", group="业务", sort_values=True),
        FilterField(config.plan_aggregate_column, label="计划聚合", group="业务"),
    )
    selections = render_sidebar_filters(df, filter_fields, key_prefix="广告数据汇总")
    filtered_df = apply_filters(df, selections, filter_fields)

    if filtered_df.empty:
        render_empty_state()
        return

    render_summary_table("季度汇总", build_period_summary(filtered_df, "quarter", config), config)
    render_summary_table("月度汇总", build_period_summary(filtered_df, "month", config), config)
    render_summary_table("周度汇总", build_period_summary(filtered_df, "week", config), config)
    render_summary_table("日度汇总", build_period_summary(filtered_df, "day", config), config)


if __name__ == "__main__":
    main()
