"""渠道分析数据归一化处理。"""
import pandas as pd

from app.dashboards.channel_analysis.config import AppConfig


class DataProcessingError(Exception):
    """渠道分析数据加工异常。"""


def build_channel_analysis_dataset(
    tables: dict[str, pd.DataFrame],
    config: AppConfig,
) -> pd.DataFrame:
    """构建渠道分析统一明细表。

    Args:
        tables: 已读取的业务数据源和打标表，必须包含 station、cps、brand、
            sitewide、channel_tag、sku_tag。
        config: 渠道分析配置，提供工作表、字段和固定场景名称。

    Returns:
        多来源广告数据归一后的明细 DataFrame。
    """
    try:
        channel_map = _build_channel_mapping(tables["channel_tag"], config)
        sku_map = _build_sku_mapping(tables["sku_tag"], config)
        frames = [
            _build_station_rows(tables["station"], channel_map, sku_map, config),
            _build_cps_rows(tables["cps"], channel_map, sku_map, config),
            _build_brand_rows(tables["brand"], channel_map, config),
            _build_sitewide_rows(tables["sitewide"], channel_map, config),
        ]
        result_df = pd.concat(frames, ignore_index=True)
        result_df = _fill_dimensions(result_df, config)
        result_df = _fill_metrics(result_df, config)
        return _add_time_columns(result_df, config)
    except KeyError as exc:
        raise DataProcessingError(f"渠道分析缺少必要字段: {exc}") from exc
    except Exception as exc:
        raise DataProcessingError(f"渠道分析加工失败: {exc}") from exc


