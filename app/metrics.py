"""指标计算模块。

这里集中维护所有“口径”相关逻辑，避免 UI 或 processor 中直接写计算公式。
后续如果 CTR、CVR、ROI 的定义发生变化，只需要优先修改本模块。
"""

from dataclasses import dataclass

import pandas as pd

from app.config import AppConfig


@dataclass(frozen=True)
class SummaryMetrics:
    """页面顶部指标卡所需的汇总结果。"""

    impressions: float
    clicks: float
    cost: float
    gmv: float
    orders: float
    ctr: float
    cvr: float
    roi: float


def safe_divide(numerator: float, denominator: float) -> float:
    """安全除法，分母为空或为 0 时返回 0。"""

    return numerator / denominator if denominator and denominator != 0 else 0


def calculate_summary_metrics(df: pd.DataFrame, config: AppConfig) -> SummaryMetrics:
    """计算当前筛选范围下的大盘汇总指标。

    关键口径：
    - 先对原子指标求和；
    - 再基于汇总值计算比率；
    这样可以避免“先逐行算比率再平均”造成的统计失真。
    """

    impressions = df[config.impressions_column].sum()
    clicks = df[config.clicks_column].sum()
    cost = df[config.cost_column].sum()
    gmv = df[config.gmv_column].sum()
    orders = df[config.orders_column].sum()

    return SummaryMetrics(
        impressions=impressions,
        clicks=clicks,
        cost=cost,
        gmv=gmv,
        orders=orders,
        ctr=safe_divide(clicks, impressions),
        cvr=safe_divide(orders, clicks),
        roi=safe_divide(gmv, cost),
    )


def build_pivot_table(
    df: pd.DataFrame, group_by: list[str], config: AppConfig
) -> pd.DataFrame:
    """按指定维度构建透视分析表。

    参数 `group_by` 使用列表而不是单个字段，是为了兼容后续扩展到多维分组。
    当前默认仍按 `新产品渠道` 分组，以保持现有行为不变。
    """

    pivot_df = (
        df.groupby(group_by)
        .agg(
            曝光数=(config.impressions_column, "sum"),
            点击数=(config.clicks_column, "sum"),
            消耗=(config.cost_column, "sum"),
            总订单金额=(config.gmv_column, "sum"),
            总订单行=(config.orders_column, "sum"),
        )
        .reset_index()
    )

    # 透视表同样遵循“先聚合，再算比率”的口径。
    pivot_df["CTR"] = pivot_df["点击数"].div(pivot_df["曝光数"]).fillna(0)
    pivot_df["CVR"] = pivot_df["总订单行"].div(pivot_df["点击数"]).fillna(0)
    pivot_df["ROI"] = pivot_df["总订单金额"].div(pivot_df["消耗"]).fillna(0)

    return pivot_df
