"""广告汇总多来源归一化。

本模块只负责把不同 Excel sheet 转成同一套事实字段，不做周期汇总。
这样后续指标模块可以统一按基础指标先求和、再重算比例指标。
"""
import pandas as pd

from app.dashboards.ad_summary.config import AppConfig
from app.dashboards.ad_summary.source_utils import (
    dimension_columns,
    format_day_label,
    metric_columns,
    normalize_key,
    parse_date,
)


class DataProcessingError(Exception):
    """广告数据汇总加工异常。"""


def build_normalized_detail(
    tables: dict[str, pd.DataFrame],
    config: AppConfig,
) -> pd.DataFrame:
    """构建广告汇总统一明细表。

    Args:
        tables: 已读取的业务表和打标表，必须包含 station、brand、cps、sitewide、
            shop、channel_tag、sku_tag。
        config: 广告汇总字段配置。

    Returns:
        已完成来源归一、打标和时间维度补充的 DataFrame。

    Raises:
        DataProcessingError: 缺少必要字段或加工失败时抛出。
    """
    try:
        channel_map = _build_channel_mapping(tables["channel_tag"], config)
        sku_map = _build_sku_mapping(tables["sku_tag"], config)
        frames = [
            _build_station_rows(tables["station"], channel_map, sku_map, config),
            _build_brand_rows(tables["brand"], channel_map, config),
            _build_cps_rows(tables["cps"], channel_map, sku_map, config),
            _build_sitewide_rows(tables["sitewide"], channel_map, config),
            _build_shop_rows(tables["shop"], sku_map, config),
        ]
        result_df = pd.concat(frames, ignore_index=True)
        result_df = _fill_dimension_columns(result_df, config)
        result_df = _fill_metric_columns(result_df, config)
        return _add_time_columns(result_df, config)
    except KeyError as exc:
        raise DataProcessingError(f"广告汇总缺少必要字段: {exc}") from exc
    except Exception as exc:
        raise DataProcessingError(f"广告汇总加工失败: {exc}") from exc


