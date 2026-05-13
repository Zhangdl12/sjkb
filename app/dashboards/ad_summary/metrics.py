import pandas as pd

from app.dashboards.ad_summary.config import AppConfig


TOTAL_LABEL = "总计"


def build_period_summary(
    df: pd.DataFrame,
    period: str,
    config: AppConfig,
    shop_metric_df: pd.DataFrame | None = None,
    yoy_source_df: pd.DataFrame | None = None,
    include_click_yoy: bool = True,
) -> pd.DataFrame:
    period_column, sort_column = _resolve_period_columns(period, config)
    shop_source_df = _build_shop_metric_scope_df(shop_metric_df if shop_metric_df is not None else df, config)
    ad_grouped_df = _group_period_metrics(
        df,
        period_column,
        sort_column,
        config,
        [
            config.ad_cost_column,
            config.ad_gmv_column,
            config.ad_click_column,
        ],
    )
    shop_grouped_df = _group_period_metrics(
        shop_source_df,
        period_column,
        sort_column,
        config,
        [
            config.shop_gmv_column,
            config.shop_target_column,
            config.shop_pv_column,
            config.shop_visitor_column,
            config.shop_buyer_column,
            config.shop_order_count_column,
            config.shop_item_count_column,
        ],
    )
    grouped_df = ad_grouped_df.merge(
        shop_grouped_df,
        on=[config.year_column, period_column, sort_column],
        how="outer",
    ).fillna(0)
    grouped_df = grouped_df.sort_values([config.year_column, sort_column], ascending=[True, True]).reset_index(drop=True)

    yoy_grouped_df = None
    if include_click_yoy:
        yoy_grouped_df = _group_period_metrics(
            yoy_source_df if yoy_source_df is not None else df,
            period_column,
            sort_column,
            config,
            [config.ad_click_column],
        )
        yoy_grouped_df = yoy_grouped_df.sort_values(
            [config.year_column, sort_column],
            ascending=[True, True],
        ).reset_index(drop=True)

    return _build_summary_from_aggregated(
        grouped_df,
        period_column,
        sort_column,
        config,
        yoy_grouped_df=yoy_grouped_df,
    )


def filter_detail_by_summary_scope(
    detail_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    period: str,
    config: AppConfig,
) -> pd.DataFrame:
    period_column, _ = _resolve_period_columns(period, config)
    period_values = summary_df.loc[
        summary_df[config.period_label_column] != TOTAL_LABEL,
        config.period_label_column,
    ].dropna()
    return detail_df[detail_df[period_column].isin(period_values)].copy()


