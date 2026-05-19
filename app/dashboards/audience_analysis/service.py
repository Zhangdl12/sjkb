"""人群分析最终展示结果服务层。"""

from dataclasses import dataclass
from io import BytesIO
from typing import Any, Literal

import pandas as pd
import streamlit as st

from app.core.filters import FilterField, apply_filters
from app.core.loader import load_excel_sheets
from app.dashboards.audience_analysis import metrics as audience_metrics
from app.dashboards.audience_analysis.config import AppConfig
from app.dashboards.audience_analysis.processor import build_audience_analysis_dataset
from app.dashboards.audience_analysis.tree_builder import (
    build_classification_tree_summary,
    build_time_tree_summary,
)


AudienceAnalysisView = Literal["人群分类", "时间渠道"]
AUDIENCE_ANALYSIS_PAYLOAD_CACHE_VERSION = "audience_analysis_v2_month_tree"
DATASET_TABLE_KEY = "dataset"
@dataclass(frozen=True)
class AudienceAnalysisPayload:
    """人群分析当前视图的最终展示载荷。

    Attributes:
        classification_df: 人群分类树表，仅人群分类视图使用。
        time_df: 时间渠道树表，仅时间渠道视图使用。
        total_df: 当前筛选范围总计表，仅人群分类视图使用。
    """

    classification_df: pd.DataFrame
    time_df: pd.DataFrame
    total_df: pd.DataFrame

@st.cache_data(show_spinner=False)
def load_audience_analysis_dataset(
    _source_bytes: bytes,
    source_name: str,
    source_token: str,
    _tag_bytes: bytes,
    tag_source_name: str,
    tag_source_token: str,
) -> pd.DataFrame:
    """读取当前 Excel 数据源并缓存人群分析统一明细。

    Args:
        _source_bytes: 业务数据源 Excel 字节。
        source_name: 业务数据源文件名。
        source_token: 业务数据源内容 token。
        _tag_bytes: 打标 Excel 字节。
        tag_source_name: 打标文件名。
        tag_source_token: 打标文件内容 token。

    Returns:
        完成打标和时间字段补充的人群分析明细表。
    """
    _ = source_name, source_token, tag_source_name, tag_source_token
    config = AppConfig()
    source_tables = load_excel_sheets(_source_bytes, config.required_sheets, config.source_usecols)
    tag_tables = load_excel_sheets(_tag_bytes, config.required_tag_sheets, _build_tag_usecols(_tag_bytes, config))
    return build_audience_analysis_dataset({**source_tables, **tag_tables}, config)

@st.cache_data(show_spinner=False)
def load_audience_analysis_payload(
    _source_bytes: bytes,
    source_name: str,
    source_token: str,
    _tag_bytes: bytes,
    tag_source_name: str,
    tag_source_token: str,
    filter_summary: tuple[tuple[str, tuple[Any, ...]], ...],
    view_type: AudienceAnalysisView,
    payload_version: str = AUDIENCE_ANALYSIS_PAYLOAD_CACHE_VERSION,
) -> AudienceAnalysisPayload:
    """读取并缓存当前筛选与视图对应的最终展示表。

    Args:
        _source_bytes: 业务数据源 Excel 字节。
        source_name: 业务数据源文件名。
        source_token: 业务数据源内容 token。
        _tag_bytes: 打标 Excel 字节。
        tag_source_name: 打标文件名。
        tag_source_token: 打标文件内容 token。
        filter_summary: 已归一化的筛选摘要，作为缓存 key 的一部分。
        view_type: 当前用户选择的展示视图。
        payload_version: 缓存版本号，结构调整时用于刷新旧缓存。

    Returns:
        当前视图需要的最终展示表。
    """
    _ = payload_version
    config = AppConfig()
    dataset = load_audience_analysis_dataset(
        _source_bytes,
        source_name,
        source_token,
        _tag_bytes,
        tag_source_name,
        tag_source_token,
    )
    selections = _restore_selections(filter_summary)
    return build_audience_analysis_payload(
        {DATASET_TABLE_KEY: dataset},
        selections,
        build_filter_fields(config, dataset),
        view_type,
        config,
    )


def build_audience_analysis_payload(
    tables: dict[str, pd.DataFrame],
    selections: dict[str, Any],
    filter_fields: tuple[FilterField, ...],
    view_type: AudienceAnalysisView,
    config: AppConfig,
) -> AudienceAnalysisPayload:
    """按当前筛选和视图生成人群分析最终展示载荷。

    Args:
        tables: 包含统一明细表的字典，也兼容传入原始表现场构建。
        selections: 侧边栏筛选条件。
        filter_fields: 筛选字段声明。
        view_type: 当前展示视图。
        config: 人群分析字段配置。

    Returns:
        人群分析页面最终展示载荷。
    """
    dataset = _resolve_dataset(tables, config)
    filtered_df = apply_filters(dataset, selections, filter_fields)
    empty_payload = _empty_payload(config)
    if filtered_df.empty:
        return empty_payload

    if view_type == "人群分类":
        return AudienceAnalysisPayload(
            classification_df=build_classification_tree_summary(filtered_df, config),
            time_df=empty_payload.time_df,
            total_df=audience_metrics.build_total(filtered_df, config),
        )

    return AudienceAnalysisPayload(
        classification_df=empty_payload.classification_df,
        time_df=build_time_tree_summary(filtered_df, config),
    total_df=empty_payload.total_df,
    )

