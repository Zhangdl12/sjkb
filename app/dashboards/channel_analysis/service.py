"""渠道分析最终展示结果服务层。

本模块把 Excel 读取、统一明细构建、筛选和最终展示表汇总集中到服务层。
页面层只负责收集筛选条件和渲染当前视图，避免在切换展示方式时重复构造所有大表。
"""
from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd
import streamlit as st

from app.core.filters import FilterField, apply_filters
from app.core.loader import load_excel_sheets
from app.dashboards.channel_analysis import metrics as channel_metrics
from app.dashboards.channel_analysis.config import AppConfig
from app.dashboards.channel_analysis.processor import build_channel_analysis_dataset
from app.dashboards.channel_analysis.tree_builder import (
    add_category_tree_path,
    build_category_tree_summary,
    build_channel_tree_summary,
    build_time_tree_summary,
)


ChannelAnalysisView = Literal["分类汇总", "时间渠道"]
CHANNEL_ANALYSIS_PAYLOAD_CACHE_VERSION = "channel_summary_month_tree_v6"


@dataclass(frozen=True)
class ChannelAnalysisPayload:
    """渠道分析当前视图的最终渲染载荷。

    Attributes:
        channel_df: 带 path 的新产品渠道/月树形表，仅分类汇总视图使用。
        category_df: 带 path 的品线/商品/渠道/月树形表，仅分类汇总视图使用。
        time_df: 月/日/新产品渠道汇总表，仅时间渠道视图使用。
        total_df: 分类汇总总计表，仅分类汇总视图使用。
    """

    channel_df: pd.DataFrame
    category_df: pd.DataFrame
    time_df: pd.DataFrame
    total_df: pd.DataFrame


@st.cache_data(show_spinner=False)
def load_channel_analysis_dataset(
    _source_bytes: bytes,
    source_name: str,
    source_token: str,
    _tag_bytes: bytes,
    tag_source_name: str,
    tag_source_token: str,
) -> pd.DataFrame:
    """读取当前 Excel 数据源并缓存渠道分析统一明细。

    Args:
        _source_bytes: 业务数据源 Excel 字节，真实缓存失效依赖 source_token。
        source_name: 业务数据源文件名，用于缓存键和错误定位。
        source_token: 业务数据源内容 token，文件变化时缓存失效。
        _tag_bytes: 打标 Excel 字节，真实缓存失效依赖 tag_source_token。
        tag_source_name: 打标文件名，用于缓存键和错误定位。
        tag_source_token: 打标文件内容 token，文件变化时缓存失效。

    Returns:
        已完成四类广告来源归一化、渠道打标、商品打标和时间字段补充的明细表。
    """
    _ = source_name, source_token, tag_source_name, tag_source_token
    config = AppConfig()
    source_tables = load_excel_sheets(
        _source_bytes,
        config.required_sheets,
        config.source_usecols,
    )
    tag_tables = load_excel_sheets(
        _tag_bytes,
        config.required_tag_sheets,
        config.tag_usecols,
    )
    return build_channel_analysis_dataset({**source_tables, **tag_tables}, config)


@st.cache_data(show_spinner=False)
def load_channel_analysis_payload(
    _source_bytes: bytes,
    source_name: str,
    source_token: str,
    _tag_bytes: bytes,
    tag_source_name: str,
    tag_source_token: str,
    filter_summary: tuple[tuple[str, tuple[Any, ...]], ...],
    view_type: ChannelAnalysisView,
    payload_version: str = CHANNEL_ANALYSIS_PAYLOAD_CACHE_VERSION,
) -> ChannelAnalysisPayload:
    """读取并缓存当前筛选与视图对应的最终展示表。

    Args:
        _source_bytes: 业务数据源 Excel 字节，参数名前缀用于避免大字节哈希。
        source_name: 业务数据源文件名，用于缓存键和排查问题。
        source_token: 业务数据源内容 token。
        _tag_bytes: 打标 Excel 字节，参数名前缀用于避免大字节哈希。
        tag_source_name: 打标文件名，用于缓存键和排查问题。
        tag_source_token: 打标文件内容 token。
        filter_summary: 已归一化的筛选摘要，作为最终结果缓存 key 的一部分。
        view_type: 当前用户选择的展示视图。
        payload_version: 缓存版本号。树表结构调整后提升版本，强制失效旧缓存。

    Returns:
        当前视图需要的最终展示表；未使用的表保持为空表，避免无关计算。
    """
    _ = payload_version
    config = AppConfig()
    dataset = load_channel_analysis_dataset(
        _source_bytes,
        source_name,
        source_token,
        _tag_bytes,
        tag_source_name,
        tag_source_token,
    )
    selections = _restore_selections(filter_summary)
    return build_channel_analysis_payload(
        {DATASET_TABLE_KEY: dataset},
        selections,
        _build_filter_fields(config),
        view_type,
        config,
    )


DATASET_TABLE_KEY = "dataset"


