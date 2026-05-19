"""关键词分析数据归一化处理。"""
import pandas as pd

from app.dashboards.keyword_analysis.config import AppConfig
from app.dashboards.keyword_analysis.date_utils import (
    add_time_columns as _add_time_columns,
    normalize_key as _normalize_key,
    parse_date as _parse_date,
)


class DataProcessingError(Exception):
    """关键词分析数据无法加工时抛出的异常。"""


def build_keyword_analysis_dataset(
    tables: dict[str, pd.DataFrame],
    config: AppConfig,
) -> pd.DataFrame:
    """构建关键词分析统一明细表。

    Args:
        tables: 已读取的事实表和打标表，必须包含 keyword_fact、keyword_tag、channel_tag、sku_tag。
        config: 关键词分析字段配置。

    Returns:
        完成关键词、渠道、SKU 打标和时间字段补充后的明细 DataFrame。
    """
    try:
        keyword_map = _build_keyword_mapping(tables["keyword_tag"], config)
        channel_map = _build_channel_mapping(tables["channel_tag"], config)
        sku_map = _build_sku_mapping(tables["sku_tag"], config)
        result_df = _build_keyword_rows(
            tables["keyword_fact"],
            keyword_map,
            channel_map,
            sku_map,
            config,
        )
        result_df = _fill_dimensions(result_df, config)
        result_df = _fill_metrics(result_df, config)
        return _add_time_columns(result_df, config)
    except KeyError as exc:
        raise DataProcessingError(f"关键词分析缺少必要字段: {exc}") from exc
    except Exception as exc:
        raise DataProcessingError(f"关键词分析加工失败: {exc}") from exc


