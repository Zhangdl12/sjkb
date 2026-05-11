import pandas as pd

from app.dashboards.ad_summary.config import AppConfig


def build_period_summary(df: pd.DataFrame, period: str, config: AppConfig) -> pd.DataFrame:
    period_column, sort_column = _resolve_period_columns(period, config)
    grouped_df = (
        df.groupby([config.year_column, period_column, sort_column], dropna=False, as_index=False)
        .agg(
            {
                config.ad_cost_column: "sum",
                config.ad_gmv_column: "sum",
                config.shop_gmv_column: "sum",
                config.shop_target_column: "sum",
                config.ad_click_column: "sum",
                config.shop_pv_column: "sum",
                config.shop_visitor_column: "sum",
                config.shop_buyer_column: "sum",
                config.shop_order_count_column: "sum",
                config.shop_item_count_column: "sum",
            }
        )
        .sort_values([config.year_column, sort_column], ascending=[True, True])
        .reset_index(drop=True)
    )

    shop_gmv_series = _normalize_numeric_series(grouped_df[config.shop_gmv_column])
    shop_gmv_ratio_series = _build_change_ratio(shop_gmv_series)

    summary_df = pd.DataFrame(
        {
            config.period_label_column: grouped_df[period_column],
            "广告费用": _normalize_numeric_series(grouped_df[config.ad_cost_column]),
            "投放GMV": _normalize_numeric_series(grouped_df[config.ad_gmv_column]),
            "店铺GMV": shop_gmv_series,
            "广告GMV贡献": _safe_series_divide(
                grouped_df[config.ad_gmv_column],
                grouped_df[config.shop_gmv_column],
            ),
            "广告ROI": _safe_series_divide(
                grouped_df[config.ad_gmv_column],
                grouped_df[config.ad_cost_column],
            ),
            "费比": _safe_series_divide(
                grouped_df[config.ad_cost_column],
                grouped_df[config.shop_gmv_column],
            ),
            "店铺GMV目标": _normalize_numeric_series(grouped_df[config.shop_target_column]),
            "店铺完成进度": _safe_series_divide(
                grouped_df[config.shop_gmv_column],
                grouped_df[config.shop_target_column],
            ),
            "广告点击": _normalize_numeric_series(grouped_df[config.ad_click_column]),
            "广告点击季度同比": 0.0,
            "PV贡献": _safe_series_divide(
                grouped_df[config.ad_click_column],
                grouped_df[config.shop_pv_column],
            ),
            "PV": _normalize_numeric_series(grouped_df[config.shop_pv_column]),
            "人均访问数": _safe_series_divide(
                grouped_df[config.shop_pv_column],
                grouped_df[config.shop_visitor_column],
            ),
            "转化率": _safe_series_divide(
                grouped_df[config.shop_buyer_column],
                grouped_df[config.shop_visitor_column],
            ),
            "人均子订单量": _safe_series_divide(
                grouped_df[config.shop_order_count_column],
                grouped_df[config.shop_buyer_column],
            ),
            "均单商品数": _safe_series_divide(
                grouped_df[config.shop_item_count_column],
                grouped_df[config.shop_order_count_column],
            ),
            "商品单价": _safe_series_divide(
                grouped_df[config.shop_gmv_column],
                grouped_df[config.shop_item_count_column],
            ),
            config.shop_gmv_tail_column: shop_gmv_series,
            config.shop_gmv_ratio_tail_column: shop_gmv_ratio_series,
        }
    )

    summary_df["消耗环比"] = _build_change_ratio(summary_df["广告费用"])
    summary_df["投放GMV环比"] = _build_change_ratio(summary_df["投放GMV"])
    summary_df["店铺GMV环比"] = shop_gmv_ratio_series
    summary_df["ROI环比"] = _build_change_ratio(summary_df["广告ROI"])
    summary_df["费比环比"] = _build_change_ratio(summary_df["费比"])
    summary_df["广告点击季度同比"] = _build_yoy_ratio(
        grouped_df,
        value_column=config.ad_click_column,
        period_column=period_column,
        sort_column=sort_column,
        config=config,
    )

    summary_df["_year"] = grouped_df[config.year_column]
    summary_df["_sort"] = grouped_df[sort_column]
    summary_df = summary_df.sort_values(["_year", "_sort"], ascending=[False, True]).reset_index(drop=True)
    return summary_df[config.display_columns]


def _resolve_period_columns(period: str, config: AppConfig) -> tuple[str, str]:
    mapping = {
        "quarter": (config.quarter_label_column, config.quarter_sort_column),
        "month": (config.month_label_column, config.month_sort_column),
        "week": (config.week_label_column, config.week_sort_column),
        "day": (config.day_label_column, config.date_column),
    }
    return mapping[period]


def _normalize_numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype(float)


def _safe_series_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    normalized_numerator = _normalize_numeric_series(numerator)
    normalized_denominator = _normalize_numeric_series(denominator)
    valid_denominator = normalized_denominator.where(
        normalized_denominator.notna() & normalized_denominator.ne(0)
    )
    return normalized_numerator.div(valid_denominator).fillna(0.0)


def _build_change_ratio(series: pd.Series) -> pd.Series:
    normalized_series = _normalize_numeric_series(series)
    previous = normalized_series.shift(1)
    valid_previous = previous.where(previous.notna() & previous.ne(0))
    return normalized_series.div(valid_previous).sub(1).fillna(0.0)


def _build_yoy_ratio(
    grouped_df: pd.DataFrame,
    value_column: str,
    period_column: str,
    sort_column: str,
    config: AppConfig,
) -> pd.Series:
    compare_df = grouped_df[
        [config.year_column, period_column, sort_column, value_column]
    ].copy()
    compare_df[value_column] = _normalize_numeric_series(compare_df[value_column])
    compare_df["上一年"] = compare_df[config.year_column] + 1

    result_df = grouped_df.merge(
        compare_df,
        left_on=[config.year_column, period_column, sort_column],
        right_on=["上一年", period_column, sort_column],
        how="left",
        suffixes=("", "_去年"),
    )
    return _build_ratio_from_previous(
        result_df[value_column],
        result_df[f"{value_column}_去年"],
    )


def _build_ratio_from_previous(current: pd.Series, previous: pd.Series) -> pd.Series:
    normalized_current = _normalize_numeric_series(current)
    normalized_previous = _normalize_numeric_series(previous)
    valid_previous = normalized_previous.where(
        normalized_previous.notna() & normalized_previous.ne(0)
    )
    return normalized_current.div(valid_previous).sub(1).fillna(0.0)
