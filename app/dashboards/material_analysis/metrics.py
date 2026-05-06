"""素材分析看板的指标计算逻辑。"""

from dataclasses import dataclass

import pandas as pd

from app.dashboards.material_analysis.config import AppConfig


@dataclass(frozen=True)
class SummaryMetrics:
    """页面顶部展示的汇总指标。"""

    impressions: float
    clicks: float
    cost: float
    gmv: float
    orders: float
    ctr: float
    cvr: float
    roi: float


def safe_divide(numerator: float, denominator: float) -> float:
    """安全除法：分母为空或为 0 时返回 0。"""

    return numerator / denominator if denominator and denominator != 0 else 0


def calculate_summary_metrics(df: pd.DataFrame, config: AppConfig) -> SummaryMetrics:
    """根据筛选后的数据计算顶部汇总指标。"""

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
    """构建当前看板使用的分组透视表。"""

    pivot_df = (
        df.groupby(group_by)
        .agg(
            展现数=(config.impressions_column, "sum"),
            点击数=(config.clicks_column, "sum"),
            花费=(config.cost_column, "sum"),
            总订单金额=(config.gmv_column, "sum"),
            总订单行=(config.orders_column, "sum"),
        )
        .reset_index()
    )

    pivot_df["CTR"] = pivot_df["点击数"].div(pivot_df["展现数"]).fillna(0)
    pivot_df["CVR"] = pivot_df["总订单行"].div(pivot_df["点击数"]).fillna(0)
    pivot_df["ROI"] = pivot_df["总订单金额"].div(pivot_df["花费"]).fillna(0)

    return pivot_df
