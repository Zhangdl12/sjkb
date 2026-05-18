"""
标签检验表看板的数据加载辅助函数。

SourceTables         — 关键词检验需要的事实表和打标表
AudienceSourceTables — 人群检验需要的事实表和打标表
SkuSourceTables      — SKU 检验需要的事实表和打标表
"""
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SourceTables:
    """关键词标签检验使用的命名源表集合。

    Attributes:
        keyword_fact: 来自业务数据源 workbook 的“关键词数据源”sheet
        keyword_tag: 来自打标 workbook 的“关键词打标”sheet
    """
    keyword_fact: pd.DataFrame
    keyword_tag: pd.DataFrame


@dataclass(frozen=True)
class AudienceSourceTables:
    """人群标签检验使用的命名源表集合。

    Attributes:
        audience_fact: 来自业务数据源 workbook 的“人群数据源”sheet
        audience_tag: 来自打标 workbook 的“人群打标”sheet
    """
    audience_fact: pd.DataFrame
    audience_tag: pd.DataFrame


@dataclass(frozen=True)
class SkuSourceTables:
    """SKU 标签检验使用的命名源表集合。

    Attributes:
        sku_fact: 来自业务数据源 workbook 的“站内外数据源”sheet
        sku_tag: 来自打标 workbook 的“商品打标”sheet
    """
    sku_fact: pd.DataFrame
    sku_tag: pd.DataFrame
