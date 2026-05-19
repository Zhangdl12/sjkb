"""渠道分析指标计算。"""
import pandas as pd

from app.dashboards.channel_analysis.config import AppConfig


def build_channel_summary(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """按新产品渠道生成分类汇总表。

    Args:
        df: 已筛选的渠道分析统一明细。
        config: 渠道分析配置。

    Returns:
        新产品渠道维度汇总结果。
    """
    return _build_summary(df, [config.new_channel_column], config)


def build_category_summary(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """按品线分类、商品名称、新产品渠道、月生成层级汇总表。"""
    return _build_summary(
        df,
        [
            config.line_column,
            config.sku_product_name_column,
            config.new_channel_column,
            config.month_sort_column,
            config.month_label_column,
        ],
        config,
    )


def build_time_channel_summary(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """按月、日和新产品渠道生成时间渠道汇总表。

    同一天同一新产品渠道只保留一行，基础指标先求和，再重算比例指标。
    """
    grouped_df = _group_base_metrics(
        df,
        [
            config.month_sort_column,
            config.date_column,
            config.month_label_column,
            config.day_label_column,
            config.new_channel_column,
        ],
        config,
    )
    if grouped_df.empty:
        return pd.DataFrame(columns=config.time_columns)
    grouped_df = grouped_df.sort_values([config.month_sort_column, config.date_column, config.new_channel_column])
    result_df = _append_ratio_metrics(grouped_df, config, total_scope_columns=None)
    return result_df[config.time_columns]


def build_channel_total(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """生成分类汇总总计行。"""
    if df.empty:
        return pd.DataFrame(columns=[config.new_channel_column, *config.summary_columns])
    total_df = _group_base_metrics(df, [], config)
    result_df = _append_ratio_metrics(total_df, config, total_scope_columns=None)
    result_df[config.new_channel_column] = "总计"
    result_df["花费占比%"] = 1.0
    result_df["广告GMV占比"] = 1.0
    result_df["ROI月环比"] = pd.NA
    return result_df[[config.new_channel_column, *config.summary_columns]]


def _build_summary(df: pd.DataFrame, group_columns: list[str], config: AppConfig) -> pd.DataFrame:
    """按指定维度汇总基础指标并追加比例指标。"""
    grouped_df = _group_base_metrics(df, group_columns, config)
    if grouped_df.empty:
        return pd.DataFrame(columns=[*group_columns, *config.summary_columns])
    grouped_df = grouped_df.sort_values(group_columns).reset_index(drop=True)
    result_df = _append_ratio_metrics(grouped_df, config, total_scope_columns=None)
    result_df["ROI月环比"] = _build_month_roi_change(df, group_columns, result_df, config)
    return result_df[[*group_columns, *config.summary_columns]]


def _group_base_metrics(df: pd.DataFrame, group_columns: list[str], config: AppConfig) -> pd.DataFrame:
    """先求和基础指标，后续所有比例都基于这些求和结果重算。"""
    metric_columns = _metric_columns(config)
    if df.empty:
        return pd.DataFrame(columns=[*group_columns, *metric_columns])
    if not group_columns:
        return pd.DataFrame([{column: _numeric(df[column]).sum() for column in metric_columns}])
    return df.groupby(group_columns, dropna=False, as_index=False)[metric_columns].sum()


def _append_ratio_metrics(
    grouped_df: pd.DataFrame,
    config: AppConfig,
    total_scope_columns: list[str] | None,
) -> pd.DataFrame:
    """在基础汇总表上追加所有衍生指标。"""
    result_df = grouped_df.copy()
    if total_scope_columns:
        cost_total = result_df.groupby(total_scope_columns, dropna=False)[config.ad_cost_column].transform("sum")
        gmv_total = result_df.groupby(total_scope_columns, dropna=False)[config.ad_gmv_column].transform("sum")
    else:
        cost_total = pd.Series([_numeric(result_df[config.ad_cost_column]).sum()] * len(result_df), index=result_df.index)
        gmv_total = pd.Series([_numeric(result_df[config.ad_gmv_column]).sum()] * len(result_df), index=result_df.index)

    result_df["花费占比%"] = _safe_series_divide(result_df[config.ad_cost_column], cost_total)
    result_df["广告GMV占比"] = _safe_series_divide(result_df[config.ad_gmv_column], gmv_total)
    result_df["广告ROI"] = _safe_series_divide(result_df[config.ad_gmv_column], result_df[config.ad_cost_column])
    result_df["广告CPC"] = _safe_series_divide(result_df[config.ad_cost_column], result_df[config.ad_click_column])
    result_df["广告CVR"] = _safe_series_divide(result_df[config.ad_order_row_column], result_df[config.ad_click_column])
    result_df["广告CTR"] = _safe_series_divide(result_df[config.ad_click_column], result_df[config.ad_impression_column])
    result_df["广告新客成本"] = _safe_series_divide(result_df[config.ad_cost_column], result_df[config.ad_new_customer_column])
    result_df["广告商品单价"] = _safe_series_divide(result_df[config.ad_gmv_column], result_df[config.ad_order_row_column])
    result_df["广告加购率"] = _safe_series_divide(result_df[config.ad_cart_column], result_df[config.ad_click_column])
    result_df["广告CPA"] = _safe_series_divide(result_df[config.ad_cost_column], result_df[config.ad_order_row_column])
    result_df["广告新客浓度"] = _safe_series_divide(result_df[config.ad_new_customer_column], result_df[config.ad_order_row_column])
    result_df["广告总加购成本"] = _safe_series_divide(result_df[config.ad_cost_column], result_df[config.ad_cart_column])
    result_df["ROI月环比"] = 0.0
    return result_df


def _build_month_roi_change(
    detail_df: pd.DataFrame,
    group_columns: list[str],
    result_df: pd.DataFrame,
    config: AppConfig,
) -> pd.Series:
    """按同一分组计算本月 ROI 相对上月 ROI 的变化。"""
    if config.month_label_column not in detail_df.columns or config.month_sort_column not in detail_df.columns:
        return pd.Series([0.0] * len(result_df), index=result_df.index)

    month_identity_columns = {config.month_sort_column, config.month_label_column}
    comparison_columns = [column for column in group_columns if column not in month_identity_columns]
    month_group_columns = [config.month_sort_column, config.month_label_column, *comparison_columns]
    month_df = _group_base_metrics(detail_df, month_group_columns, config)
    sort_columns = [*comparison_columns, config.month_sort_column] if comparison_columns else [config.month_sort_column]
    month_df = month_df.sort_values(sort_columns).reset_index(drop=True)
    month_df["广告ROI"] = _safe_series_divide(month_df[config.ad_gmv_column], month_df[config.ad_cost_column])
    if comparison_columns:
        month_df["ROI月环比"] = month_df.groupby(comparison_columns, dropna=False)["广告ROI"].transform(_change_ratio)
    else:
        month_df["ROI月环比"] = _change_ratio(month_df["广告ROI"])

    # 分组维度已包含月份时，直接回填每个月自己的月环比；否则沿用原有最新月口径。
    if month_identity_columns.intersection(group_columns):
        source_df = month_df
        preferred_merge_columns = [
            config.month_sort_column,
            config.month_label_column,
            *comparison_columns,
        ]
    else:
        latest_month = _numeric(month_df[config.month_sort_column]).max()
        source_df = month_df[month_df[config.month_sort_column].eq(latest_month)]
        preferred_merge_columns = comparison_columns

    merge_columns = [
        column
        for column in preferred_merge_columns
        if column in result_df.columns and column in source_df.columns
    ]
    if not merge_columns:
        return pd.Series([0.0] * len(result_df), index=result_df.index)
    merged_df = result_df.merge(
        source_df[[*merge_columns, "ROI月环比"]],
        on=merge_columns,
        how="left",
        suffixes=("", "_latest"),
    )
    return merged_df["ROI月环比_latest"].fillna(0.0)


def _change_ratio(series: pd.Series) -> pd.Series:
    """计算当前值相对上一行的变化率。"""
    current = _numeric(series)
    previous = current.shift(1)
    valid_previous = previous.where(previous.notna() & previous.ne(0))
    return current.div(valid_previous).sub(1).fillna(0.0)


def _numeric(series: pd.Series) -> pd.Series:
    """把序列安全转为浮点数。"""
    return pd.to_numeric(series, errors="coerce").astype(float).fillna(0.0)


def _safe_series_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """安全除法，分母为 0 或空时返回 0。"""
    normalized_denominator = _numeric(denominator)
    valid_denominator = normalized_denominator.where(normalized_denominator.ne(0))
    return _numeric(numerator).div(valid_denominator).fillna(0.0)


def _metric_columns(config: AppConfig) -> list[str]:
    """返回参与汇总的基础指标列。"""
    return [
        config.ad_cost_column,
        config.ad_impression_column,
        config.ad_click_column,
        config.ad_order_row_column,
        config.ad_gmv_column,
        config.ad_new_customer_column,
        config.ad_cart_column,
    ]
