"""人群分析指标计算。"""

import pandas as pd

from app.dashboards.audience_analysis.config import AppConfig


def build_classification_summary(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """按人群分类和人群名称生成汇总表。

    Args:
        df: 已筛选的人群分析明细。
        config: 人群分析字段配置。

    Returns:
        人群分类汇总结果。
    """

    group_columns = [config.audience_category_column, config.audience_name_column]
    result_df = _build_classification_summary(df, group_columns, config)
    if config.month_label_column not in result_df.columns:
        result_df[config.month_label_column] = ""
    return result_df[config.classification_columns]


def build_time_summary(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """按人群分类、人群名称、周和日生成时间渠道表。

    Args:
        df: 已筛选的人群分析明细。
        config: 人群分析字段配置。

    Returns:
        时间渠道视图需要的汇总结果。
    """

    group_columns = [
        config.audience_category_column,
        config.audience_name_column,
        config.week_sort_column,
        config.date_column,
        config.week_label_column,
        config.day_label_column,
    ]
    grouped_df = _group_base_metrics(df, group_columns, config)
    if grouped_df.empty:
        return pd.DataFrame(columns=config.time_columns)
    grouped_df = grouped_df.sort_values(
        [
            config.audience_category_column,
            config.audience_name_column,
            config.week_sort_column,
            config.date_column,
        ]
    ).reset_index(drop=True)
    result_df = _append_time_ratio_metrics(grouped_df, config)
    return result_df[config.time_columns]


def build_total(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """生成当前筛选范围下的总计行。

    Args:
        df: 已筛选的人群分析明细。
        config: 人群分析字段配置。

    Returns:
        单行总计表，所有比率按总量重算。
    """

    if df.empty:
        return pd.DataFrame(columns=config.total_columns)
    total_df = _group_base_metrics(df, [], config)
    result_df = _append_classification_ratio_metrics(total_df, config)
    result_df[config.audience_category_column] = "总计"
    result_df[config.audience_name_column] = ""
    result_df[config.month_label_column] = ""
    result_df["花费占比%"] = 1.0
    return result_df[config.total_columns]


def _build_classification_summary(
    df: pd.DataFrame,
    group_columns: list[str],
    config: AppConfig,
) -> pd.DataFrame:
    """按指定维度生成人群指标汇总。

    Args:
        df: 已筛选的人群分析明细。
        group_columns: 聚合维度。
        config: 人群分析字段配置。

    Returns:
        已追加 ROI、CPC、CTR 和占比的汇总表。
    """

    grouped_df = _group_base_metrics(df, group_columns, config)
    if grouped_df.empty:
        return pd.DataFrame(columns=[*group_columns, *config.classification_columns])
    grouped_df = grouped_df.sort_values([config.ad_cost_column], ascending=False).reset_index(drop=True)
    return _append_classification_ratio_metrics(grouped_df, config)


def _group_base_metrics(df: pd.DataFrame, group_columns: list[str], config: AppConfig) -> pd.DataFrame:
    """先求和基础指标，后续所有比率都从这里重算。

    Args:
        df: 人群分析明细。
        group_columns: 分组维度；为空时生成全局总计。
        config: 人群分析字段配置。

    Returns:
        基础指标求和后的 DataFrame。
    """

    metric_columns = _metric_columns(config)
    if df.empty:
        return pd.DataFrame(columns=[*group_columns, *metric_columns])
    if not group_columns:
        return pd.DataFrame([{column: _numeric(df[column]).sum() for column in metric_columns}])
    return df.groupby(group_columns, dropna=False, as_index=False)[metric_columns].sum()


def _append_classification_ratio_metrics(grouped_df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """为人群分类汇总表追加派生指标。

    Args:
        grouped_df: 基础指标已经求和的汇总表。
        config: 人群分析字段配置。

    Returns:
        带花费占比、ROI-kw、CPC-kw、CTR-kw 等字段的 DataFrame。
    """

    result_df = grouped_df.copy()
    cost_total = _numeric(result_df[config.ad_cost_column]).sum()
    result_df["花费占比%"] = _safe_series_divide(result_df[config.ad_cost_column], pd.Series([cost_total] * len(result_df), index=result_df.index))
    result_df["ROI-kw"] = _safe_series_divide(result_df[config.ad_gmv_column], result_df[config.ad_cost_column])
    result_df["CPC-kw"] = _safe_series_divide(result_df[config.ad_cost_column], result_df[config.ad_click_column])
    result_df["CTR-kw"] = _safe_series_divide(result_df[config.ad_click_column], result_df[config.ad_impression_column])
    result_df["点击数"] = result_df[config.ad_click_column]
    result_df["总订单金额"] = result_df[config.ad_gmv_column]
    return result_df


def _append_time_ratio_metrics(grouped_df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """为时间渠道表追加派生指标。

    Args:
        grouped_df: 基础指标已经求和的时间汇总表。
        config: 人群分析字段配置。

    Returns:
        带 CPC、CTR、CVR、ROI、占比等字段的 DataFrame。
    """

    result_df = grouped_df.copy()
    cost_total = _numeric(result_df[config.ad_cost_column]).sum()
    gmv_total = _numeric(result_df[config.ad_gmv_column]).sum()
    result_df["广告商品单价"] = _safe_series_divide(result_df[config.ad_gmv_column], result_df[config.ad_order_row_column])
    result_df["广告CPC"] = _safe_series_divide(result_df[config.ad_cost_column], result_df[config.ad_click_column])
    result_df["广告CTR"] = _safe_series_divide(result_df[config.ad_click_column], result_df[config.ad_impression_column])
    result_df["广告CVR"] = _safe_series_divide(result_df[config.ad_order_row_column], result_df[config.ad_click_column])
    result_df["广告ROI"] = _safe_series_divide(result_df[config.ad_gmv_column], result_df[config.ad_cost_column])
    result_df["广告加购率"] = _safe_series_divide(result_df[config.ad_cart_column], result_df[config.ad_click_column])
    result_df["广告CPA"] = _safe_series_divide(result_df[config.ad_cost_column], result_df[config.ad_order_row_column])
    result_df["广告新客成本"] = _safe_series_divide(result_df[config.ad_cost_column], result_df[config.ad_new_customer_column])
    result_df["广告总加购成本"] = _safe_series_divide(result_df[config.ad_cost_column], result_df[config.ad_cart_column])
    result_df["花费占比%"] = _safe_series_divide(result_df[config.ad_cost_column], pd.Series([cost_total] * len(result_df), index=result_df.index))
    result_df["广告GMV占比"] = _safe_series_divide(result_df[config.ad_gmv_column], pd.Series([gmv_total] * len(result_df), index=result_df.index))
    return result_df


def _numeric(series: pd.Series) -> pd.Series:
    """把序列安全转为浮点数。

    Args:
        series: 待转换序列。

    Returns:
        无法转换的值填 0 后的浮点序列。
    """

    return pd.to_numeric(series, errors="coerce").astype(float).fillna(0.0)


def _safe_series_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """安全除法，分母为 0 或空时返回 0。

    Args:
        numerator: 分子序列。
        denominator: 分母序列。

    Returns:
        除法结果序列。
    """

    normalized_denominator = _numeric(denominator)
    valid_denominator = normalized_denominator.where(normalized_denominator.ne(0))
    return _numeric(numerator).div(valid_denominator).fillna(0.0)


def _metric_columns(config: AppConfig) -> list[str]:
    """返回参与汇总的基础指标列。

    Args:
        config: 人群分析字段配置。

    Returns:
        基础指标字段名列表。
    """

    return [
        config.ad_cost_column,
        config.ad_impression_column,
        config.ad_click_column,
        config.ad_order_row_column,
        config.ad_gmv_column,
        config.ad_new_customer_column,
        config.ad_cart_column,
    ]