def build_total_row_for_scope(
    scoped_detail_df: pd.DataFrame,
    config: AppConfig,
    shop_metric_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    scoped_shop_df = _build_shop_metric_scope_df(
        shop_metric_df if shop_metric_df is not None else scoped_detail_df,
        config,
    )
    total_row = {
        config.period_label_column: TOTAL_LABEL,
        "广告费用": _sum_column(scoped_detail_df, config.ad_cost_column),
        "投放GMV": _sum_column(scoped_detail_df, config.ad_gmv_column),
        "店铺GMV": _sum_column(scoped_shop_df, config.shop_gmv_column),
        "广告GMV贡献": _safe_scalar_divide(
            _sum_column(scoped_detail_df, config.ad_gmv_column),
            _sum_column(scoped_shop_df, config.shop_gmv_column),
        ),
        "广告ROI": _safe_scalar_divide(
            _sum_column(scoped_detail_df, config.ad_gmv_column),
            _sum_column(scoped_detail_df, config.ad_cost_column),
        ),
        "费比": _safe_scalar_divide(
            _sum_column(scoped_detail_df, config.ad_cost_column),
            _sum_column(scoped_shop_df, config.shop_gmv_column),
        ),
        "消耗环比": pd.NA,
        "投放GMV环比": pd.NA,
        "店铺GMV环比": pd.NA,
        "ROI环比": pd.NA,
        "费比环比": pd.NA,
        "店铺GMV目标": _sum_column(scoped_shop_df, config.shop_target_column),
        "店铺完成进度": _safe_scalar_divide(
            _sum_column(scoped_shop_df, config.shop_gmv_column),
            _sum_column(scoped_shop_df, config.shop_target_column),
        ),
        "广告点击": _sum_column(scoped_detail_df, config.ad_click_column),
        "广告点击季度同比": pd.NA,
        "PV贡献": _safe_scalar_divide(
            _sum_column(scoped_detail_df, config.ad_click_column),
            _sum_column(scoped_shop_df, config.shop_pv_column),
        ),
        "PV": _sum_column(scoped_shop_df, config.shop_pv_column),
        "人均访问数": _safe_scalar_divide(
            _sum_column(scoped_shop_df, config.shop_pv_column),
            _sum_column(scoped_shop_df, config.shop_visitor_column),
        ),
        "转化率": _safe_scalar_divide(
            _sum_column(scoped_shop_df, config.shop_buyer_column),
            _sum_column(scoped_shop_df, config.shop_visitor_column),
        ),
        "人均子订单量": _safe_scalar_divide(
            _sum_column(scoped_shop_df, config.shop_order_count_column),
            _sum_column(scoped_shop_df, config.shop_buyer_column),
        ),
        "均单商品数": _safe_scalar_divide(
            _sum_column(scoped_shop_df, config.shop_item_count_column),
            _sum_column(scoped_shop_df, config.shop_order_count_column),
        ),
        "商品单价": _safe_scalar_divide(
            _sum_column(scoped_shop_df, config.shop_gmv_column),
            _sum_column(scoped_shop_df, config.shop_item_count_column),
        ),
    }
    total_row[config.shop_gmv_tail_column] = total_row["店铺GMV"]
    total_row[config.shop_gmv_ratio_tail_column] = pd.NA
    return pd.DataFrame([total_row], columns=config.display_columns)


def build_summary_and_total(
    detail_df: pd.DataFrame,
    period: str,
    config: AppConfig,
    shop_metric_df: pd.DataFrame | None = None,
    yoy_source_df: pd.DataFrame | None = None,
    include_click_yoy: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_df = build_period_summary(
        detail_df,
        period,
        config,
        shop_metric_df,
        yoy_source_df=yoy_source_df,
        include_click_yoy=include_click_yoy,
    )
    scoped_detail_df = filter_detail_by_summary_scope(detail_df, summary_df, period, config)
    scoped_shop_df = filter_detail_by_summary_scope(
        shop_metric_df if shop_metric_df is not None else detail_df,
        summary_df,
        period,
        config,
    )
    total_row_df = build_total_row_for_scope(scoped_detail_df, config, scoped_shop_df)
    return summary_df, total_row_df


def _group_period_metrics(
    df: pd.DataFrame,
    period_column: str,
    sort_column: str,
    config: AppConfig,
    metric_columns: list[str],
) -> pd.DataFrame:
    return (
        df.groupby([config.year_column, period_column, sort_column], dropna=False, as_index=False)[metric_columns]
        .sum()
    )


def _build_shop_metric_scope_df(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    dedupe_columns = [config.date_column, config.ad_sku_id_column]
    if any(column not in df.columns for column in dedupe_columns):
        return df.copy()
    return df.sort_values(dedupe_columns).drop_duplicates(subset=dedupe_columns, keep="first").copy()


def _build_summary_from_aggregated(
    grouped_df: pd.DataFrame,
    period_column: str,
    sort_column: str,
    config: AppConfig,
    yoy_grouped_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    shop_gmv_series = _normalize_numeric_series(grouped_df[config.shop_gmv_column])
    shop_gmv_ratio_series = _build_change_ratio(shop_gmv_series)
    if yoy_grouped_df is None:
        yoy_ratio_series = pd.Series([0.0] * len(grouped_df), index=grouped_df.index, dtype=float)
    else:
        yoy_ratio_series = _build_click_yoy_series(
            grouped_df,
            yoy_grouped_df,
            period_column,
            sort_column,
            config,
        )

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
            "广告点击季度同比": yoy_ratio_series,
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

    summary_df["_year"] = grouped_df[config.year_column]
    summary_df["_sort"] = grouped_df[sort_column]
    summary_df = summary_df.sort_values(["_year", "_sort"], ascending=[False, True]).reset_index(drop=True)
    return summary_df[config.display_columns]


def _build_click_yoy_series(
    grouped_df: pd.DataFrame,
    yoy_grouped_df: pd.DataFrame,
    period_column: str,
    sort_column: str,
    config: AppConfig,
) -> pd.Series:
    yoy_compare_df = yoy_grouped_df[
        [config.year_column, period_column, sort_column, config.ad_click_column]
    ].copy()
    yoy_compare_df["广告点击季度同比"] = _build_yoy_ratio(
        yoy_grouped_df,
        value_column=config.ad_click_column,
        period_column=period_column,
        sort_column=sort_column,
        config=config,
    )
    merged_df = grouped_df.merge(
        yoy_compare_df[
            [config.year_column, period_column, sort_column, "广告点击季度同比"]
        ],
        on=[config.year_column, period_column, sort_column],
        how="left",
    )
    return _normalize_numeric_series(merged_df["广告点击季度同比"]).fillna(0.0)


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


def _sum_column(df: pd.DataFrame, column: str) -> float:
    return float(_normalize_numeric_series(df[column]).sum())


def _safe_scalar_divide(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return 0.0
    return float(numerator / denominator)
