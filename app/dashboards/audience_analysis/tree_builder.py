"""人群分析树形表数据构造。"""

import pandas as pd

from app.dashboards.audience_analysis import metrics as audience_metrics
from app.dashboards.audience_analysis.config import AppConfig


def build_classification_tree_summary(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """生成人群分类树表，父级节点也带真实汇总指标。

    Args:
        df: 已筛选的人群分析明细。
        config: 人群分析字段配置。

    Returns:
        带 path 列的人群分类树形汇总表。
    """

    if df.empty:
        return pd.DataFrame(columns=[*config.classification_columns, "path"])

    category_df = _build_tree_level_summary(df, [config.audience_category_column], 1, config)
    audience_df = _build_tree_level_summary(
        df,
        [config.audience_category_column, config.audience_name_column],
        2,
        config,
    )
    month_df = _build_tree_level_summary(
        df,
        [
            config.audience_category_column,
            config.audience_name_column,
            config.month_sort_column,
            config.month_label_column,
        ],
        3,
        config,
    )
    tree_df = pd.concat([category_df, audience_df, month_df], ignore_index=True)
    tree_df = tree_df.sort_values(["path", "_tree_depth"]).reset_index(drop=True)
    return tree_df.drop(columns=["_tree_depth", config.month_sort_column], errors="ignore")


def build_time_tree_summary(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """生成人群分类、人群名称、周、日四层时间树表。

    Args:
        df: 已筛选的人群分析明细。
        config: 人群分析字段配置。

    Returns:
        带 path 列的时间渠道树形汇总表。
    """

    if df.empty:
        return pd.DataFrame(columns=[*config.time_columns, "path"])

    category_df = _build_time_tree_level_summary(df, [config.audience_category_column], 1, config)
    audience_df = _build_time_tree_level_summary(
        df,
        [config.audience_category_column, config.audience_name_column],
        2,
        config,
    )
    week_df = _build_time_tree_level_summary(
        df,
        [
            config.audience_category_column,
            config.audience_name_column,
            config.week_sort_column,
            config.week_label_column,
        ],
        3,
        config,
    )
    day_df = _build_time_tree_level_summary(
        df,
        [
            config.audience_category_column,
            config.audience_name_column,
            config.week_sort_column,
            config.date_column,
            config.week_label_column,
            config.day_label_column,
        ],
        4,
        config,
    )
    tree_df = pd.concat([category_df, audience_df, week_df, day_df], ignore_index=True)
    tree_df = tree_df.sort_values(["path", "_tree_depth"]).reset_index(drop=True)
    return tree_df.drop(columns=["_tree_depth", config.week_sort_column, config.date_column], errors="ignore")


def _build_tree_level_summary(
    df: pd.DataFrame,
    group_columns: list[str],
    tree_depth: int,
    config: AppConfig,
) -> pd.DataFrame:
    """按指定人群分类树层级生成汇总行。

    Args:
        df: 已筛选明细。
        group_columns: 当前层级参与聚合的字段。
        tree_depth: 当前树深度。
        config: 人群分析字段配置。

    Returns:
        补齐展示列、path 和树深度的汇总表。
    """

    summary_df = audience_metrics._build_classification_summary(df, group_columns, config)
    for column in [config.audience_category_column, config.audience_name_column, config.month_label_column]:
        if column not in summary_df.columns:
            summary_df[column] = ""
    if config.month_sort_column not in summary_df.columns:
        summary_df[config.month_sort_column] = 0
    summary_df["_tree_depth"] = tree_depth
    summary_df["path"] = summary_df[_path_columns(group_columns, config)].fillna(config.blank_text).astype(str).agg("||".join, axis=1)
    return summary_df[[*config.classification_columns, config.month_sort_column, "path", "_tree_depth"]]


def _build_time_tree_level_summary(
    df: pd.DataFrame,
    group_columns: list[str],
    tree_depth: int,
    config: AppConfig,
) -> pd.DataFrame:
    """按指定时间树层级生成汇总行。

    Args:
        df: 已筛选明细。
        group_columns: 当前层级参与聚合的字段。
        tree_depth: 当前树深度。
        config: 人群分析字段配置。

    Returns:
        补齐展示列、path 和树深度的时间汇总表。
    """

    grouped_df = audience_metrics._group_base_metrics(df, group_columns, config)
    if grouped_df.empty:
        return pd.DataFrame(columns=[*config.time_columns, "path", "_tree_depth"])
    grouped_df = grouped_df.sort_values(group_columns).reset_index(drop=True)
    summary_df = audience_metrics._append_time_ratio_metrics(grouped_df, config)
    for column in config.time_columns:
        if column not in summary_df.columns:
            summary_df[column] = ""
    for column in [config.week_sort_column, config.date_column]:
        if column not in summary_df.columns:
            summary_df[column] = 0 if column == config.week_sort_column else pd.NaT
    summary_df["_tree_depth"] = tree_depth
    summary_df["path"] = summary_df[_time_path_columns(group_columns, config)].fillna(config.blank_text).astype(str).agg("||".join, axis=1)
    return summary_df[[*config.time_columns, config.week_sort_column, config.date_column, "path", "_tree_depth"]]


def _path_columns(group_columns: list[str], config: AppConfig) -> list[str]:
    """返回人群分类树 path 使用的展示维度。

    Args:
        group_columns: 当前聚合维度。
        config: 人群分析字段配置。

    Returns:
        过滤掉排序列后的 path 字段。
    """

    preferred_columns = [config.audience_category_column, config.audience_name_column, config.month_label_column]
    return [column for column in preferred_columns if column in group_columns]


def _time_path_columns(group_columns: list[str], config: AppConfig) -> list[str]:
    """返回时间树 path 使用的展示维度。

    Args:
        group_columns: 当前聚合维度。
        config: 人群分析字段配置。

    Returns:
        过滤掉排序列后的 path 字段。
    """

    preferred_columns = [
        config.audience_category_column,
        config.audience_name_column,
        config.week_label_column,
        config.day_label_column,
    ]
    return [column for column in preferred_columns if column in group_columns]
