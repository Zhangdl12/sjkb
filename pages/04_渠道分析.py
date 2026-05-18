import pandas as pd
import streamlit as st

from app.core.filters import FilterField, apply_filters, render_sidebar_filters
from app.core.session_loader import load_current_source_sheets
from app.core.shared_source import get_shared_source_name, has_shared_source
from app.dashboards.channel_analysis.config import AppConfig
from app.dashboards.channel_analysis import metrics as channel_metrics
from app.dashboards.channel_analysis import ui as channel_ui
from app.dashboards.channel_analysis.processor import build_channel_analysis_dataset


def build_filter_fields(config: AppConfig) -> tuple[FilterField, ...]:
    return (
        FilterField(
            config.year_column,
            group="时间",
            sort_values=True,
            control="single_select",
            default_latest=True,
        ),
        FilterField(config.quarter_label_column, group="时间", sort_values=True),
        FilterField(config.month_label_column, group="时间", sort_values=True),
        FilterField(config.week_label_column, group="时间", sort_values=True),
        FilterField(config.day_label_column, label="日期", group="时间", sort_values=True),
        FilterField(config.channel_type_column, group="业务"),
        FilterField(config.new_channel_column, group="业务"),
        FilterField(config.plan_aggregate_column, label="计划聚合", group="业务"),
        FilterField(config.brand_column, group="业务"),
        FilterField(config.category_column, group="业务"),
        FilterField(config.sku_product_name_column, label="商品名称", group="业务"),
    )


def get_period_tabs(config: AppConfig) -> tuple[tuple[str, str], ...]:
    return config.period_tabs


def build_period_tables(
    df: pd.DataFrame,
    period: str,
    config: AppConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """生成指定周期的渠道汇总表和总计表。

    Args:
        df: 已经过侧边栏条件筛选后的渠道分析明细数据。
        period: 周期类型，支持 year、quarter、month、week、day。
        config: 渠道分析配置对象，提供字段名和展示列顺序。

    Returns:
        二元组，第一项为按周期和新产品渠道拆分的汇总表，第二项为当前筛选范围的总计表。
    """
    # 汇总表用于展示每个周期下各新产品渠道的指标拆分。
    summary_df = channel_metrics.build_period_summary(df, period, config)
    # 总计表用于展示当前筛选范围整体指标，避免用户需要手动汇总页面明细。
    total_df = channel_metrics.build_period_total(df, period, config)
    return summary_df, total_df


def main() -> None:
    config = AppConfig()
    st.set_page_config(page_title="渠道分析", page_icon="📈", layout="wide")
    st.title("渠道分析")
    st.caption("按年、季度、月、周、日切换查看新产品渠道表现。")

    if not has_shared_source():
        st.warning("请先在首页上传共享 Excel 数据源。")
        st.stop()

    source_name = get_shared_source_name()
    st.caption(f"当前共享数据源：`{source_name}`")
    # 只读取渠道分析需要的 3 张工作表和必要列，避免解析整本 Excel。
    tables = load_current_source_sheets(
        config.required_sheets,
        config.source_usecols,
    )
    df = build_channel_analysis_dataset(tables, config) # 构建数据集

    filter_fields = build_filter_fields(config)
    selections = render_sidebar_filters(df, filter_fields, key_prefix="渠道分析")
    filtered_df = apply_filters(df, selections, filter_fields)

    if filtered_df.empty:
        channel_ui.render_empty_state()
        return

    # st.tabs 会一次性执行全部周期的计算。单选后只计算当前周期，减少页面等待时间。
    period_tabs = get_period_tabs(config)
    selected_label = st.radio(
        "选择渠道分析周期",
        [label for label, _ in period_tabs],
        horizontal=True,
    )
    period = resolve_selected_period(selected_label, period_tabs)
    summary_df, total_df = build_period_tables(filtered_df, period, config)
    if summary_df.empty:
        channel_ui.render_empty_state()
        return
    channel_ui.render_summary_table(f"{selected_label}渠道分析", summary_df, config)
    st.caption(f"{selected_label}总计")
    channel_ui.render_total_table(total_df, config)


def resolve_selected_period(
    selected_label: str,
    period_tabs: tuple[tuple[str, str], ...],
) -> str:
    """根据页面选择的周期名称解析内部周期标识。

    Args:
        selected_label: 用户在单选控件中选择的周期名称
        period_tabs: 周期显示名称和内部标识的二元组集合

    Returns:
        内部周期标识，例如 month、week
    """
    return dict(period_tabs)[selected_label]


if __name__ == "__main__":
    main()