def _build_channel_mapping(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """生成营销场景到渠道标签的映射表。

    Args:
        df: 渠道打标 sheet。
        config: 广告汇总字段配置。

    Returns:
        去重后的渠道映射表，包含内部关联键和三列渠道标签。
    """
    mapping_df = df[
        [
            config.channel_scene_column,
            config.plan_aggregate_column,
            config.new_channel_column,
            config.channel_type_column,
        ]
    ].copy()
    mapping_df["_scene_key"] = normalize_key(mapping_df[config.channel_scene_column])
    return mapping_df.drop_duplicates(subset=["_scene_key"])


def _build_sku_mapping(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """生成 SKU 到商品标签的映射表。

    Args:
        df: 商品打标 sheet。
        config: 广告汇总字段配置。

    Returns:
        去重后的商品映射表，包含内部 SKU 键、商品名称、投放品牌和新分类。
    """
    mapping_df = df[
        [
            config.sku_tag_id_column,
            config.sku_tag_name_column,
            config.sku_tag_brand_column,
            config.sku_tag_category_column,
        ]
    ].copy()
    mapping_df["_sku_key"] = normalize_key(mapping_df[config.sku_tag_id_column])
    mapping_df = mapping_df.rename(
        columns={
            config.sku_tag_name_column: "_tag_product_name",
            config.sku_tag_brand_column: "_tag_brand",
            config.sku_tag_category_column: "_tag_category",
        }
    )
    return mapping_df.drop_duplicates(subset=["_sku_key"])


def _build_station_rows(
    df: pd.DataFrame,
    channel_map: pd.DataFrame,
    sku_map: pd.DataFrame,
    config: AppConfig,
) -> pd.DataFrame:
    """归一化站内外广告数据。

    Args:
        df: 站内外数据源。
        channel_map: 渠道打标映射。
        sku_map: 商品打标映射。
        config: 广告汇总字段配置。

    Returns:
        统一字段的站内外广告明细。
    """
    rows = _empty_normalized_frame(df, config, config.ad_source_type)
    rows[config.date_column] = parse_date(df[config.station_date_column])
    rows[config.ad_sku_id_column] = normalize_key(df[config.station_sku_column])
    rows = _merge_sku_tags(rows, sku_map, df[config.station_sku_name_column], config)

    rows["_scene_key"] = normalize_key(df[config.station_scene_column])
    rows = _merge_channel_tags(rows, channel_map, config)
    _copy_metric(rows, df, config.station_cost_column, config.ad_cost_column)
    _copy_metric(rows, df, config.station_impression_column, config.ad_impression_column)
    _copy_metric(rows, df, config.station_click_column, config.ad_click_column)
    _copy_metric(rows, df, config.station_order_row_column, config.ad_order_row_column)
    _copy_metric(rows, df, config.station_gmv_column, config.ad_gmv_column)
    _copy_metric(rows, df, config.station_cart_column, config.ad_cart_column)
    _copy_metric(rows, df, config.station_new_customer_column, config.ad_new_customer_column)
    return rows


def _build_brand_rows(
    df: pd.DataFrame,
    channel_map: pd.DataFrame,
    config: AppConfig,
) -> pd.DataFrame:
    """归一化品专数据，并通过合成营销场景关联渠道打标。

    Args:
        df: 品专数据源。
        channel_map: 渠道打标映射。
        config: 广告汇总字段配置。

    Returns:
        统一字段的品专广告明细。
    """
    rows = _empty_normalized_frame(df, config, config.ad_source_type)
    rows[config.date_column] = parse_date(df[config.brand_date_column])
    rows["_scene_key"] = normalize_key(pd.Series(config.synthetic_brand_scene, index=df.index))
    rows = _merge_channel_tags(rows, channel_map, config)
    for target_column, source_column in _brand_metric_map(config).items():
        _copy_metric(rows, df, source_column, target_column)
    return rows


def _build_sitewide_rows(
    df: pd.DataFrame,
    channel_map: pd.DataFrame,
    config: AppConfig,
) -> pd.DataFrame:
    """归一化全站营销数据，并通过合成营销场景关联渠道打标。"""
    rows = _empty_normalized_frame(df, config, config.ad_source_type)
    rows[config.date_column] = parse_date(df[config.sitewide_date_column])
    rows["_scene_key"] = normalize_key(pd.Series(config.synthetic_sitewide_scene, index=df.index))
    rows = _merge_channel_tags(rows, channel_map, config)
    for target_column, source_column in _sitewide_metric_map(config).items():
        _copy_metric(rows, df, source_column, target_column)
    return rows


def _build_cps_rows(
    df: pd.DataFrame,
    channel_map: pd.DataFrame,
    sku_map: pd.DataFrame,
    config: AppConfig,
) -> pd.DataFrame:
    """归一化 CPS 数据。

    Args:
        df: CPS 数据源。
        sku_map: 商品打标映射。
        config: 广告汇总字段配置。

    Returns:
        统一字段的 CPS 广告明细。
    """
    rows = _empty_normalized_frame(df, config, config.ad_source_type)
    rows[config.date_column] = parse_date(df[config.cps_date_column])
    rows[config.ad_sku_id_column] = normalize_key(df[config.cps_sku_column])
    rows = _merge_sku_tags(rows, sku_map, pd.Series(pd.NA, index=df.index), config)
    rows["_scene_key"] = normalize_key(pd.Series(config.synthetic_cps_scene, index=df.index))
    rows = _merge_channel_tags(rows, channel_map, config)
    _copy_metric(rows, df, config.cps_cost_column, config.ad_cost_column)
    _copy_metric(rows, df, config.cps_gmv_column, config.ad_gmv_column)
    _copy_metric(rows, df, config.cps_order_row_column, config.ad_order_row_column)
    return rows


def _build_shop_rows(
    df: pd.DataFrame,
    sku_map: pd.DataFrame,
    config: AppConfig,
) -> pd.DataFrame:
    """归一化店铺销售数据。

    Args:
        df: 店铺商智销售数据源。
        sku_map: 商品打标映射。
        config: 广告汇总字段配置。

    Returns:
        统一字段的店铺销售明细。广告维度保持空白，后续筛选时会被排除。
    """
    rows = _empty_normalized_frame(df, config, config.shop_source_type)
    rows[config.date_column] = parse_date(df[config.shop_date_column])
    rows[config.ad_sku_id_column] = normalize_key(df[config.shop_sku_id_column])
    rows = _merge_sku_tags(rows, sku_map, df[config.shop_product_name_column], config)
    rows[config.brand_column] = rows[config.brand_column].where(
        rows[config.brand_column].notna(),
        df[config.shop_brand_column],
    )
    _copy_metric(rows, df, config.shop_gmv_source_column, config.shop_gmv_column)
    _copy_metric(rows, df, config.shop_pv_source_column, config.shop_pv_column)
    _copy_metric(rows, df, config.shop_visitor_source_column, config.shop_visitor_column)
    _copy_metric(rows, df, config.shop_buyer_source_column, config.shop_buyer_column)
    _copy_metric(rows, df, config.shop_item_count_source_column, config.shop_item_count_column)
    rows[config.shop_target_column] = 0.0
    return rows


def _empty_normalized_frame(df: pd.DataFrame, config: AppConfig, source_type: str) -> pd.DataFrame:
    """创建包含所有统一字段的空壳 DataFrame。"""
    rows = pd.DataFrame(index=df.index)
    rows[config.source_type_column] = source_type
    for column in dimension_columns(config):
        rows[column] = pd.NA
    for column in metric_columns(config):
        rows[column] = 0.0
    return rows


def _merge_sku_tags(
    rows: pd.DataFrame,
    sku_map: pd.DataFrame,
    fallback_name: pd.Series,
    config: AppConfig,
) -> pd.DataFrame:
    """按 SKU 关联商品打标，并处理商品名称兜底。"""
    merged_df = rows.merge(sku_map, left_on=config.ad_sku_id_column, right_on="_sku_key", how="left")
    merged_df[config.product_name_column] = merged_df["_tag_product_name"].where(
        merged_df["_tag_product_name"].notna(),
        fallback_name.reset_index(drop=True),
    )
    merged_df[config.brand_column] = merged_df["_tag_brand"]
    merged_df[config.category_column] = merged_df["_tag_category"]
    return merged_df.drop(
        columns=["_sku_key", "_tag_product_name", "_tag_brand", "_tag_category"],
        errors="ignore",
    )


def _merge_channel_tags(
    rows: pd.DataFrame,
    channel_map: pd.DataFrame,
    config: AppConfig,
) -> pd.DataFrame:
    """按营销场景统一写回计划聚合、新产品渠道和渠道类型。"""
    merged_df = rows.merge(channel_map, on="_scene_key", how="left", suffixes=("", "_tag"))
    for column in [config.plan_aggregate_column, config.new_channel_column, config.channel_type_column]:
        # 所有广告来源统一从渠道打标表回填三列渠道维度，保证规则来源唯一。
        merged_df[column] = merged_df[f"{column}_tag"].where(
            merged_df[f"{column}_tag"].notna(),
            merged_df[column],
        )
    return merged_df.drop(
        columns=[
            "_scene_key",
            config.channel_scene_column,
            f"{config.plan_aggregate_column}_tag",
            f"{config.new_channel_column}_tag",
            f"{config.channel_type_column}_tag",
        ],
        errors="ignore",
    )


def _brand_metric_map(config: AppConfig) -> dict[str, str]:
    """返回品专来源字段映射。"""
    return {
        config.ad_cost_column: config.brand_cost_column,
        config.ad_impression_column: config.brand_impression_column,
        config.ad_click_column: config.brand_click_column,
        config.ad_order_row_column: config.brand_order_row_column,
        config.ad_gmv_column: config.brand_gmv_column,
        config.ad_cart_column: config.brand_cart_column,
    }


def _sitewide_metric_map(config: AppConfig) -> dict[str, str]:
    """返回全站营销来源字段映射。"""
    return {
        config.ad_cost_column: config.sitewide_cost_column,
        config.ad_impression_column: config.sitewide_impression_column,
        config.ad_click_column: config.sitewide_click_column,
        config.ad_order_row_column: config.sitewide_order_row_column,
        config.ad_gmv_column: config.sitewide_gmv_column,
        config.ad_new_customer_column: config.sitewide_new_customer_column,
    }


def _copy_metric(rows: pd.DataFrame, source_df: pd.DataFrame, source_column: str, target_column: str) -> None:
    """把原始数值列复制到统一指标列，并统一转为数字。"""
    rows[target_column] = pd.to_numeric(source_df[source_column], errors="coerce").fillna(0.0)


def _fill_dimension_columns(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """维度列缺失统一进入空白项，避免筛选器出现 NaN。"""
    result_df = df.copy()
    for column in dimension_columns(config):
        if column == config.date_column:
            continue
        result_df[column] = result_df[column].fillna(config.blank_text).replace("", config.blank_text)
    return result_df


def _fill_metric_columns(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """所有基础指标转为数值并补 0，保障后续聚合公式稳定。"""
    result_df = df.copy()
    for column in metric_columns(config):
        result_df[column] = pd.to_numeric(result_df[column], errors="coerce").fillna(0.0)
    return result_df


def _add_time_columns(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """补充年、季度、月、周、日维度字段。"""
    result_df = df.copy()
    # 年份可能遇到空日期。直接使用 dt.year 会因为 NaN 把整列转成 float，
    # 导致筛选器展示 2025.0；这里使用 nullable integer 保留空值并展示整数年份。
    result_df[config.year_column] = result_df[config.date_column].dt.year.astype("Int64")
    result_df[config.quarter_sort_column] = result_df[config.date_column].dt.quarter
    result_df[config.quarter_label_column] = "Q" + result_df[config.quarter_sort_column].astype("Int64").astype(str)
    result_df[config.month_sort_column] = result_df[config.date_column].dt.month
    result_df[config.month_label_column] = "M" + result_df[config.month_sort_column].astype("Int64").astype(str)
    result_df[config.week_sort_column] = result_df[config.date_column].dt.isocalendar().week.astype("Int64")
    result_df[config.week_label_column] = "W" + result_df[config.week_sort_column].astype(str)
    result_df[config.day_label_column] = result_df[config.date_column].apply(format_day_label)
    return result_df
