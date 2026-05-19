import pandas as pd
import streamlit as st

from app.core.filters import FilterField, apply_filters, render_sidebar_filters
from app.core.page_state import render_page_radio
from app.core.session_loader import load_current_source_sheets, load_current_tag_sheets
from app.core.shared_source import (
    get_shared_source_name,
    get_tag_source_name,
    has_shared_source,
    has_tag_source,
)
from app.dashboards.ad_summary import metrics as ad_metrics
from app.dashboards.ad_summary import ui as ad_ui
from app.dashboards.ad_summary.config import AppConfig
from app.dashboards.ad_summary.processor import build_ad_summary_dataset


def _build_yoy_selections(selections: dict[str, object], config: AppConfig) -> dict[str, object]:
    """把当前筛选条件扩展为“当前年 + 上一年”的同比计算范围。

    Args:
        selections: 侧边栏当前筛选结果。
        config: 广告汇总配置。

    Returns:
        用于同比计算的筛选结果。
    """
    yoy_selections = dict(selections)
    selected_year = selections.get(config.year_column)
    previous_year = _resolve_previous_year(selected_year)
    if previous_year is not None:
        yoy_selections[config.year_column] = [previous_year, selected_year]
    extended_day_labels = _extend_day_labels_with_previous_year(selections.get(config.day_label_column))
    if extended_day_labels:
        yoy_selections[config.day_label_column] = extended_day_labels
    else:
        yoy_selections.pop(config.day_label_column, None)
    return yoy_selections


def _build_period_yoy_source_df(
    df: pd.DataFrame,
    selections: dict[str, object],
    filter_fields: tuple[FilterField, ...],
    config: AppConfig,
    period: str,
) -> pd.DataFrame | None:
    """生成当前周期的同比来源数据，日维度不计算同比。"""
    if period == "day":
        return None
    return apply_filters(df, _build_yoy_selections(selections, config), filter_fields)


def _resolve_previous_year(selected_year: object) -> int | None:
    """解析上一年，无法解析时返回 None。"""
    try:
        return int(selected_year) - 1
    except (TypeError, ValueError):
        return None


def _extend_day_labels_with_previous_year(selected_values: object) -> list[object]:
    """日筛选存在时，同时补充上一年同月同日。"""
    if selected_values in (None, []):
        return []
    day_labels = selected_values if isinstance(selected_values, list) else [selected_values]
    extended_labels: list[object] = []
    for label in day_labels:
        extended_labels.append(label)
        try:
            date_value = pd.to_datetime(label)
        except (TypeError, ValueError):
            continue
        previous_label = f"{date_value.year - 1}/{date_value.month}/{date_value.day}"
        if previous_label not in extended_labels:
            extended_labels.append(previous_label)
    return extended_labels


def _drop_day_click_yoy_column(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """日维度不展示点击同比列。"""
    if period != "day":
        return df
    return df.drop(columns=["广告点击季度同比"], errors="ignore")


def get_period_options() -> tuple[tuple[str, str], ...]:
    """返回广告汇总页面支持的周期选项。"""
    return (
        ("季度汇总", "quarter"),
        ("月度汇总", "month"),
        ("周度汇总", "week"),
        ("日度汇总", "day"),
    )


def _resolve_selected_period(selected_title: str, period_options: tuple[tuple[str, str], ...]) -> str:
    """根据页面展示名称解析内部周期标识。"""
    return dict(period_options)[selected_title]


def build_filter_fields(config: AppConfig) -> tuple[FilterField, ...]:
    """构造广告汇总侧边栏筛选器。"""
    return (
        FilterField(config.year_column, group="时间", sort_values=True, control="single_select", default_latest=True),
        FilterField(config.quarter_label_column, group="时间", sort_values=True),
        FilterField(config.month_label_column, group="时间", sort_values=True),
        FilterField(config.week_label_column, group="时间", sort_values=True),
        FilterField(config.day_label_column, label="日期", group="时间", sort_values=True),
        FilterField(config.channel_type_column, group="业务"),
        FilterField(config.new_channel_column, group="业务"),
        FilterField(config.plan_aggregate_column, label="计划聚合", group="业务"),
        FilterField(config.brand_column, label="投放品牌", group="业务"),
        FilterField(config.category_column, label="新分类", group="业务"),
        FilterField(config.product_name_column, label="商品名称", group="业务"),
    )


def build_shop_metric_selections(selections: dict[str, object], config: AppConfig) -> dict[str, object]:
    """生成店铺指标专用筛选条件。

    店铺商智销售没有广告渠道维度。这里保留时间、商品、品牌等条件，
    但移除计划聚合、新产品渠道和渠道类型，避免店铺 GMV 被广告维度切片误过滤。
    """
    ignored_columns = {
        config.channel_type_column,
        config.new_channel_column,
        config.plan_aggregate_column,
    }
    return {column: value for column, value in selections.items() if column not in ignored_columns}


def main() -> None:
    config = AppConfig()
    st.set_page_config(page_title="广告数据汇总", page_icon="📊", layout="wide")
    st.title("广告数据汇总")
    st.caption("按季度、月、周、日四个维度汇总广告与店铺经营数据。")

    if not has_shared_source():
        st.warning("请先在首页上传共享 Excel 数据源。")
        st.stop()
    if not has_tag_source():
        st.warning("请先在首页上传打标文件。")
        st.stop()

    source_name = get_shared_source_name()
    tag_source_name = get_tag_source_name()
    st.caption(f"当前共享数据源：`{source_name}`")
    st.caption(f"当前打标文件：`{tag_source_name}`")

    source_tables = load_current_source_sheets(config.required_sheets, config.source_usecols)
    tag_tables = load_current_tag_sheets(config.required_tag_sheets, config.tag_usecols)
    df = build_ad_summary_dataset({**source_tables, **tag_tables}, config)

    filter_fields = build_filter_fields(config)
    selections = render_sidebar_filters(df, filter_fields, key_prefix="广告数据汇总")
    filtered_df = apply_filters(df, selections, filter_fields)
    shop_metric_df = apply_filters(df, build_shop_metric_selections(selections, config), filter_fields)

    if filtered_df.empty:
        ad_ui.render_empty_state()
        return

    period_options = get_period_options()
    selected_title = render_page_radio(
        "选择汇总周期",
        [title for title, _ in period_options],
        key="ad_summary_period_radio",
        default=period_options[0][0],
        horizontal=True,
    )
    period = _resolve_selected_period(selected_title, period_options)

    period_yoy_df = _build_period_yoy_source_df(df, selections, filter_fields, config, period)
    summary_df, total_row_df = ad_metrics.build_summary_and_total(
        filtered_df,
        period,
        config,
        shop_metric_df=shop_metric_df,
        yoy_source_df=period_yoy_df,
        include_click_yoy=period != "day",
    )
    summary_df = _drop_day_click_yoy_column(summary_df, period)
    total_row_df = _drop_day_click_yoy_column(total_row_df, period)
    ad_ui.render_summary_table(selected_title, summary_df, config, period)
    st.caption(selected_title.replace("汇总", "总计"))
    ad_ui.render_total_table(total_row_df, config, period)


if __name__ == "__main__":
    main()
