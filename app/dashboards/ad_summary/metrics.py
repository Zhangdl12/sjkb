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
    """按指定周期生成广告汇总表。

    Args:
        df: 已应用广告侧筛选的统一明细数据。
        period: 周期类型，支持 quarter、month、week、day。
        config: 广告汇总配置。
        shop_metric_df: 店铺指标专用筛选范围，用于忽略渠道等广告维度。
        yoy_source_df: 点击同比计算范围，通常包含当前年和上一年。
        include_click_yoy: 是否计算并保留点击同比列。

    Returns:
        周期汇总结果，列顺序与 config.display_columns 保持一致。
    """
    period_column, sort_column = _resolve_period_columns(period, config)
    shop_source_df = _build_shop_metric_scope_df(shop_metric_df if shop_metric_df is not None else df, config)
    ad_grouped_df = _group_period_metrics(
        df,
        period_column,
        sort_column,
        config,
        [config.ad_cost_column, config.ad_gmv_column, config.ad_click_column],
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
            config.shop_item_count_column,
        ],
    )
    grouped_df = ad_grouped_df.merge(
        shop_grouped_df,
        on=[config.year_column, period_column, sort_column],
        how="outer",
    ).fillna(0)
    if grouped_df.empty:
        return pd.DataFrame(columns=config.display_columns)

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
    return _build_summary_from_aggregated(grouped_df, period_column, sort_column, config, yoy_grouped_df)


def filter_detail_by_summary_scope(
    detail_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    period: str,
    config: AppConfig,
) -> pd.DataFrame:
    """根据当前周期汇总表保留总计需要覆盖的明细范围。

    Args:
        detail_df: 原始筛选后的明细表。
        summary_df: 周期汇总表。
        period: 当前周期类型。
        config: 广告汇总配置。

    Returns:
        只包含当前汇总表周期范围内的明细数据。
    """
    if summary_df.empty:
        return detail_df.iloc[0:0].copy()
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
    """按当前筛选范围生成总计行。

    Args:
        scoped_detail_df: 当前周期表覆盖范围内的广告明细。
        config: 广告汇总配置。
        shop_metric_df: 店铺指标专用范围。

    Returns:
        单行总计 DataFrame。
    """
    shop_df = _build_shop_metric_scope_df(shop_metric_df if shop_metric_df is not None else scoped_detail_df, config)
    ad_cost = _sum_column(scoped_detail_df, config.ad_cost_column)
    ad_gmv = _sum_column(scoped_detail_df, config.ad_gmv_column)
    ad_click = _sum_column(scoped_detail_df, config.ad_click_column)
    shop_gmv = _sum_column(shop_df, config.shop_gmv_column)
    shop_target = _sum_column(shop_df, config.shop_target_column)
    shop_pv = _sum_column(shop_df, config.shop_pv_column)
    shop_visitor = _sum_column(shop_df, config.shop_visitor_column)
    shop_buyer = _sum_column(shop_df, config.shop_buyer_column)
    shop_item_count = _sum_column(shop_df, config.shop_item_count_column)

    total_row = {
        config.period_label_column: TOTAL_LABEL,
        "广告费用": ad_cost,
        "投放GMV": ad_gmv,
        "店铺GMV": shop_gmv,
        "广告GMV贡献": _safe_scalar_divide(ad_gmv, shop_gmv),
        "广告ROI": _safe_scalar_divide(ad_gmv, ad_cost),
        "费比": _safe_scalar_divide(ad_cost, shop_gmv),
        "消耗环比": pd.NA,
        "投放GMV环比": pd.NA,
        "店铺GMV环比": pd.NA,
        "ROI环比": pd.NA,
        "费比环比": pd.NA,
        "店铺GMV目标": shop_target,
        "店铺完成进度": _safe_scalar_divide(shop_gmv, shop_target),
        "广告点击": ad_click,
        "广告点击季度同比": pd.NA,
        "PV贡献": _safe_scalar_divide(ad_click, shop_pv),
        "PV": shop_pv,
        "店铺转化率": _safe_scalar_divide(shop_buyer, shop_visitor),
        "商品单价": _safe_scalar_divide(shop_gmv, shop_item_count),
        config.shop_gmv_tail_column: shop_gmv,
        config.shop_gmv_ratio_tail_column: pd.NA,
    }
    return pd.DataFrame([total_row], columns=config.display_columns)