def _build_keyword_mapping(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """生成关键词到词性分类的去重映射表。

    Args:
        df: 关键词打标表。
        config: 关键词分析字段配置。

    Returns:
        带 `_keyword_key` 的关键词打标映射表。
    """
    columns = [config.keyword_column, config.keyword_category_column]
    if config.keyword_second_category_column in df.columns:
        columns.append(config.keyword_second_category_column)
    mapping_df = df[columns].copy()
    mapping_df["_keyword_key"] = _normalize_key(mapping_df[config.keyword_column])
    if config.keyword_second_category_column not in mapping_df.columns:
        mapping_df[config.keyword_second_category_column] = ""
    return mapping_df.drop_duplicates(subset=["_keyword_key"])


def _build_channel_mapping(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """生成营销场景到渠道标签的去重映射表。

    Args:
        df: 渠道打标表。
        config: 关键词分析字段配置。

    Returns:
        带 `_scene_key` 的渠道打标映射表。
    """
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
    """生成 SKU 到商品标签的去重映射表。

    Args:
        df: 商品打标表。
        config: 关键词分析字段配置。

    Returns:
        带 `_sku_key` 的商品打标映射表；可选字段不存在时补为空字符串。
    """
    columns = [
        config.sku_id_column,
        config.sku_product_name_column,
        config.brand_column,
        config.sku_category_column,
    ]
    for optional_column in [config.sku_second_category_column, config.stage_column]:
        if optional_column in df.columns:
            columns.append(optional_column)
    mapping_df = df[columns].copy()
    mapping_df["_sku_key"] = _normalize_key(mapping_df[config.sku_id_column])
    if config.sku_second_category_column not in mapping_df.columns:
        mapping_df[config.sku_second_category_column] = ""
    if config.stage_column not in mapping_df.columns:
        mapping_df[config.stage_column] = ""
    mapping_df = mapping_df.rename(columns={config.sku_category_column: config.line_column})
    return mapping_df.drop_duplicates(subset=["_sku_key"])


def _build_keyword_rows(
    df: pd.DataFrame,
    keyword_map: pd.DataFrame,
    channel_map: pd.DataFrame,
    sku_map: pd.DataFrame,
    config: AppConfig,
) -> pd.DataFrame:
    """把关键词事实表补齐所有分析维度和基础指标。

    Args:
        df: 关键词数据源事实表。
        keyword_map: 关键词打标映射表。
        channel_map: 渠道打标映射表。
        sku_map: 商品打标映射表。
        config: 关键词分析字段配置。

    Returns:
        统一后的关键词明细数据。
    """
    rows = pd.DataFrame(index=df.index)
    rows[config.date_column] = _parse_date(df[config.fact_date_column])
    rows[config.keyword_column] = _normalize_key(df[config.fact_keyword_column])
    rows[config.sku_product_name_column] = df[config.fact_sku_name_column]
    rows["_keyword_key"] = rows[config.keyword_column]
    rows["_scene_key"] = _normalize_key(df[config.fact_scene_column])
    rows["_sku_key"] = _normalize_key(df[config.fact_sku_column])

    rows = _merge_keyword_tags(rows, keyword_map, config)
    rows = _merge_channel_tags(rows, channel_map, config)
    rows = _merge_sku_tags(rows, sku_map, config)
    _copy_metric(rows, df, config.fact_cost_column, config.ad_cost_column)
    _copy_metric(rows, df, config.fact_impression_column, config.ad_impression_column)
    _copy_metric(rows, df, config.fact_click_column, config.ad_click_column)
    _copy_metric(rows, df, config.fact_order_row_column, config.ad_order_row_column)
    _copy_metric(rows, df, config.fact_gmv_column, config.ad_gmv_column)
    _copy_metric(rows, df, config.fact_new_customer_column, config.ad_new_customer_column)
    _copy_metric(rows, df, config.fact_cart_column, config.ad_cart_column)
    return rows


def _merge_keyword_tags(rows: pd.DataFrame, keyword_map: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """按关键词写入词性一级和二级分类。

    Args:
        rows: 关键词事实行。
        keyword_map: 关键词打标映射表。
        config: 关键词分析字段配置。

    Returns:
        合并词性标签后的 DataFrame。
    """
    result_df = rows.merge(keyword_map, on="_keyword_key", how="left", suffixes=("", "_tag"))
    result_df[config.keyword_category_column] = result_df[config.keyword_category_column].fillna(config.blank_text)
    result_df[config.keyword_second_category_column] = (
        result_df[config.keyword_second_category_column].fillna("").replace(config.blank_text, "")
    )
    return result_df.drop(
        columns=[config.keyword_column + "_tag", "_keyword_key"],
        errors="ignore",
    )


def _merge_channel_tags(rows: pd.DataFrame, channel_map: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """按营销场景写入计划聚合、新产品渠道和渠道类型。

    Args:
        rows: 关键词事实行。
        channel_map: 渠道打标映射表。
        config: 关键词分析字段配置。

    Returns:
        合并渠道标签后的 DataFrame。
    """
    result_df = rows.merge(channel_map, on="_scene_key", how="left", suffixes=("", "_tag"))
    return result_df.drop(
        columns=[config.channel_scene_column, "_scene_key"],
        errors="ignore",
    )


def _merge_sku_tags(rows: pd.DataFrame, sku_map: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """按 SKU 写入品线分类、商品名称、品牌和可选商品标签。

    Args:
        rows: 关键词事实行。
        sku_map: 商品打标映射表。
        config: 关键词分析字段配置。

    Returns:
        合并商品标签后的 DataFrame。
    """
    result_df = rows.merge(sku_map, on="_sku_key", how="left", suffixes=("", "_tag"))
    for column in [
        config.sku_product_name_column,
        config.brand_column,
        config.line_column,
        config.sku_second_category_column,
        config.stage_column,
    ]:
        tag_column = f"{column}_tag"
        if tag_column in result_df.columns:
            result_df[column] = result_df[tag_column].where(result_df[tag_column].notna(), result_df[column])
    return result_df.drop(
        columns=[
            "_sku_key",
            f"{config.sku_product_name_column}_tag",
            f"{config.brand_column}_tag",
            f"{config.line_column}_tag",
            f"{config.sku_second_category_column}_tag",
            f"{config.stage_column}_tag",
        ],
        errors="ignore",
    )


def _fill_dimensions(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """填充维度空值，避免筛选器和树表出现 NaN。

    Args:
        df: 待处理明细表。
        config: 关键词分析字段配置。

    Returns:
        维度空值已补齐的 DataFrame。
    """
    result_df = df.copy()
    text_columns = [
        config.keyword_column,
        config.keyword_category_column,
        config.plan_aggregate_column,
        config.new_channel_column,
        config.channel_type_column,
        config.line_column,
        config.sku_product_name_column,
        config.brand_column,
        config.sku_second_category_column,
        config.stage_column,
    ]
    for column in text_columns:
        if column not in result_df.columns:
            result_df[column] = ""
        fill_value = config.blank_text if column == config.keyword_category_column else config.unknown_text
        if column in {config.keyword_second_category_column, config.sku_second_category_column, config.stage_column}:
            fill_value = ""
        result_df[column] = result_df[column].fillna(fill_value).replace("", fill_value)
    result_df[config.keyword_second_category_column] = result_df[config.keyword_second_category_column].replace(config.unknown_text, "")
    return result_df


def _fill_metrics(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """把基础指标转为数值并补 0。

    Args:
        df: 待处理明细表。
        config: 关键词分析字段配置。

    Returns:
        指标列已数值化的 DataFrame。
    """
    result_df = df.copy()
    for column in _metric_columns(config):
        result_df[column] = pd.to_numeric(result_df[column], errors="coerce").fillna(0.0)
    return result_df


def _copy_metric(rows: pd.DataFrame, source_df: pd.DataFrame, source_column: str, target_column: str) -> None:
    """把来源指标列复制到统一指标列。

    Args:
        rows: 目标明细行。
        source_df: 原始事实表。
        source_column: 原始指标字段名。
        target_column: 统一指标字段名。

    Returns:
        None。函数直接修改 rows。
    """
    rows[target_column] = pd.to_numeric(source_df[source_column], errors="coerce").fillna(0.0)


def _metric_columns(config: AppConfig) -> list[str]:
    """返回关键词分析基础指标列。

    Args:
        config: 关键词分析字段配置。

    Returns:
        基础指标字段名列表。
    """
    return [
        config.ad_cost_column,
        config.ad_impression_column,
        config.ad_click_column,
        config.ad_order_row_column,
        config.ad_gmv_column,
        config.ad_new_customer_column,
        config.ad_cart_column,
    ]
