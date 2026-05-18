import pandas as pd

from app.dashboards.channel_analysis.config import AppConfig


class DataProcessingError(Exception):
    """渠道分析数据加工异常。"""


def build_channel_analysis_dataset(
    tables: dict[str, pd.DataFrame],
    config: AppConfig,
) -> pd.DataFrame:
    """构建渠道分析明细宽表。"""
    try:
        ad_df = _build_ad_detail(tables["ad"], config)
        plan_df = _build_plan_mapping(tables["plan"], config)
        sku_df = _build_sku_mapping(tables["sku"], config)

        merged_df = ad_df.merge(  # 将广告数据与计划类型匹配表进行合并，获取计划聚合、渠道类型等信息
            plan_df,
            left_on=config.ad_plan_type_column,
            right_on=config.plan_type_column,
            how="left",
        )
        merged_df = merged_df.merge( # 将上一步的结果与商品匹配表进行合并，获取商品名称、分类、品牌等信息
            sku_df,
            left_on=config.ad_sku_id_column,
            right_on=config.sku_id_column,
            how="left",
        )

        merged_df[config.sku_product_name_column] = ( # 优先使用商品匹配表中的商品名称，其次使用广告数据中的跟单SKU名称，最后填充为未知
            merged_df[config.sku_product_name_column]
            .fillna(merged_df[config.ad_product_name_column])
            .fillna(config.unknown_text)
        )
        for column in [
            config.channel_type_column,
            config.new_channel_column,
            config.plan_aggregate_column,
            config.brand_column,
            config.category_column,
        ]:
            merged_df[column] = merged_df[column].fillna(config.unknown_text)

        metric_columns = [
            config.ad_cost_column,
            config.ad_order_row_column,
            config.ad_gmv_column,
            config.ad_click_column,
            config.ad_impression_column,
            config.ad_new_customer_column,
        ]
        for column in metric_columns:
            merged_df[column] = pd.to_numeric(merged_df[column], errors="coerce").fillna(0)

        return _add_time_columns(merged_df, config)
    except KeyError as exc:
        raise DataProcessingError(f"渠道分析缺少必要字段: {exc}") from exc
    except Exception as exc:
        raise DataProcessingError(f"渠道分析加工失败: {exc}") from exc


def _build_ad_detail(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    ad_df = df.copy()
    ad_df[config.date_column] = pd.to_datetime(
        ad_df[config.ad_date_column].astype(str),
        format="%Y%m%d",
        errors="coerce",
    )
    ad_df[config.ad_sku_id_column] = pd.to_numeric(
        ad_df[config.ad_sku_id_column],
        errors="coerce",
    )
    return ad_df


def _build_plan_mapping(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    return df[
        [
            config.plan_type_column,
            config.plan_aggregate_column,
            config.new_channel_column,
            config.channel_type_column,
        ]
    ].drop_duplicates(subset=[config.plan_type_column])


def _build_sku_mapping(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    sku_df = df.copy()
    sku_df[config.sku_id_column] = pd.to_numeric(sku_df[config.sku_id_column], errors="coerce")
    if config.sku_product_name_column not in sku_df.columns:
        sku_df[config.sku_product_name_column] = pd.NA
    return sku_df[
        [
            config.sku_id_column,
            config.sku_product_name_column,
            config.category_column,
            config.brand_column,
        ]
    ].drop_duplicates(subset=[config.sku_id_column])


def _add_time_columns(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    result_df = df.copy()
    result_df[config.year_column] = result_df[config.date_column].dt.year
    result_df[config.quarter_sort_column] = result_df[config.date_column].dt.quarter
    result_df[config.quarter_label_column] = (
        "Q" + result_df[config.quarter_sort_column].astype("Int64").astype(str)
    )
    result_df[config.month_sort_column] = result_df[config.date_column].dt.month
    result_df[config.month_label_column] = (
        "M" + result_df[config.month_sort_column].astype("Int64").astype(str)
    )
    result_df[config.week_sort_column] = result_df[config.date_column].dt.isocalendar().week.astype("Int64")
    result_df[config.week_label_column] = (
        "W" + result_df[config.week_sort_column].astype(str)
    )
    result_df[config.day_label_column] = result_df[config.date_column].apply(_format_day_label)
    return result_df


def _format_day_label(value: pd.Timestamp) -> str:
    if pd.isna(value):
        return ""
    return f"{value.year}/{value.month}/{value.day}"