def build_channel_analysis_payload(
    tables: dict[str, pd.DataFrame],
    selections: dict[str, Any],
    filter_fields: tuple[FilterField, ...],
    view_type: ChannelAnalysisView,
    config: AppConfig,
) -> ChannelAnalysisPayload:
    """按当前筛选和视图生成最终展示载荷。

    Args:
        tables: 包含统一明细表的字典；也兼容传入原始来源表并现场构建明细。
        selections: 侧边栏筛选条件，语义与 apply_filters 保持一致。
        filter_fields: 筛选字段声明，决定筛选应用顺序。
        view_type: 当前视图，只计算这个视图需要的表。
        config: 渠道分析配置。

    Returns:
        当前视图需要的最终表集合，未命中的视图表为空 DataFrame。
    """
    dataset = _resolve_dataset(tables, config)
    filtered_df = apply_filters(dataset, selections, filter_fields)
    empty_payload = _empty_payload(config)
    if filtered_df.empty:
        return empty_payload

    if view_type == "分类汇总":
        channel_df = build_channel_tree_summary(filtered_df, config)
        category_df = build_category_tree_summary(filtered_df, config)
        total_df = channel_metrics.build_channel_total(filtered_df, config)
        return ChannelAnalysisPayload(
            channel_df=channel_df,
            category_df=category_df,
            time_df=empty_payload.time_df,
            total_df=total_df,
        )

    time_df = build_time_tree_summary(filtered_df, config)
    return ChannelAnalysisPayload(
        channel_df=empty_payload.channel_df,
        category_df=empty_payload.category_df,
        time_df=time_df,
        total_df=empty_payload.total_df,
    )


def build_filter_summary(selections: dict[str, Any]) -> tuple[tuple[str, tuple[Any, ...]], ...]:
    """把筛选条件转成稳定、可缓存的摘要。

    Args:
        selections: 页面侧边栏返回的筛选条件，值可能是单值、列表或空值。

    Returns:
        按字段名排序后的元组结构，可安全作为 st.cache_data 的普通参数。
    """
    return tuple(
        (column, tuple(_normalize_selection_values(values)))
        for column, values in sorted(selections.items(), key=lambda item: item[0])
    )


def _resolve_dataset(tables: dict[str, pd.DataFrame], config: AppConfig) -> pd.DataFrame:
    """从输入表集合中解析统一明细表。

    Args:
        tables: 服务层传入的表集合。
        config: 渠道分析配置。

    Returns:
        渠道分析统一明细表。
    """
    if DATASET_TABLE_KEY in tables:
        return tables[DATASET_TABLE_KEY]
    return build_channel_analysis_dataset(tables, config)


def _empty_payload(config: AppConfig) -> ChannelAnalysisPayload:
    """构造空载荷，保证页面和测试可以稳定访问四个表属性。"""
    return ChannelAnalysisPayload(
        channel_df=pd.DataFrame(columns=[config.new_channel_column, config.month_label_column, *config.summary_columns, "path"]),
        category_df=pd.DataFrame(
            columns=[
                config.line_column,
                config.sku_product_name_column,
                config.new_channel_column,
                config.month_label_column,
                *config.summary_columns,
                "path",
            ]
        ),
        time_df=pd.DataFrame(columns=config.time_columns),
        total_df=pd.DataFrame(columns=[config.new_channel_column, *config.summary_columns]),
    )


def _restore_selections(filter_summary: tuple[tuple[str, tuple[Any, ...]], ...]) -> dict[str, list[Any]]:
    """把缓存摘要还原为 apply_filters 可使用的筛选字典。"""
    return {column: list(values) for column, values in filter_summary}


def _normalize_selection_values(values: Any) -> list[Any]:
    """把单值或多值筛选统一成列表，并保持值顺序稳定。"""
    if values is None:
        return []
    if isinstance(values, list):
        return values
    if isinstance(values, tuple):
        return list(values)
    return [values]


def _build_filter_fields(config: AppConfig) -> tuple[FilterField, ...]:
    """构造服务层使用的筛选字段声明。

    页面模块文件名包含中文，不适合在服务层反向导入。这里保持与页面筛选字段相同的
    字段顺序，确保缓存服务和页面筛选语义一致。
    """
    return (
        FilterField(config.year_column, group="时间", sort_values=True, control="single_select", default_latest=True),
        FilterField(config.quarter_label_column, group="时间", sort_values=True),
        FilterField(config.month_label_column, group="时间", sort_values=True),
        FilterField(config.week_label_column, group="时间", sort_values=True),
        FilterField(config.day_label_column, label="日期", group="时间", sort_values=True),
        FilterField(config.channel_type_column, group="业务"),
        FilterField(config.new_channel_column, group="业务"),
        FilterField(config.plan_aggregate_column, label="计划聚合", group="业务"),
        FilterField(config.brand_column, group="业务"),
        FilterField(config.line_column, group="业务"),
        FilterField(config.sku_product_name_column, label="商品名称", group="业务"),
    )
