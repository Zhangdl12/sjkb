"""
标签检验表看板的数据加载辅助函数。

SourceTables       — 关键词检验需要的两张工作表
AudienceSourceTables — 人群检验需要的两张工作表
SkuSourceTables    — SKU检验需要的两张工作表
"""
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SourceTables:
    """关键词标签检验使用的命名源表集合。"""
    keyword_match: pd.DataFrame   # 关键词匹配表
    keyword_fact: pd.DataFrame    # 数据中心-关键词数据


@dataclass(frozen=True)
class AudienceSourceTables:
    """人群标签检验使用的命名源表集合。"""
    audience_match: pd.DataFrame  # 人群匹配表
    audience_fact: pd.DataFrame   # 数据中心-店铺人群数据


@dataclass(frozen=True)
class SkuSourceTables:
    """SKU 标签检验使用的命名源表集合。"""
    sku_match: pd.DataFrame       # 商品匹配表
    sku_fact: pd.DataFrame        # 数据中心-产品数据
