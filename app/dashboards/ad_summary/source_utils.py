"""广告汇总归一化通用工具。"""
import pandas as pd

from app.dashboards.ad_summary.config import AppConfig


def parse_date(series: pd.Series) -> pd.Series:
    """兼容 YYYYMMDD 数字、字符串和普通日期格式。

    Args:
        series: 原始日期列。

    Returns:
        标准化到日粒度的 pandas datetime 序列。
    """
    text = series.astype("string").str.strip()
    compact_date = text.str.fullmatch(r"\d{8}", na=False)
    result = pd.to_datetime(text, errors="coerce")
    result.loc[compact_date] = pd.to_datetime(text.loc[compact_date], format="%Y%m%d", errors="coerce")
    return result.dt.normalize()


def normalize_key(series: pd.Series) -> pd.Series:
    """把 Excel 中可能是数字或文本的关联键统一成字符串。

    Args:
        series: SKU、营销场景等关联键列。

    Returns:
        去空格、去 `.0` 后缀后的字符串序列；空值返回空字符串。
    """
    text = series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    return text.fillna("").replace({"nan": "", "<NA>": ""})


def format_day_label(value: pd.Timestamp) -> str:
    """把日期格式化成页面使用的年/月/日文本。

    Args:
        value: pandas Timestamp 或空日期。

    Returns:
        形如 `2025/1/1` 的文本；空日期返回空字符串。
    """
    if pd.isna(value):
        return ""
    return f"{value.year}/{value.month}/{value.day}"


def dimension_columns(config: AppConfig) -> list[str]:
    """返回统一明细中的维度列。

    Args:
        config: 广告汇总配置。

    Returns:
        统一事实表必须包含的维度列名列表。
    """
    return [
        config.date_column,
        config.ad_sku_id_column,
        config.product_name_column,
        config.category_column,
        config.brand_column,
        config.plan_aggregate_column,
        config.new_channel_column,
        config.channel_type_column,
    ]


def metric_columns(config: AppConfig) -> list[str]:
    """返回统一明细中的基础指标列。

    Args:
        config: 广告汇总配置。

    Returns:
        所有来源归一化后需要补齐的基础指标列名列表。
    """
    return [
        config.ad_cost_column,
        config.ad_impression_column,
        config.ad_click_column,
        config.ad_order_row_column,
        config.ad_gmv_column,
        config.ad_cart_column,
        config.ad_new_customer_column,
        config.shop_gmv_column,
        config.shop_target_column,
        config.shop_pv_column,
        config.shop_visitor_column,
        config.shop_buyer_column,
        config.shop_item_count_column,
    ]