def build_filter_fields(config: AppConfig, df: pd.DataFrame | None = None) -> tuple[FilterField, ...]:
    """构造人群分析侧边栏筛选字段。

    Args:
        config: 人群分析字段配置。
        df: 可选的人群分析明细，用于判断店铺级特殊字段是否存在有效值。

    Returns:
        筛选字段声明元组。
    """
    fields = [
        FilterField(config.year_column, group="时间", sort_values=True, control="single_select", default_latest=True),
        FilterField(config.quarter_label_column, group="时间", sort_values=True),
        FilterField(config.month_label_column, group="时间", sort_values=True),
        FilterField(config.week_label_column, group="时间", sort_values=True),
        FilterField(config.day_label_column, label="日期", group="时间", sort_values=True),
        FilterField(config.audience_category_column, group="人群"),
        FilterField(config.audience_name_column, group="人群"),
        FilterField(config.channel_type_column, group="业务"),
        FilterField(config.new_channel_column, group="业务"),
        FilterField(config.plan_aggregate_column, group="业务"),
        FilterField(config.brand_column, label="投放品牌", group="业务"),
        FilterField(config.line_column, label="品线分类", group="业务"),
        FilterField(config.sku_product_name_column, label="商品名称", group="业务"),
    ]
    optional_fields = [
        FilterField(config.sku_second_category_column, label="商品二级分类", group="可选"),
        FilterField(config.stage_column, label="段位", group="可选"),
    ]
    if df is None:
        fields.extend(optional_fields)
    else:
        fields.extend(field for field in optional_fields if _has_effective_values(df, field.column))
    return tuple(fields)


def build_filter_summary(selections: dict[str, Any]) -> tuple[tuple[str, tuple[Any, ...]], ...]:
    """把筛选条件转成稳定、可缓存的摘要。

    Args:
        selections: 页面侧边栏返回的筛选条件。

    Returns:
        按字段名排序后的元组结构。
    """
    return tuple(
        (column, tuple(_normalize_selection_values(values)))
        for column, values in sorted(selections.items(), key=lambda item: item[0])
    )


def _build_tag_usecols(_tag_bytes: bytes, config: AppConfig) -> dict[str, list[str]]:
    """根据打标文件真实表头补充可选读取列。

    Args:
        _tag_bytes: 打标 Excel 字节。
        config: 人群分析字段配置。

    Returns:
        包含可选列的 usecols 配置。
    """
    usecols = {alias: columns.copy() for alias, columns in config.tag_usecols.items()}
    excel_file = pd.ExcelFile(BytesIO(_tag_bytes))
    sheet_columns = {
        sheet_name: excel_file.parse(sheet_name, nrows=0).columns.tolist()
        for sheet_name in excel_file.sheet_names
    }
    sku_columns = sheet_columns.get(config.sku_tag_sheet, [])
    for optional_column in [config.sku_second_category_column, config.stage_column]:
        if optional_column in sku_columns:
            usecols["sku_tag"].append(optional_column)
    return usecols


def _resolve_dataset(tables: dict[str, pd.DataFrame], config: AppConfig) -> pd.DataFrame:
    """从输入表集合中解析统一明细表。

    Args:
        tables: 服务层传入的表集合。
        config: 人群分析字段配置。

    Returns:
        人群分析统一明细表。
    """
    if DATASET_TABLE_KEY in tables:
        return tables[DATASET_TABLE_KEY]
    return build_audience_analysis_dataset(tables, config)


def _empty_payload(config: AppConfig) -> AudienceAnalysisPayload:
    """构造空载荷，保证页面和测试稳定访问三个表属性。

    Args:
        config: 人群分析字段配置。

    Returns:
        空的人群分析载荷。
    """
    return AudienceAnalysisPayload(
        classification_df=pd.DataFrame(columns=[*config.classification_columns, "path"]),
        time_df=pd.DataFrame(columns=[*config.time_columns, "path"]),
        total_df=pd.DataFrame(columns=config.total_columns),
    )


def _restore_selections(filter_summary: tuple[tuple[str, tuple[Any, ...]], ...]) -> dict[str, list[Any]]:
    """把缓存摘要还原为 apply_filters 可用的筛选字典。

    Args:
        filter_summary: 缓存使用的筛选摘要。

    Returns:
        筛选字段到值列表的映射。
    """
    return {column: list(values) for column, values in filter_summary}


def _normalize_selection_values(values: Any) -> list[Any]:
    """把单值或多值筛选统一成列表。

    Args:
        values: 任意筛选值。

    Returns:
        列表形式的筛选值。
    """
    if values is None:
        return []
    if isinstance(values, list):
        return values
    if isinstance(values, tuple):
        return list(values)
    return [values]


def _has_effective_values(df: pd.DataFrame, column: str) -> bool:
    """判断可选字段是否存在有效筛选值。

    Args:
        df: 人群分析明细。
        column: 可选字段名。

    Returns:
        字段存在且包含非空、非未知值时返回 True。
    """
    if column not in df.columns:
        return False
    values = df[column].dropna().astype(str).str.strip()
    return bool(values.ne("").any())
