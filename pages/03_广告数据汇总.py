import streamlit as st
import pandas as pd

from app.core.filters import FilterField, apply_filters, render_sidebar_filters
from app.core.loader import load_shared_workbook, select_required_sheets
from app.core.shared_source import (
    get_shared_source_bytes,
    get_shared_source_name,
    get_shared_source_token,
    has_shared_source,
)
from app.dashboards.ad_summary.config import AppConfig
from app.dashboards.ad_summary import metrics as ad_metrics
from app.dashboards.ad_summary.processor import build_ad_summary_dataset
from app.dashboards.ad_summary import ui as ad_ui


def _build_yoy_selections(
    selections: dict[str, object],
    config: AppConfig,
) -> dict[str, object]:
    yoy_selections = dict(selections)
    selected_year = selections.get(config.year_column)
    previous_year = _resolve_previous_year(selected_year)
    if previous_year is not None:
        yoy_selections[config.year_column] = [previous_year, selected_year]
    extended_day_labels = _extend_day_labels_with_previous_year(
        selections.get(config.day_label_column),
    )
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
    if period == "day":
        return None
    return apply_filters(df, _build_yoy_selections(selections, config), filter_fields)


def _resolve_previous_year(selected_year: object) -> int | None:
    try:
        return int(selected_year) - 1
    except (TypeError, ValueError):
        return None


def _extend_day_labels_with_previous_year(selected_values: object) -> list[object]:
    if selected_values in (None, []):
        return []

    if isinstance(selected_values, list):
        day_labels = selected_values
    else:
        day_labels = [selected_values]

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


def _drop_day_click_yoy_column(
    df: pd.DataFrame,
    period: str,
) -> pd.DataFrame:
    if period != "day":
        return df
    return df.drop(columns=["广告点击季度同比"], errors="ignore")


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
        FilterField(config.channel_type_column, group="业务"),
        FilterField(config.new_channel_column, group="业务"),
        FilterField(config.brand_column, group="业务"),
        FilterField(config.category_column, group="业务"),
        FilterField(config.product_name_column, label="商品名称", group="业务"),
        FilterField(config.day_label_column, label="日期", group="时间", sort_values=True),
        FilterField(config.plan_aggregate_column, label="计划聚合", group="业务"),
    )
    selections = render_sidebar_filters(df, filter_fields, key_prefix="广告数据汇总")
    filtered_df = apply_filters(df, selections, filter_fields)
    shop_metric_selections = {
        column: value
        for column, value in selections.items()
        if column
        not in {
            config.channel_type_column,
            config.new_channel_column,
        }
    }
    shop_metric_df = apply_filters(df, shop_metric_selections, filter_fields)

    if filtered_df.empty:
        ad_ui.render_empty_state()
        return

    for title, period in (
        ("季度汇总", "quarter"),
        ("月度汇总", "month"),
        ("周度汇总", "week"),
        ("日度汇总", "day"),
    ):
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
        ad_ui.render_summary_table(title, summary_df, config, period)
        st.caption(title.replace("汇总", "总计"))
        ad_ui.render_total_table(total_row_df, config, period)


if __name__ == "__main__":
    main()
