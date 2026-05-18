"""
标签检验表看板的工作表和字段配置。

包含三个标签页的数据配置：
  - 关键词标签检验：关键词数据源 + 关键词打标
  - 人群标签检验：人群数据源 + 人群打标
  - SKU标签检验：站内外数据源 + 商品打标
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """标签检验表使用的工作表与字段配置。"""

    # ===== 关键词相关 — Excel 工作表名 =====
    keyword_fact_sheet: str = "关键词数据源"
    keyword_tag_sheet: str = "关键词打标"

    # ===== 关键词相关 — 源数据列名 =====
    keyword_column: str = "关键词"                # 关联键（两表同名）
    keyword_category_column: str = "词性分类"      # 来自关键词打标
    keyword_cost_column: str = "花费"              # 来自关键词数据源

    # ===== 关键词相关 — UI 展示列名 =====
    display_keyword_category_column: str = "词性分类"
    display_keyword_cost_column: str = "广告费用"

    # ===== 人群相关 — Excel 工作表名 =====
    audience_fact_sheet: str = "人群数据源"
    audience_tag_sheet: str = "人群打标"

    # ===== 人群相关 — 源数据列名 =====
    audience_name_column: str = "人群名称"          # 关联键（两表同名）
    audience_category_column: str = "人群分类"       # 来自人群打标
    audience_cost_column: str = "花费"               # 来自人群数据源

    # ===== 人群相关 — UI 展示列名 =====
    display_audience_category_column: str = "人群分类"
    display_audience_cost_column: str = "广告费用"

    # ===== SKU 相关 — Excel 工作表名 =====
    sku_fact_sheet: str = "站内外数据源"
    sku_tag_sheet: str = "商品打标"

    # ===== SKU 相关 — 源数据列名 =====
    # 注意：SKU 的关联键在两张表中列名不同！
    sku_match_id_column: str = "京东skuID"          # 商品打标中的关联键
    sku_fact_id_column: str = "跟单SKU ID"          # 站内外数据源中的关联键
    sku_name_column: str = "商品名称"              # 商品打标中的商品名称
    sku_category_column: str = "新分类"             # 来自商品打标
    sku_cost_column: str = "花费"                   # 来自站内外数据源

    # ===== SKU 相关 — UI 展示列名 =====
    display_sku_category_column: str = "新分类"
    display_sku_name_column: str = "商品名称"
    display_sku_cost_column: str = "广告费用"

    # ===== 通用常量 =====
    blank_category: str = "(空白)"                  # 空白分类的占位文本

    @property
    def required_source_sheets(self) -> dict[str, str]:
        """返回标签检验表需要从业务数据源 workbook 读取的工作表。

        Returns:
            别名到业务数据源 sheet 名的映射
        """
        return {
            "keyword_fact": self.keyword_fact_sheet,
            "audience_fact": self.audience_fact_sheet,
            "sku_fact": self.sku_fact_sheet,
        }

    @property
    def required_tag_sheets(self) -> dict[str, str]:
        """返回标签检验表需要从打标 workbook 读取的工作表。

        Returns:
            别名到打标 sheet 名的映射
        """
        return {
            "keyword_tag": self.keyword_tag_sheet,
            "audience_tag": self.audience_tag_sheet,
            "sku_tag": self.sku_tag_sheet,
        }

    @property
    def source_usecols(self) -> dict[str, list[str]]:
        """返回业务数据源按需读取的列配置。

        标签检验表只需要关联键和花费列。显式限制列范围可以减少大型 xlsx
        的解析、内存占用和页面等待时间。

        Returns:
            别名到列名列表的映射
        """
        return {
            "keyword_fact": [self.keyword_column, self.keyword_cost_column],
            "audience_fact": [self.audience_name_column, self.audience_cost_column],
            "sku_fact": [self.sku_fact_id_column, self.sku_cost_column],
        }

    @property
    def tag_usecols(self) -> dict[str, list[str]]:
        """返回打标 workbook 按需读取的列配置。

        Returns:
            别名到列名列表的映射
        """
        return {
            "keyword_tag": [self.keyword_column, self.keyword_category_column],
            "audience_tag": [self.audience_name_column, self.audience_category_column],
            "sku_tag": [
                self.sku_match_id_column,
                self.sku_category_column,
                self.sku_name_column,
            ],
        }


DEFAULT_CONFIG = AppConfig()
