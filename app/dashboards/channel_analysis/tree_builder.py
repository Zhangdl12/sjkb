"""渠道分析分类树表构造函数。

本模块专门把筛选后的渠道分析明细加工成 AgGrid treeData 需要的四层 path 表。
父级节点也在后端显式计算指标，避免前端自动补空分组行导致页面显示 0。
"""
import pandas as pd

from app.dashboards.channel_analysis import metrics as channel_metrics
from app.dashboards.channel_analysis.config import AppConfig


def build_channel_tree_summary(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """生成带月度下钻的新产品渠道树表。

    Args:
        df: 已筛选的渠道分析统一明细。
        config: 渠道分析配置。

    Returns:
        两层树表 DataFrame。第一层为新产品渠道汇总，第二层为该渠道下的月份；
        ROI 月环比只在月份层展示，渠道父级置空避免被误读。
    """
    if df.empty:
        return pd.DataFrame(columns=[*_channel_dimension_columns(config), *config.summary_columns, "path"])

    # 渠道父级用于看整体表现，月层用于查看同一渠道跨月份的 ROI 变化。
    channel_df = _build_channel_tree_level_summary(
        df,
        [config.new_channel_column],
        1,
        config,
    )
    month_df = _build_channel_tree_level_summary(
        df,
        [config.new_channel_column, config.month_sort_column, config.month_label_column],
        2,
        config,
    )
    tree_df = pd.concat([channel_df, month_df], ignore_index=True)
    tree_df = tree_df.sort_values([config.new_channel_column, "_month_sort", "path", "_tree_depth"]).reset_index(drop=True)
    return tree_df.drop(columns=["_tree_depth", "_month_sort"], errors="ignore")


def build_category_tree_summary(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """生成带父级汇总数据的分类树表。

    Args:
        df: 已筛选的渠道分析统一明细。
        config: 渠道分析配置。

    Returns:
        四层树表 DataFrame。品线分类、商品名称、新产品渠道和月每个层级都有显式
        汇总行，避免 AgGrid 自动生成的空父级节点显示 0。
    """
    if df.empty:
        return pd.DataFrame(columns=[*_dimension_columns(config), *config.summary_columns, "path"])

    # 复用现有汇总公式分别计算四层，父级 ROI 月环比保持为空，仅月份叶子节点展示该指标。
    line_df = _build_tree_level_summary(
        df,
        [config.line_column],
        1,
        config,
    )
    product_df = _build_tree_level_summary(
        df,
        [config.line_column, config.sku_product_name_column],
        2,
        config,
    )
    channel_df = _build_tree_level_summary(
        df,
        [config.line_column, config.sku_product_name_column, config.new_channel_column],
        3,
        config,
    )
    month_df = _build_tree_level_summary(
        df,
        [
            config.line_column,
            config.sku_product_name_column,
            config.new_channel_column,
            config.month_sort_column,
            config.month_label_column,
        ],
        4,
        config,
    )
    tree_df = pd.concat([line_df, product_df, channel_df, month_df], ignore_index=True)
    tree_df = tree_df.sort_values(
        [
            config.line_column,
            config.sku_product_name_column,
            config.new_channel_column,
            "_month_sort",
            "path",
            "_tree_depth",
        ]
    ).reset_index(drop=True)
    return tree_df.drop(columns=["_tree_depth", "_month_sort"], errors="ignore")


def build_time_tree_summary(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """生成带父级汇总数据的时间渠道树表。

    Args:
        df: 已筛选的渠道分析统一明细。
        config: 渠道分析配置。

    Returns:
        三层树表 DataFrame。月、日和新产品渠道每个层级都有显式汇总行，
        path 结构为“月||日||新产品渠道”。
    """
    if df.empty:
        return pd.DataFrame(columns=[*_time_dimension_columns(config), *config.time_columns[3:], "path"])

    month_df = _build_time_tree_level_summary(
        df,
        [config.month_sort_column, config.month_label_column],
        1,
        config,
    )
    day_df = _build_time_tree_level_summary(
        df,
        [
            config.month_sort_column,
            config.date_column,
            config.month_label_column,
            config.day_label_column,
        ],
        2,
        config,
    )
    channel_df = _build_time_tree_level_summary(
        df,
        [
            config.month_sort_column,
            config.date_column,
            config.month_label_column,
            config.day_label_column,
            config.new_channel_column,
        ],
        3,
        config,
    )
    tree_df = pd.concat([month_df, day_df, channel_df], ignore_index=True)
    tree_df = tree_df.sort_values(
        [config.month_sort_column, config.date_column, "path", "_tree_depth"]
    ).reset_index(drop=True)
    return tree_df.drop(columns=["_tree_depth", config.month_sort_column, config.date_column], errors="ignore")


def add_category_tree_path(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """为已有分类汇总表追加 AgGrid 树形表 path 列。

    Args:
        df: 品线分类、商品名称、新产品渠道、月四层汇总结果。
        config: 渠道分析配置，提供四层维度列名。

    Returns:
        带 path 列的新 DataFrame，path 结构为“品线分类||商品名称||新产品渠道||月”。
    """
    result_df = df.copy()
    path_columns = _dimension_columns(config)
    if result_df.empty:
        result_df["path"] = pd.Series(dtype="string")
        return result_df
    # AgGrid 的 getDataPath 会按 || 拆分 path，因此这里统一转为字符串并补空值。
    result_df["path"] = result_df[path_columns].fillna(config.unknown_text).astype(str).agg("||".join, axis=1)
    return result_df


def _build_tree_level_summary(
    df: pd.DataFrame,
    group_columns: list[str],
    tree_depth: int,
    config: AppConfig,
) -> pd.DataFrame:
    """按指定树层级生成汇总行并补齐 path。

    Args:
        df: 已筛选的渠道分析统一明细。
        group_columns: 当前层级参与汇总的维度列。
        tree_depth: 当前树深度，品线为 1、商品为 2、渠道为 3、月为 4。
        config: 渠道分析配置。

    Returns:
        补齐四层维度列、path 和排序深度的汇总表。
    """
    # 调用 metrics 的统一汇总实现，避免父级节点和原叶子节点出现公式差异。
    summary_df = channel_metrics._build_summary(df, group_columns, config)
    for column in _dimension_columns(config):
        if column not in summary_df.columns:
            summary_df[column] = ""
    summary_df["_tree_depth"] = tree_depth
    summary_df["_month_sort"] = summary_df.get(config.month_sort_column, 0)
    if tree_depth < 4:
        # ROI 月环比只有“月”节点才有明确语义，父级汇总行置空避免被误读。
        summary_df["ROI月环比"] = pd.NA
    # 月排序值只用于排序，不能进入 path；AgGrid 树路径只保留用户可见的中文维度。
    path_columns = _existing_category_path_columns(group_columns, config)
    summary_df["path"] = summary_df[path_columns].fillna(config.unknown_text).astype(str).agg("||".join, axis=1)
    return summary_df[[*_dimension_columns(config), *config.summary_columns, "path", "_tree_depth", "_month_sort"]]


def _build_channel_tree_level_summary(
    df: pd.DataFrame,
    group_columns: list[str],
    tree_depth: int,
    config: AppConfig,
) -> pd.DataFrame:
    """按指定渠道树层级生成汇总行并补齐 path。

    Args:
        df: 已筛选的渠道分析统一明细。
        group_columns: 当前层级参与汇总的维度列。
        tree_depth: 当前树深度，渠道为 1、月为 2。
        config: 渠道分析配置。

    Returns:
        补齐渠道、月、path 和排序深度的汇总表。
    """
    # 统一复用指标汇总函数，确保渠道父级和月份子级的基础指标计算口径一致。
    summary_df = channel_metrics._build_summary(df, group_columns, config)
    for column in _channel_dimension_columns(config):
        if column not in summary_df.columns:
            summary_df[column] = ""
    summary_df["_tree_depth"] = tree_depth
    summary_df["_month_sort"] = summary_df.get(config.month_sort_column, 0)
    if tree_depth < 2:
        # ROI 月环比只有“月”节点才有明确语义，渠道父级汇总行置空。
        summary_df["ROI月环比"] = pd.NA
    path_columns = _existing_channel_path_columns(group_columns, config)
    summary_df["path"] = summary_df[path_columns].fillna(config.unknown_text).astype(str).agg("||".join, axis=1)
    return summary_df[[*_channel_dimension_columns(config), *config.summary_columns, "path", "_tree_depth", "_month_sort"]]


def _build_time_tree_level_summary(
    df: pd.DataFrame,
    group_columns: list[str],
    tree_depth: int,
    config: AppConfig,
) -> pd.DataFrame:
    """按指定时间树层级生成汇总行并补齐 path。"""
    summary_df = channel_metrics._group_base_metrics(df, group_columns, config)
    if summary_df.empty:
        return pd.DataFrame(
            columns=[
                config.month_sort_column,
                config.date_column,
                *_time_dimension_columns(config),
                *config.time_columns[3:],
                "path",
                "_tree_depth",
            ]
        )
    summary_df = summary_df.sort_values(group_columns).reset_index(drop=True)
    summary_df = channel_metrics._append_ratio_metrics(summary_df, config, total_scope_columns=None)
    if config.month_sort_column not in summary_df.columns:
        summary_df[config.month_sort_column] = 0
    if config.date_column not in summary_df.columns:
        summary_df[config.date_column] = pd.NaT
    for column in _time_dimension_columns(config):
        if column not in summary_df.columns:
            summary_df[column] = ""
    summary_df["_tree_depth"] = tree_depth
    summary_df["path"] = summary_df[_existing_path_columns(group_columns, config)].fillna(config.unknown_text).astype(str).agg("||".join, axis=1)
    return summary_df[
        [
            config.month_sort_column,
            config.date_column,
            *_time_dimension_columns(config),
            *config.time_columns[3:],
            "path",
            "_tree_depth",
        ]
    ]


def _dimension_columns(config: AppConfig) -> list[str]:
    """返回分类树表固定使用的四层维度列。"""
    return [
        config.line_column,
        config.sku_product_name_column,
        config.new_channel_column,
        config.month_label_column,
    ]


def _channel_dimension_columns(config: AppConfig) -> list[str]:
    """返回新产品渠道树表固定使用的两层维度列。"""
    return [
        config.new_channel_column,
        config.month_label_column,
    ]


def _time_dimension_columns(config: AppConfig) -> list[str]:
    """返回时间树表固定使用的三层维度列。"""
    return [
        config.month_label_column,
        config.day_label_column,
        config.new_channel_column,
    ]


def _existing_path_columns(group_columns: list[str], config: AppConfig) -> list[str]:
    """从分组列中过滤出真正参与树路径拼接的展示维度列。"""
    path_columns = [
        config.month_label_column,
        config.day_label_column,
        config.new_channel_column,
    ]
    return [column for column in path_columns if column in group_columns]


def _existing_category_path_columns(group_columns: list[str], config: AppConfig) -> list[str]:
    """从分类分组列中过滤出真正参与树路径拼接的展示维度列。"""
    path_columns = [
        config.line_column,
        config.sku_product_name_column,
        config.new_channel_column,
        config.month_label_column,
    ]
    return [column for column in path_columns if column in group_columns]


def _existing_channel_path_columns(group_columns: list[str], config: AppConfig) -> list[str]:
    """从渠道分组列中过滤出真正参与树路径拼接的展示维度列。"""
    path_columns = [
        config.new_channel_column,
        config.month_label_column,
    ]
    return [column for column in path_columns if column in group_columns]