def build_summary_and_total(
    detail_df: pd.DataFrame,
    period: str,
    config: AppConfig,
    shop_metric_df: pd.DataFrame | None = None,
    yoy_source_df: pd.DataFrame | None = None,
    include_click_yoy: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """同时生成周期汇总表和总计表。"""
    summary_df = build_period_summary(detail_df, period, config, shop_metric_df, yoy_source_df, include_click_yoy)
    scoped_detail_df = filter_detail_by_summary_scope(detail_df, summary_df, period, config)
    scoped_shop_df = filter_detail_by_summary_scope(shop_metric_df if shop_metric_df is not None else detail_df, summary_df, period, config)
    return summary_df, build_total_row_for_scope(scoped_detail_df, config, scoped_shop_df)


def _group_period_metrics(
    df: pd.DataFrame,
    period_column: str,
    sort_column: str,
    config: AppConfig,
    metric_columns: list[str],
) -> pd.DataFrame:
    """按年和周期汇总指定基础指标。"""
    group_columns = [config.year_column, period_column, sort_column]
    return df.groupby(group_columns, dropna=False, as_index=False)[metric_columns].sum()


def _build_shop_metric_scope_df(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """提取店铺指标行，确保店铺指标不被广告来源行重复或污染。"""
    if config.source_type_column not in df.columns:
        return df.copy()
    return df[df[config.source_type_column] == config.shop_source_type].copy()


def _build_summary_from_aggregated(
    grouped_df: pd.DataFrame,
    period_column: str,
    sort_column: str,
    config: AppConfig,
    yoy_grouped_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """把基础指标汇总表转换成最终展示指标表。"""
    shop_gmv = _numeric(grouped_df[config.shop_gmv_column])
    shop_gmv_ratio = _build_change_ratio(shop_gmv)
    yoy_ratio = pd.Series([0.0] * len(grouped_df), index=grouped_df.index, dtype=float)
    if yoy_grouped_df is not None:
        yoy_ratio = _build_click_yoy_series(grouped_df, yoy_grouped_df, period_column, sort_column, config)

    summary_df = pd.DataFrame(
        {
            config.period_label_column: grouped_df[period_column],
            "广告费用": _numeric(grouped_df[config.ad_cost_column]),
            "投放GMV": _numeric(grouped_df[config.ad_gmv_column]),
            "店铺GMV": shop_gmv,
            "广告GMV贡献": _safe_series_divide(grouped_df[config.ad_gmv_column], grouped_df[config.shop_gmv_column]),
            "广告ROI": _safe_series_divide(grouped_df[config.ad_gmv_column], grouped_df[config.ad_cost_column]),
            "费比": _safe_series_divide(grouped_df[config.ad_cost_column], grouped_df[config.shop_gmv_column]),
            "店铺GMV目标": _numeric(grouped_df[config.shop_target_column]),
            "店铺完成进度": _safe_series_divide(grouped_df[config.shop_gmv_column], grouped_df[config.shop_target_column]),
            "广告点击": _numeric(grouped_df[config.ad_click_column]),
            "广告点击季度同比": yoy_ratio,
            "PV贡献": _safe_series_divide(grouped_df[config.ad_click_column], grouped_df[config.shop_pv_column]),
            "PV": _numeric(grouped_df[config.shop_pv_column]),
            "店铺转化率": _safe_series_divide(grouped_df[config.shop_buyer_column], grouped_df[config.shop_visitor_column]),
            "商品单价": _safe_series_divide(grouped_df[config.shop_gmv_column], grouped_df[config.shop_item_count_column]),
            config.shop_gmv_tail_column: shop_gmv,
            config.shop_gmv_ratio_tail_column: shop_gmv_ratio,
        }
    )
    summary_df["消耗环比"] = _build_change_ratio(summary_df["广告费用"])
    summary_df["投放GMV环比"] = _build_change_ratio(summary_df["投放GMV"])
    summary_df["店铺GMV环比"] = shop_gmv_ratio
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
    """按同周期上一年点击量计算同比。"""
    yoy_df = yoy_grouped_df[[config.year_column, period_column, sort_column, config.ad_click_column]].copy()
    yoy_df["广告点击季度同比"] = _build_yoy_ratio(yoy_grouped_df, config.ad_click_column, period_column, sort_column, config)
    merged_df = grouped_df.merge(
        yoy_df[[config.year_column, period_column, sort_column, "广告点击季度同比"]],
        on=[config.year_column, period_column, sort_column],
        how="left",
    )
    return _numeric(merged_df["广告点击季度同比"]).fillna(0.0)


def _resolve_period_columns(period: str, config: AppConfig) -> tuple[str, str]:
    """根据周期标识返回周期标签列和排序列。"""
    return {
        "quarter": (config.quarter_label_column, config.quarter_sort_column),
        "month": (config.month_label_column, config.month_sort_column),
        "week": (config.week_label_column, config.week_sort_column),
        "day": (config.day_label_column, config.date_column),
    }[period]


def _build_yoy_ratio(grouped_df: pd.DataFrame, value_column: str, period_column: str, sort_column: str, config: AppConfig) -> pd.Series:
    """计算同周期上一年的同比变化。"""
    compare_df = grouped_df[[config.year_column, period_column, sort_column, value_column]].copy()
    compare_df[value_column] = _numeric(compare_df[value_column])
    compare_df["上一年"] = compare_df[config.year_column] + 1
    result_df = grouped_df.merge(
        compare_df,
        left_on=[config.year_column, period_column, sort_column],
        right_on=["上一年", period_column, sort_column],
        how="left",
        suffixes=("", "_去年"),
    )
    return _build_ratio_from_previous(result_df[value_column], result_df[f"{value_column}_去年"])


def _build_change_ratio(series: pd.Series) -> pd.Series:
    """计算当前值相对上一行的环比。"""
    current = pd.to_numeric(series, errors="coerce").astype(float)
    return _build_ratio_from_previous(current, current.shift(1))


def _build_ratio_from_previous(current: pd.Series, previous: pd.Series) -> pd.Series:
    """按 current / previous - 1 计算变化率，分母无效时返回 0。"""
    current_numeric = pd.to_numeric(current, errors="coerce").astype(float)
    previous_numeric = pd.to_numeric(previous, errors="coerce").astype(float)
    valid_previous = previous_numeric.where(previous_numeric.notna() & previous_numeric.ne(0))
    return current_numeric.div(valid_previous).sub(1).fillna(0.0)


def _numeric(series: pd.Series) -> pd.Series:
    """把任意序列安全转换成浮点数。"""
    return pd.to_numeric(series, errors="coerce").astype(float).fillna(0.0)


def _safe_series_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """序列安全除法，分母为 0 或空时返回 0。"""
    valid_denominator = _numeric(denominator).where(_numeric(denominator).ne(0))
    return _numeric(numerator).div(valid_denominator).fillna(0.0)


def _sum_column(df: pd.DataFrame, column: str) -> float:
    """对指定列安全求和。"""
    return float(_numeric(df[column]).sum()) if column in df.columns else 0.0


def _safe_scalar_divide(numerator: float, denominator: float) -> float:
    """标量安全除法，分母为 0 或空时返回 0。"""
    if denominator in (0, 0.0) or pd.isna(denominator):
        return 0.0
    return float(numerator / denominator)
