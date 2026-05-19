"""CPS 分析树形表数据构造。"""
import pandas as pd

from app.dashboards.cps_analysis.config import AppConfig


def build_cps_tree_summary(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """生成“团长 > 日期 > 产品”三层树表。

    Args:
        df: 已筛选的 CPS 分析明细。
        config: CPS 分析字段配置。

    Returns:
        带 path 列的树形汇总表。团长、日期和产品三个层级都会显式计算汇总值，
        避免前端自动生成父级节点时展示空指标。
    """
    if df.empty:
        return pd.DataFrame(columns=[*config.tree_columns, "path"])

    # 三个层级分别汇总，父级节点也保留真实金额和佣金比例，方便直接查看整体表现。
    leader_df = _build_tree_level_summary(
        df,
        [config.leader_column],
        1,
        config,
    )
    day_df = _build_tree_level_summary(
        df,
        [config.leader_column, config.date_column, config.day_label_column],
        2,
        config,
    )
    product_df = _build_tree_level_summary(
        df,
        [
            config.leader_column,
            config.date_column,
            config.day_label_column,
            config.product_name_column,
        ],
        3,
        config,
    )
    tree_df = pd.concat([leader_df, day_df, product_df], ignore_index=True)
    tree_df = tree_df.sort_values(
        [
            config.leader_column,
            config.date_column,
            config.product_name_column,
            "_tree_depth",
            "path",
        ],
        na_position="first",
    ).reset_index(drop=True)
    return tree_df.drop(columns=["_tree_depth", config.date_column], errors="ignore")


def _build_tree_level_summary(
    df: pd.DataFrame,
    group_columns: list[str],
    tree_depth: int,
    config: AppConfig,
) -> pd.DataFrame:
    """按指定树层级生成汇总行。

    Args:
        df: 已筛选的 CPS 明细。
        group_columns: 当前层级参与聚合的字段。
        tree_depth: 当前树深度，团长为 1、日期为 2、产品为 3。
        config: CPS 分析字段配置。

    Returns:
        补齐展示列、path 和树深度的汇总表。
    """
    summary_df = _build_summary(df, group_columns, config)
    for column in [config.leader_column, config.day_label_column, config.product_name_column]:
        if column not in summary_df.columns:
            summary_df[column] = ""
    if config.date_column not in summary_df.columns:
        summary_df[config.date_column] = pd.NaT

    # path 只拼接用户可见字段，Date 仅用于稳定排序，不出现在树路径里。
    summary_df["_tree_depth"] = tree_depth
    summary_df["path"] = (
        summary_df[_path_columns(group_columns, config)]
        .fillna(config.unknown_text)
        .astype(str)
        .agg("||".join, axis=1)
    )
    return summary_df[
        [
            *config.tree_columns,
            config.date_column,
            "path",
            "_tree_depth",
        ]
    ]


def _build_summary(
    df: pd.DataFrame,
    group_columns: list[str],
    config: AppConfig,
) -> pd.DataFrame:
    """按维度汇总 CPS 金额并重新计算佣金比例。

    Args:
        df: 已筛选的 CPS 明细。
        group_columns: 当前汇总维度。
        config: CPS 分析字段配置。

    Returns:
        含 tk计佣金额、tk总佣金、佣金比例的汇总表。
    """
    grouped_df = (
        df.groupby(group_columns, dropna=False, as_index=False)
        .agg(
            {
                config.display_commission_base_column: "sum",
                config.display_total_commission_column: "sum",
            }
        )
    )
    grouped_df[config.commission_rate_column] = _safe_divide(
        grouped_df[config.display_total_commission_column],
        grouped_df[config.display_commission_base_column],
    )
    return grouped_df


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """安全计算比值，分母为 0 时返回 0。

    Args:
        numerator: 分子序列。
        denominator: 分母序列。

    Returns:
        已处理除零和空值的比值序列。
    """
    denominator = pd.to_numeric(denominator, errors="coerce").fillna(0)
    numerator = pd.to_numeric(numerator, errors="coerce").fillna(0)
    result = numerator.divide(denominator.where(denominator != 0), fill_value=0)
    return result.replace([float("inf"), float("-inf")], 0).fillna(0)


def _path_columns(group_columns: list[str], config: AppConfig) -> list[str]:
    """返回树路径使用的展示维度。

    Args:
        group_columns: 当前聚合维度。
        config: CPS 分析字段配置。

    Returns:
        过滤掉排序用 Date 字段后的 path 字段列表。
    """
    preferred_columns = [
        config.leader_column,
        config.day_label_column,
        config.product_name_column,
    ]
    return [column for column in preferred_columns if column in group_columns]
