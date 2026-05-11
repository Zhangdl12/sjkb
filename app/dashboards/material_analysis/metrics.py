"""
素材分析看板的指标计算逻辑。

提供两个核心函数：
  - calculate_summary_metrics() → 顶部汇总指标卡
  - build_pivot_table() → 分组透视表

指标说明：
  - CTR（点击率）= 点击数 / 展现数
  - CVR（转化率）= 总订单行 / 点击数
  - ROI（投资回报率）= 总订单金额 / 花费
  所有比率类指标在分母为 0 时返回 0（调用 safe_divide）
"""
from dataclasses import dataclass

import pandas as pd

from app.dashboards.material_analysis.config import AppConfig


@dataclass(frozen=True)
class SummaryMetrics:
    """页面顶部展示的汇总指标。

    包含 5 个绝对量指标 + 3 个比率指标，共 8 个值。
    渲染时只展示其中 6 个（展现/点击/花费/CTR/CVR/ROI）。
    """
    impressions: float  # 展现数
    clicks: float       # 点击数
    cost: float         # 花费（元）
    gmv: float          # 总订单金额（元）
    orders: float       # 总订单行
    ctr: float          # 点击率
    cvr: float          # 转化率
    roi: float          # 投资回报率


def safe_divide(numerator: float, denominator: float) -> float:
    """安全除法：分母为 0 或空值时返回 0，避免 ZeroDivisionError。"""
    return numerator / denominator if denominator and denominator != 0 else 0


def calculate_summary_metrics(df: pd.DataFrame, config: AppConfig) -> SummaryMetrics:
    """根据筛选后的数据计算顶部汇总指标。

    Args:
        df: 筛选后的分析宽表
        config: 看板列名配置

    Returns:
        SummaryMetrics 对象，包含所有汇总值
    """
    # 直接对筛选后的 DataFrame 做列求和
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
    """构建分组透视表。

    按 group_by 列分组，聚合各指标列的 sum，并计算 CTR/CVR/ROI 比率列。

    Args:
        df: 筛选后的分析宽表
        group_by: 分组列列表（如 ["新产品渠道"]）
        config: 看板列名配置

    Returns:
        透视表 DataFrame，包含分组列 + 5 个汇总列 + 3 个比率列
    """
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

    # 在聚合结果上派生比率列
    pivot_df["CTR"] = pivot_df["点击数"].div(pivot_df["展现数"]).fillna(0)
    pivot_df["CVR"] = pivot_df["总订单行"].div(pivot_df["点击数"]).fillna(0)
    pivot_df["ROI"] = pivot_df["总订单金额"].div(pivot_df["花费"]).fillna(0)

    return pivot_df
