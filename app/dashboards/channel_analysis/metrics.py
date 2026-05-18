import pandas as pd

from app.dashboards.channel_analysis.config import AppConfig


def build_period_summary(
    df: pd.DataFrame,
    period: str,
    config: AppConfig,
) -> pd.DataFrame:
    """按周期和新产品渠道生成汇总表。"""
    period_column, sort_columns = resolve_period_columns(period, config)
    grouped_df = _group_metrics(df, period_column, sort_columns, config)
    if grouped_df.empty:
        return pd.DataFrame(columns=config.display_columns)

    grouped_df = grouped_df.sort_values(
        [*sort_columns, config.new_channel_column],
        ascending=True,
    ).reset_index(drop=True)
    result_df = _build_summary_from_grouped(grouped_df, period_column, config)
    result_df["ROI环比"] = _build_roi_change_ratio(
        result_df,
        grouped_df,
        sort_columns,
        config,
    )
    return result_df[config.display_columns]


def build_period_total(
    df: pd.DataFrame,
    period: str,
    config: AppConfig,
) -> pd.DataFrame:
    """生成当前周期表范围内的一行总计。"""
    resolve_period_columns(period, config)
    if df.empty:
        return pd.DataFrame(columns=config.display_columns)

    total_df = _build_single_total(df, config)
    result_df = _build_total_from_grouped(total_df, config)
    return result_df[config.display_columns]


def resolve_period_columns(period: str, config: AppConfig) -> tuple[str, list[str]]:
    mapping = {
        "year": (config.year_column, [config.year_column]),
        "quarter": (config.quarter_label_column, [config.year_column, config.quarter_sort_column]),
        "month": (config.month_label_column, [config.year_column, config.month_sort_column]),
        "week": (config.week_label_column, [config.year_column, config.week_sort_column]),
        "day": (config.day_label_column, [config.date_column]),
    }
    return mapping[period]


def _group_metrics(
    df: pd.DataFrame,
    period_column: str,
    sort_columns: list[str],
    config: AppConfig,
) -> pd.DataFrame:
    group_columns = [*sort_columns, period_column, config.new_channel_column]
    group_columns = list(dict.fromkeys(group_columns))
    metric_columns = [
        config.ad_cost_column,
        config.ad_order_row_column,
        config.ad_gmv_column,
        config.ad_click_column,
        config.ad_impression_column,
        config.ad_new_customer_column,
    ]
    return df.groupby(group_columns, dropna=False, as_index=False)[metric_columns].sum()


def _build_single_total(
    df: pd.DataFrame,
    config: AppConfig,
) -> pd.DataFrame:
    metric_columns = [
        config.ad_cost_column,
        config.ad_order_row_column,
        config.ad_gmv_column,
        config.ad_click_column,
        config.ad_impression_column,
        config.ad_new_customer_column,
    ]
    total_row = {
        column: _numeric(df[column]).sum()
        for column in metric_columns
    }
    return pd.DataFrame([total_row])


def _build_summary_from_grouped(
    grouped_df: pd.DataFrame,
    period_column: str,
    config: AppConfig,
) -> pd.DataFrame:
    period_cost = grouped_df.groupby(period_column, dropna=False)[config.ad_cost_column].transform("sum")
    period_gmv = grouped_df.groupby(period_column, dropna=False)[config.ad_gmv_column].transform("sum")
    return pd.DataFrame(
        {
            config.period_label_column: grouped_df[period_column],
            config.new_channel_column: grouped_df[config.new_channel_column],
            "广告费用": _numeric(grouped_df[config.ad_cost_column]),
            "花费占比%": _safe_series_divide(grouped_df[config.ad_cost_column], period_cost),
            "广告订单行": _numeric(grouped_df[config.ad_order_row_column]),
            "广告GMV": _numeric(grouped_df[config.ad_gmv_column]),
            "广告GMV占比": _safe_series_divide(grouped_df[config.ad_gmv_column], period_gmv),
            "广告ROI": _safe_series_divide(grouped_df[config.ad_gmv_column], grouped_df[config.ad_cost_column]),
            "ROI环比": 0.0,
            "广告CPC": _safe_series_divide(grouped_df[config.ad_cost_column], grouped_df[config.ad_click_column]),
            "广告CVR": _safe_series_divide(grouped_df[config.ad_order_row_column], grouped_df[config.ad_click_column]),
            "广告CTR": _safe_series_divide(grouped_df[config.ad_click_column], grouped_df[config.ad_impression_column]),
            "广告新客": _numeric(grouped_df[config.ad_new_customer_column]),
            "广告新客成本": _safe_series_divide(
                grouped_df[config.ad_cost_column],
                grouped_df[config.ad_new_customer_column],
            ),
        }
    )


def _build_total_from_grouped(
    grouped_df: pd.DataFrame,
    config: AppConfig,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            config.period_label_column: "总计",
            config.new_channel_column: "总计",
            "广告费用": _numeric(grouped_df[config.ad_cost_column]),
            "花费占比%": 1.0,
            "广告订单行": _numeric(grouped_df[config.ad_order_row_column]),
            "广告GMV": _numeric(grouped_df[config.ad_gmv_column]),
            "广告GMV占比": 1.0,
            "广告ROI": _safe_series_divide(grouped_df[config.ad_gmv_column], grouped_df[config.ad_cost_column]),
            "ROI环比": pd.NA,
            "广告CPC": _safe_series_divide(grouped_df[config.ad_cost_column], grouped_df[config.ad_click_column]),
            "广告CVR": _safe_series_divide(grouped_df[config.ad_order_row_column], grouped_df[config.ad_click_column]),
            "广告CTR": _safe_series_divide(grouped_df[config.ad_click_column], grouped_df[config.ad_impression_column]),
            "广告新客": _numeric(grouped_df[config.ad_new_customer_column]),
            "广告新客成本": _safe_series_divide(
                grouped_df[config.ad_cost_column],
                grouped_df[config.ad_new_customer_column],
            ),
        }
    )


def _build_roi_change_ratio(
    result_df: pd.DataFrame,
    grouped_df: pd.DataFrame,
    sort_columns: list[str],
    config: AppConfig,
) -> pd.Series:
    roi_df = result_df[
        [config.period_label_column, config.new_channel_column, "广告ROI"]
    ].copy()
    for sort_column in sort_columns:
        roi_df[sort_column] = grouped_df[sort_column].values
    roi_df = roi_df.sort_values([config.new_channel_column, *sort_columns])
    ratios = roi_df.groupby(config.new_channel_column, dropna=False)["广告ROI"].transform(_change_ratio)
    return ratios.reindex(result_df.index).fillna(0.0)


def _change_ratio(series: pd.Series) -> pd.Series:
    current = _numeric(series)
    previous = current.shift(1)
    valid_previous = previous.where(previous.notna() & previous.ne(0))
    return current.div(valid_previous).sub(1).fillna(0.0)


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype(float).fillna(0.0)


def _safe_series_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    normalized_numerator = _numeric(numerator)
    normalized_denominator = _numeric(denominator)
    valid_denominator = normalized_denominator.where(normalized_denominator.ne(0))
    return normalized_numerator.div(valid_denominator).fillna(0.0)
