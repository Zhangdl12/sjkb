"""
标签检验表的一次性加载与缓存服务。

页面层只负责渲染，真正耗时的 Excel 读取、关联计算、树表构造都集中在这里。
缓存粒度直接落在最终树形结果上，避免 Streamlit 为几十万行中间 DataFrame
反复做哈希和序列化。
"""
from dataclasses import dataclass

import pandas as pd
import streamlit as st

from app.core.loader import load_excel_sheets
from app.dashboards.tag_validation.config import AppConfig
from app.dashboards.tag_validation.fast_loader import (
    CostSummarySpec,
    load_cost_summary_sheets,
)
from app.dashboards.tag_validation.processor import (
    build_audience_dataset,
    build_keyword_dataset,
    build_sku_dataset,
)
from app.dashboards.tag_validation.tree_builder import (
    AudienceTreePayload,
    KeywordTreePayload,
    SkuTreePayload,
    build_audience_tree_payload,
    build_keyword_tree_payload,
    build_sku_tree_payload,
)


@dataclass(frozen=True)
class TagValidationPayloads:
    """标签检验表三类树表的最终渲染载荷。

    Attributes:
        keyword: 关键词标签检验树表载荷
        audience: 人群标签检验树表载荷
        sku: SKU 标签检验树表载荷
    """

    keyword: KeywordTreePayload
    audience: AudienceTreePayload
    sku: SkuTreePayload


@st.cache_data(show_spinner=False)
def load_tag_validation_payloads(
    _source_bytes: bytes,
    source_name: str,
    source_token: str,
    _tag_bytes: bytes,
    tag_source_name: str,
    tag_source_token: str,
) -> TagValidationPayloads:
    """一次性读取并计算关键词、人群、SKU 三类标签检验结果。

    Args:
        _source_bytes: 业务数据源 Excel 字节。参数名前缀为下划线，避免 Streamlit
            对大文件字节做缓存哈希；真正的失效依据是 source_token。
        source_name: 业务数据源文件名，用于缓存键和问题定位。
        source_token: 业务数据源内容哈希，文件变化时缓存自动失效。
        _tag_bytes: 打标 Excel 字节。参数名前缀为下划线，避免大文件字节哈希。
        tag_source_name: 打标文件名，用于缓存键和问题定位。
        tag_source_token: 打标文件内容哈希，文件变化时缓存自动失效。

    Returns:
        三类标签检验的最终树表载荷。页面切换单选项时直接复用这些小结果，
        不再重新解析 Excel 或重新合并几十万行明细。
    """
    _ = source_name, source_token, tag_source_name, tag_source_token
    config = AppConfig()

    # 业务数据源很大，这里直接从 xlsx XML 流中按键汇总花费，避免构造几十万行明细表。
    source_tables = load_cost_summary_sheets(
        _source_bytes,
        _build_fact_summary_specs(config),
    )
    # 打标 workbook 很小，继续用通用读取逻辑，代码更简单且性能足够。
    tag_tables = load_excel_sheets(
        _tag_bytes,
        config.required_tag_sheets,
        config.tag_usecols,
    )

    return build_tag_validation_payloads({**source_tables, **tag_tables}, config)


def _build_fact_summary_specs(config: AppConfig) -> dict[str, CostSummarySpec]:
    """构造三张事实表的流式费用汇总配置。

    Args:
        config: 标签检验表字段配置

    Returns:
        别名到 CostSummarySpec 的映射，供 fast_loader 定位 sheet、关联键和花费列
    """
    return {
        "keyword_fact": CostSummarySpec(
            sheet_name=config.keyword_fact_sheet,
            key_column=config.keyword_column,
            cost_column=config.keyword_cost_column,
        ),
        "audience_fact": CostSummarySpec(
            sheet_name=config.audience_fact_sheet,
            key_column=config.audience_name_column,
            cost_column=config.audience_cost_column,
        ),
        "sku_fact": CostSummarySpec(
            sheet_name=config.sku_fact_sheet,
            key_column=config.sku_fact_id_column,
            cost_column=config.sku_cost_column,
        ),
    }


def build_tag_validation_payloads(
    tables: dict[str, pd.DataFrame],
    config: AppConfig,
) -> TagValidationPayloads:
    """把已读取的六张源表加工成三类树表载荷。

    Args:
        tables: 包含 keyword_fact、keyword_tag、audience_fact、audience_tag、
            sku_fact、sku_tag 的 DataFrame 字典
        config: 标签检验表字段配置

    Returns:
        三类标签检验的树表载荷，供页面按当前选择渲染
    """
    # 先生成三类明细，再统一构造成 AgGrid 需要的 path 树形数据。
    keyword_df = build_keyword_dataset(tables, config)
    audience_df = build_audience_dataset(tables, config)
    sku_df = build_sku_dataset(tables, config)

    return TagValidationPayloads(
        keyword=build_keyword_tree_payload(keyword_df, [], config),
        audience=build_audience_tree_payload(audience_df, [], config),
        sku=build_sku_tree_payload(sku_df, [], config),
    )
