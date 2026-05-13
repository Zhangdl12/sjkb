import pandas as pd
import streamlit as st

from app.dashboards.ad_summary.config import AppConfig


def render_summary_table(title: str, df: pd.DataFrame, config: AppConfig, period: str) -> None:
    st.markdown(f"### {title}")
    st.dataframe(
        _build_styler(df, config),
        width="stretch",
        height=_get_height(df),
        column_config=_get_column_config(df, config, period),
    )


def render_empty_state() -> None:
    st.warning("当前筛选条件下无广告汇总数据，请放宽筛选条件。")


def render_total_table(df: pd.DataFrame, config: AppConfig, period: str) -> None:
    st.dataframe(
        _build_total_styler(df, config),
        width="stretch",
        height=76,
        column_config=_get_column_config(df, config, period),
    )


def _build_styler(df: pd.DataFrame, config: AppConfig):
    ratio_columns = {
        "广告GMV贡献",
        "费比",
        "店铺完成进度",
        "PV贡献",
        "转化率",
        "消耗环比",
        "投放GMV环比",
        "店铺GMV环比",
        "ROI环比",
        "费比环比",
        "广告点击季度同比",
        config.shop_gmv_ratio_tail_column,
    }
    number_columns = {
        "广告费用",
        "投放GMV",
        "店铺GMV",
        "店铺GMV目标",
        "广告点击",
        "PV",
        config.shop_gmv_tail_column,
    }
    decimal_columns = {"广告ROI", "人均访问数", "人均子订单量", "均单商品数", "商品单价"}
    trend_columns = [
        column for column in ratio_columns
        if ("环比" in column or "同比" in column) and column in df.columns
    ]

    format_map: dict[str, object] = {}
    for column in df.columns:
        if column in ratio_columns:
            format_map[column] = _format_percent
        elif column in decimal_columns:
            format_map[column] = _format_decimal
        elif column in number_columns:
            format_map[column] = _format_number

    styler = (
        df.style.format(format_map, na_rep="None")
        .hide(axis="index")
        .set_properties(**{"color": "#111111"})
        .set_properties(
            subset=pd.IndexSlice[:, [config.period_label_column]],
            **{
                "background-color": "#f3f4f6",
                "color": "#111111",
                "font-weight": "600",
            },
        )
        .set_table_styles(
            [
                {
                    "selector": "th",
                    "props": [
                        ("background-color", "#1f2937"),
                        ("color", "#f9fafb"),
                        ("font-weight", "600"),
                    ],
                },
                {
                    "selector": "th.col_heading.level0.col0",
                    "props": [
                        ("background-color", "#374151"),
                        ("color", "#f9fafb"),
                        ("font-weight", "700"),
                    ],
                },
            ],
            overwrite=False,
        )
    )
    styler = styler.apply(_highlight_sections, axis=0, args=(config,))
    styler = styler.map(_trend_text_color, subset=pd.IndexSlice[:, trend_columns])
    return styler


def _build_total_styler(df: pd.DataFrame, config: AppConfig):
    return _build_styler(df, config).set_properties(**{"font-weight": "700"})


def _highlight_sections(column: pd.Series, config: AppConfig) -> list[str]:
    if column.name in ["广告费用", "投放GMV", "店铺GMV", "广告GMV贡献", "广告ROI", "费比"]:
        return ["background-color: #fff2cc; color: #111111;"] * len(column)
    if column.name in ["消耗环比", "投放GMV环比", "店铺GMV环比", "ROI环比", "费比环比", "店铺GMV目标", "店铺完成进度"]:
        return ["background-color: #d9e2f3; color: #111111;"] * len(column)
    if column.name in [
        "广告点击",
        "广告点击季度同比",
        "PV贡献",
        "PV",
        "人均访问数",
        "转化率",
        "人均子订单量",
        "均单商品数",
        "商品单价",
        config.shop_gmv_tail_column,
        config.shop_gmv_ratio_tail_column,
    ]:
        return ["background-color: #e2f0d9; color: #111111;"] * len(column)
    return [""] * len(column)


def _trend_text_color(value: float) -> str:
    if pd.isna(value):
        return "color: #111111;"
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return "color: #111111;"
    if numeric_value > 0:
        return "color: #008a3d; font-weight: 600;"
    if numeric_value < 0:
        return "color: #c00000; font-weight: 600;"
    return "color: #111111;"


def _get_height(df: pd.DataFrame) -> int:
    return min(900, max(220, 35 * (len(df) + 1)))


def _get_column_config(
    df: pd.DataFrame,
    config: AppConfig,
    period: str,
) -> dict[str, st.column_config.Column]:
    column_config: dict[str, st.column_config.Column] = {}
    if "广告点击季度同比" in df.columns:
        column_config["广告点击季度同比"] = st.column_config.NumberColumn(_get_click_yoy_label(period))
    if config.shop_gmv_tail_column in df.columns:
        column_config[config.shop_gmv_tail_column] = st.column_config.NumberColumn("店铺GMV")
    if config.shop_gmv_ratio_tail_column in df.columns:
        column_config[config.shop_gmv_ratio_tail_column] = st.column_config.NumberColumn("店铺GMV环比")
    return column_config


def _get_click_yoy_label(period: str) -> str:
    label_map = {
        "quarter": "广告点击季度同比",
        "month": "广告点击月度同比",
        "week": "广告点击周度同比",
    }
    return label_map.get(period, "广告点击同比")


def _format_percent(value: object) -> str:
    if pd.isna(value):
        return "None"
    return f"{float(value):.2%}"


def _format_decimal(value: object) -> str:
    if pd.isna(value):
        return "None"
    return f"{float(value):.2f}"


def _format_number(value: object) -> str:
    if pd.isna(value):
        return "None"
    return f"{float(value):,.0f}"