def _build_channel_mapping(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """生成营销场景到渠道标签的去重映射表。"""
    mapping_df = df[
        [
            config.channel_scene_column,
            config.plan_aggregate_column,
            config.new_channel_column,
            config.channel_type_column,
        ]
    ].copy()
    mapping_df["_scene_key"] = _normalize_key(mapping_df[config.channel_scene_column])
    return mapping_df.drop_duplicates(subset=["_scene_key"])


def _build_sku_mapping(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """生成 SKU 到商品名称、品牌、品线分类的去重映射表。"""
    mapping_df = df[
        [
            config.sku_id_column,
            config.sku_product_name_column,
            config.brand_column,
            config.sku_category_column,
        ]
    ].copy()
    mapping_df["_sku_key"] = _normalize_key(mapping_df[config.sku_id_column])
    mapping_df = mapping_df.rename(columns={config.sku_category_column: config.line_column})
    return mapping_df.drop_duplicates(subset=["_sku_key"])


def _build_station_rows(
    df: pd.DataFrame,
    channel_map: pd.DataFrame,
    sku_map: pd.DataFrame,
    config: AppConfig,
) -> pd.DataFrame:
    """归一化站内外广告数据，并同时走渠道打标和商品打标。"""
    rows = _empty_frame(df, config)
    rows[config.date_column] = _parse_date(df[config.station_date_column])
    rows["_scene_key"] = _normalize_key(df[config.station_scene_column])
    rows["_sku_key"] = _normalize_key(df[config.station_sku_column])
    rows[config.sku_product_name_column] = df[config.station_sku_name_column]
    rows = _merge_channel_tags(rows, channel_map, config)
    rows = _merge_sku_tags(rows, sku_map, config)
    _copy_metric(rows, df, config.station_cost_column, config.ad_cost_column)
    _copy_metric(rows, df, config.station_impression_column, config.ad_impression_column)
    _copy_metric(rows, df, config.station_click_column, config.ad_click_column)
    _copy_metric(rows, df, config.station_order_row_column, config.ad_order_row_column)
    _copy_metric(rows, df, config.station_gmv_column, config.ad_gmv_column)
    _copy_metric(rows, df, config.station_new_customer_column, config.ad_new_customer_column)
    _copy_metric(rows, df, config.station_cart_column, config.ad_cart_column)
    return rows


def _build_cps_rows(
    df: pd.DataFrame,
    channel_map: pd.DataFrame,
    sku_map: pd.DataFrame,
    config: AppConfig,
) -> pd.DataFrame:
    """归一化 CPS 数据，使用合成营销场景“京挑客”走渠道打标。"""
    rows = _empty_frame(df, config)
    rows[config.date_column] = _parse_date(df[config.cps_date_column])
    rows["_scene_key"] = _normalize_key(pd.Series(config.synthetic_cps_scene, index=df.index))
    rows["_sku_key"] = _normalize_key(df[config.cps_sku_column])
    rows = _merge_channel_tags(rows, channel_map, config)
    rows = _merge_sku_tags(rows, sku_map, config)
    _copy_metric(rows, df, config.cps_cost_column, config.ad_cost_column)
    _copy_metric(rows, df, config.cps_order_row_column, config.ad_order_row_column)
    _copy_metric(rows, df, config.cps_gmv_column, config.ad_gmv_column)
    return rows


def _build_brand_rows(
    df: pd.DataFrame,
    channel_map: pd.DataFrame,
    config: AppConfig,
) -> pd.DataFrame:
    """归一化品专数据，使用合成营销场景“搜索品专”走渠道打标。"""
    rows = _empty_frame(df, config)
    rows[config.date_column] = _parse_date(df[config.brand_date_column])
    rows["_scene_key"] = _normalize_key(pd.Series(config.synthetic_brand_scene, index=df.index))
    rows = _merge_channel_tags(rows, channel_map, config)
    _copy_metric(rows, df, config.brand_cost_column, config.ad_cost_column)
    _copy_metric(rows, df, config.brand_impression_column, config.ad_impression_column)
    _copy_metric(rows, df, config.brand_click_column, config.ad_click_column)
    _copy_metric(rows, df, config.brand_order_row_column, config.ad_order_row_column)
    _copy_metric(rows, df, config.brand_gmv_column, config.ad_gmv_column)
    _copy_metric(rows, df, config.brand_cart_column, config.ad_cart_column)
    return rows


def _build_sitewide_rows(
    df: pd.DataFrame,
    channel_map: pd.DataFrame,
    config: AppConfig,
) -> pd.DataFrame:
    """归一化全站营销数据，使用合成营销场景“全站营销”走渠道打标。"""
    rows = _empty_frame(df, config)
    rows[config.date_column] = _parse_date(df[config.sitewide_date_column])
    rows["_scene_key"] = _normalize_key(pd.Series(config.synthetic_sitewide_scene, index=df.index))
    rows = _merge_channel_tags(rows, channel_map, config)
    _copy_metric(rows, df, config.sitewide_cost_column, config.ad_cost_column)
    _copy_metric(rows, df, config.sitewide_impression_column, config.ad_impression_column)
    _copy_metric(rows, df, config.sitewide_click_column, config.ad_click_column)
    _copy_metric(rows, df, config.sitewide_order_row_column, config.ad_order_row_column)
    _copy_metric(rows, df, config.sitewide_gmv_column, config.ad_gmv_column)
    _copy_metric(rows, df, config.sitewide_new_customer_column, config.ad_new_customer_column)
    return rows


def _empty_frame(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """创建统一明细空壳，后续来源只需要填入对应字段。"""
    rows = pd.DataFrame(index=df.index)
    for column in _dimension_columns(config):
        rows[column] = pd.NA
    for column in _metric_columns(config):
        rows[column] = 0.0
    return rows


def _merge_channel_tags(rows: pd.DataFrame, channel_map: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """按营销场景写入计划聚合、新产品渠道和渠道类型。"""
    result_df = rows.merge(channel_map, on="_scene_key", how="left", suffixes=("", "_tag"))
    for column in [config.plan_aggregate_column, config.new_channel_column, config.channel_type_column]:
        # 左侧空壳列用于保持统一结构，真正的渠道标签来自渠道打标表的同名字段。
        result_df[column] = result_df[f"{column}_tag"].where(result_df[f"{column}_tag"].notna(), result_df[column])
    return result_df.drop(
        columns=[
            "_scene_key",
            config.channel_scene_column,
            f"{config.plan_aggregate_column}_tag",
            f"{config.new_channel_column}_tag",
            f"{config.channel_type_column}_tag",
        ],
        errors="ignore",
    )


def _merge_sku_tags(rows: pd.DataFrame, sku_map: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """按 SKU 写入品线分类、商品名称和品牌，原始商品名作为兜底。"""
    result_df = rows.merge(sku_map, on="_sku_key", how="left", suffixes=("", "_tag"))
    for column in [config.sku_product_name_column, config.brand_column, config.line_column]:
        # 商品名称允许来源表原始名称兜底，品牌和品线分类没有来源值时后续统一填“未知”。
        result_df[column] = result_df[f"{column}_tag"].where(result_df[f"{column}_tag"].notna(), result_df[column])
    return result_df.drop(
        columns=[
            "_sku_key",
            f"{config.sku_product_name_column}_tag",
            f"{config.brand_column}_tag",
            f"{config.line_column}_tag",
        ],
        errors="ignore",
    )


def _fill_dimensions(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """把缺失维度统一为“未知”，避免页面筛选器出现 NaN。"""
    result_df = df.copy()
    for column in _dimension_columns(config):
        if column == config.date_column:
            continue
        result_df[column] = result_df[column].fillna(config.unknown_text).replace("", config.unknown_text)
    return result_df


def _fill_metrics(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """把所有基础指标转为数值并补 0，保证汇总公式稳定。"""
    result_df = df.copy()
    for column in _metric_columns(config):
        result_df[column] = pd.to_numeric(result_df[column], errors="coerce").fillna(0.0)
    return result_df


def _add_time_columns(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """基于 Date 补充年、季度、月、周、日筛选字段。"""
    result_df = df.copy()
    result_df[config.year_column] = result_df[config.date_column].dt.year.astype("Int64")
    result_df[config.quarter_sort_column] = result_df[config.date_column].dt.quarter.astype("Int64")
    result_df[config.quarter_label_column] = "Q" + result_df[config.quarter_sort_column].astype(str)
    result_df[config.month_sort_column] = result_df[config.date_column].dt.month.astype("Int64")
    result_df[config.month_label_column] = "M" + result_df[config.month_sort_column].astype(str)
    result_df[config.week_sort_column] = result_df[config.date_column].dt.isocalendar().week.astype("Int64")
    result_df[config.week_label_column] = "W" + result_df[config.week_sort_column].astype(str)
    result_df[config.day_label_column] = result_df[config.date_column].apply(_format_day_label)
    return result_df


def _copy_metric(rows: pd.DataFrame, source_df: pd.DataFrame, source_column: str, target_column: str) -> None:
    """把来源指标列复制到统一指标列。"""
    rows[target_column] = pd.to_numeric(source_df[source_column], errors="coerce").fillna(0.0)


def _parse_date(series: pd.Series) -> pd.Series:
    """兼容 YYYYMMDD 数字、字符串和日期对象。"""
    text = series.astype("string").str.strip()
    compact = text.str.fullmatch(r"\d{8}", na=False)
    result = pd.to_datetime(text, errors="coerce")
    result.loc[compact] = pd.to_datetime(text.loc[compact], format="%Y%m%d", errors="coerce")
    return result.dt.normalize()


def _normalize_key(series: pd.Series) -> pd.Series:
    """统一 Excel 关联键格式，去掉空格和数字文本的 .0 后缀。"""
    return series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True).fillna("")


def _format_day_label(value: pd.Timestamp) -> str:
    """把日期转成页面展示的 YYYY/M/D 文本。"""
    if pd.isna(value):
        return ""
    return f"{value.year}/{value.month}/{value.day}"


def _dimension_columns(config: AppConfig) -> list[str]:
    """返回统一明细维度列。"""
    return [
        config.date_column,
        config.plan_aggregate_column,
        config.new_channel_column,
        config.channel_type_column,
        config.line_column,
        config.sku_product_name_column,
        config.brand_column,
    ]


def _metric_columns(config: AppConfig) -> list[str]:
    """返回统一明细基础指标列。"""
    return [
        config.ad_cost_column,
        config.ad_impression_column,
        config.ad_click_column,
        config.ad_order_row_column,
        config.ad_gmv_column,
        config.ad_new_customer_column,
        config.ad_cart_column,
    ]
