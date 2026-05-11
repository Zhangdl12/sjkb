"""
标签检验表看板的工作表和字段配置。

包含三个标签页的数据配置：
  - 关键词标签检验：关键词匹配表 + 数据中心-关键词数据
  - 人群标签检验：人群匹配表 + 数据中心-店铺人群数据
  - SKU标签检验：商品匹配表 + 数据中心-产品数据
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """标签检验表使用的工作表与字段配置。"""

    # ===== 关键词相关 — Excel 工作表名 =====
    keyword_match_sheet: str = "关键词匹配表"
    keyword_fact_sheet: str = "数据中心-关键词数据"

    # ===== 关键词相关 — 源数据列名 =====
    keyword_column: str = "关键词"                # 关联键（两表同名）
    keyword_category_column: str = "词性分类"      # 来自匹配表
    keyword_cost_column: str = "总费用"            # 来自事实表

    # ===== 关键词相关 — UI 展示列名 =====
    display_keyword_category_column: str = "关键词未分类"
    display_keyword_cost_column: str = "关键词费用"

    # ===== 人群相关 — Excel 工作表名 =====
    audience_match_sheet: str = "人群匹配表"
    audience_fact_sheet: str = "数据中心-店铺人群数据"

    # ===== 人群相关 — 源数据列名 =====
    audience_name_column: str = "人群名称"          # 关联键（两表同名）
    audience_category_column: str = "人群分类"       # 来自匹配表
    audience_cost_column: str = "总费用"             # 来自事实表

    # ===== 人群相关 — UI 展示列名 =====
    display_audience_category_column: str = "人群未分类"
    display_audience_cost_column: str = "人群费用"

    # ===== SKU 相关 — Excel 工作表名 =====
    sku_match_sheet: str = "商品匹配表"
    sku_fact_sheet: str = "数据中心-产品数据"

    # ===== SKU 相关 — 源数据列名 =====
    # 注意：SKU 的关联键在两张表中列名不同！
    sku_match_id_column: str = "京东skuID"          # 匹配表中的关联键
    sku_fact_id_column: str = "跟单SKU ID"          # 事实表中的关联键
    sku_name_column: str = "商品名称"              # 匹配表中的商品名称
    sku_category_column: str = "分类"               # 来自匹配表
    sku_cost_column: str = "总费用"                 # 来自事实表

    # ===== SKU 相关 — UI 展示列名 =====
    display_sku_category_column: str = "分类"
    display_sku_name_column: str = "商品名称"
    display_sku_cost_column: str = "广告费用"

    # ===== 通用常量 =====
    blank_category: str = "(空白)"                  # 空白分类的占位文本

    @property
    def required_sheets(self) -> dict[str, str]:
        """返回页面加载时需要的全部工作表（关键词 + 人群 + SKU 共 6 张）。"""
        return {
            "keyword_match": self.keyword_match_sheet,
            "keyword_fact": self.keyword_fact_sheet,
            "audience_match": self.audience_match_sheet,
            "audience_fact": self.audience_fact_sheet,
            "sku_match": self.sku_match_sheet,
            "sku_fact": self.sku_fact_sheet,
        }


DEFAULT_CONFIG = AppConfig()
