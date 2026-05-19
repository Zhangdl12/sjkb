"""CPS 分析最终展示结果服务层。"""
from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st

from app.core.filters import FilterField, apply_filters
from app.core.loader import load_excel_sheets
from app.dashboards.cps_analysis.config import AppConfig
from app.dashboards.cps_analysis.processor import build_cps_analysis_dataset
from app.dashboards.cps_analysis.tree_builder import build_cps_tree_summary


CPS_ANALYSIS_PAYLOAD_CACHE_VERSION = "cps_analysis_tree_v1"
DATASET_TABLE_KEY = "dataset"


@dataclass(frozen=True)
class CpsAnalysisPayload:
    """CPS 分析当前筛选条件下的最终展示载荷。

    Attributes:
        tree_df: “团长 > 日期 > 产品”树形汇总表。
    """

    tree_df: pd.DataFrame


@st.cache_data(show_spinner=False)
def load_cps_analysis_dataset(
    _source_bytes: bytes,
    source_name: str,
    source_token: str,
    _tag_bytes: bytes,
    tag_source_name: str,
    tag_source_token: str,
) -> pd.DataFrame:
    """读取当前 Excel 数据源并缓存 CPS 分析明细。

    Args:
        _source_bytes: 业务数据源 Excel 字节。
        source_name: 业务数据源文件名。
        source_token: 业务数据源内容 token。
        _tag_bytes: 打标 Excel 字节。
        tag_source_name: 打标文件名。
        tag_source_token: 打标文件内容 token。

    Returns:
        完成商品打标和时间字段补充的 CPS 分析明细表。
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
    return build_cps_analysis_dataset({**source_tables, **tag_tables}, config)


@st.cache_data(show_spinner=False)
def load_cps_analysis_payload(
    _source_bytes: bytes,
    source_name: str,
    source_token: str,
    _tag_bytes: bytes,
    tag_source_name: str,
    tag_source_token: str,
    filter_summary: tuple[tuple[str, tuple[Any, ...]], ...],
    payload_version: str = CPS_ANALYSIS_PAYLOAD_CACHE_VERSION,
) -> CpsAnalysisPayload:
    """读取并缓存当前筛选条件对应的最终展示表。

    Args:
        _source_bytes: 业务数据源 Excel 字节。
        source_name: 业务数据源文件名。
        source_token: 业务数据源内容 token。
        _tag_bytes: 打标 Excel 字节。
        tag_source_name: 打标文件名。
        tag_source_token: 打标文件内容 token。
        filter_summary: 已归一化的筛选摘要，作为缓存 key 的一部分。
        payload_version: 缓存版本号，树表结构调整时用于刷新旧缓存。

    Returns:
        当前筛选条件下的 CPS 分析展示载荷。
    """
    _ = payload_version
    config = AppConfig()
    dataset = load_cps_analysis_dataset(
        _source_bytes,
        source_name,
        source_token,
        _tag_bytes,
        tag_source_name,
        tag_source_token,
    )
    selections = _restore_selections(filter_summary)
    return build_cps_analysis_payload(
        {DATASET_TABLE_KEY: dataset},
        selections,
        build_filter_fields(config),
        config,
    )


def build_cps_analysis_payload(
    tables: dict[str, pd.DataFrame],
    selections: dict[str, Any],
    filter_fields: tuple[FilterField, ...],
    config: AppConfig,
) -> CpsAnalysisPayload:
    """按当前筛选生成 CPS 分析最终展示载荷。

    Args:
        tables: 包含统一明细表的字典，也兼容传入原始表现场构建。
        selections: 侧边栏筛选条件。
        filter_fields: 筛选字段声明。
        config: CPS 分析字段配置。

    Returns:
        CPS 分析页面最终展示载荷。
    """
    dataset = _resolve_dataset(tables, config)
    filtered_df = apply_filters(dataset, selections, filter_fields)
    if filtered_df.empty:
        return _empty_payload(config)
    return CpsAnalysisPayload(tree_df=build_cps_tree_summary(filtered_df, config))


def build_filter_fields(config: AppConfig) -> tuple[FilterField, ...]:
    """构造 CPS 分析侧边栏筛选字段。

    Args:
        config: CPS 分析字段配置。

    Returns:
        筛选字段声明元组，顺序决定侧边栏联动顺序。
    """
    return (
        FilterField(config.year_column, group="时间", sort_values=True, control="single_select", default_latest=True),
        FilterField(config.quarter_label_column, group="时间", sort_values=True),
        FilterField(config.month_label_column, group="时间", sort_values=True),
        FilterField(config.week_label_column, group="时间", sort_values=True),
        FilterField(config.day_label_column, label="日期", group="时间", sort_values=True),
        FilterField(config.leader_column, label="团长", group="业务"),
        FilterField(config.brand_column, group="业务"),
        FilterField(config.product_name_column, label="商品名称", group="业务"),
    )


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


def _resolve_dataset(tables: dict[str, pd.DataFrame], config: AppConfig) -> pd.DataFrame:
    """从输入表集合中解析统一明细表。

    Args:
        tables: 服务层传入的表集合。
        config: CPS 分析字段配置。

    Returns:
        CPS 分析统一明细表。
    """
    if DATASET_TABLE_KEY in tables:
        return tables[DATASET_TABLE_KEY]
    return build_cps_analysis_dataset(tables, config)


def _empty_payload(config: AppConfig) -> CpsAnalysisPayload:
    """构造空载荷，保证页面和测试稳定访问 tree_df。

    Args:
        config: CPS 分析字段配置。

    Returns:
        空的 CPS 分析载荷。
    """
    return CpsAnalysisPayload(tree_df=pd.DataFrame(columns=[*config.tree_columns, "path"]))


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
