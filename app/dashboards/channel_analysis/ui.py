import pandas as pd
import streamlit as st

from app.dashboards.channel_analysis.config import AppConfig


def render_summary_table(title: str, df: pd.DataFrame, config: AppConfig) -> None:
    st.markdown(f"### {title}")
    st.dataframe(
        _build_styler(df),
        width="stretch",
        height=_get_height(df),
        column_config=_get_column_config(config),
    )


def render_total_table(df: pd.DataFrame, config: AppConfig) -> None:
    st.markdown("### 总计")
    st.dataframe(
        _build_styler(df).set_properties(**{"font-weight": "700"}),
        width="stretch",
        height=_get_total_height(df),
        column_config=_get_column_config(config),
    )


def render_empty_state() -> None:
    st.warning("当前筛选条件下无渠道分析数据，请放宽筛选条件。")


def _build_styler(df: pd.DataFrame):
    ratio_columns = {"花费占比%", "广告GMV占比", "ROI环比", "广告CVR", "广告CTR"}
    decimal_columns = {"广告ROI", "广告CPC", "广告新客成本"}
    number_columns = {"广告费用", "广告订单行", "广告GMV", "广告新客"}
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
        .set_properties(
            **{
                # Streamlit 黑夜模式下，未显式设置背景色的 Styler 单元格会继承深色底色。
                # 这里同时固定浅色背景和深色文字，确保普通指标列在明暗主题下都可读。
                "background-color": "#ffffff",
                "color": "#111111",
            }
        )
        .set_properties(
            subset=pd.IndexSlice[:, ["周期", "新产品渠道"]],
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
            ],
            overwrite=False,
        )
    )
    return styler.map(_trend_text_color, subset=pd.IndexSlice[:, ["ROI环比"]])


def _get_column_config(config: AppConfig) -> dict[str, st.column_config.Column]:
    return {
        config.period_label_column: st.column_config.TextColumn("周期", pinned=True),
        config.new_channel_column: st.column_config.TextColumn("新产品渠道", pinned=True),
    }


def _get_height(df: pd.DataFrame) -> int:
    return min(900, max(220, 35 * (len(df) + 1)))


def _get_total_height(df: pd.DataFrame) -> int:
    return min(260, max(76, 35 * (len(df) + 1)))


def _trend_text_color(value: object) -> str:
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
