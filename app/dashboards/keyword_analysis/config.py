"""关键词分析页面的工作表、字段和展示配置。"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppConfig:
    """集中维护关键词分析使用的 Excel 表名、字段名和展示列。

    Args:
        无。当前配置使用 dataclass 默认值初始化。

    Returns:
        配置对象本身，供 processor、metrics、service 和 UI 层复用。
    """

    # ===== 业务数据源工作表 =====
    keyword_sheet: str = "关键词数据源"

    required_sheets: dict[str, str] = field(
        default_factory=lambda: {
            "keyword_fact": "关键词数据源",
        }
    )

    # ===== 打标工作表 =====
    keyword_tag_sheet: str = "关键词打标"
    channel_tag_sheet: str = "渠道打标"
    sku_tag_sheet: str = "商品打标"

    required_tag_sheets: dict[str, str] = field(
        default_factory=lambda: {
            "keyword_tag": "关键词打标",
            "channel_tag": "渠道打标",
            "sku_tag": "商品打标",
        }
    )

    # ===== 关键词事实表原始字段 =====
    fact_date_column: str = "日期"
    fact_scene_column: str = "营销场景"
    fact_sku_column: str = "跟单SKU ID"
    fact_sku_name_column: str = "跟单SKU名称"
    fact_keyword_column: str = "关键词"
    fact_cost_column: str = "花费"
    fact_impression_column: str = "展现数"
    fact_click_column: str = "点击数"
    fact_order_row_column: str = "总订单行"
    fact_gmv_column: str = "总订单金额"
    fact_cart_column: str = "总加购数"
    fact_new_customer_column: str = "下单新客数"

    # ===== 关键词打标字段 =====
    keyword_column: str = "关键词"
    keyword_category_column: str = "词性分类"
    keyword_second_category_column: str = "词性二级分类"

    # ===== 渠道打标字段 =====
    channel_scene_column: str = "营销场景"
    plan_aggregate_column: str = "计划聚合"
    new_channel_column: str = "新产品渠道"
    channel_type_column: str = "渠道类型"

    # ===== 商品打标字段 =====
    sku_id_column: str = "京东skuID"
    sku_product_name_column: str = "商品名称"
    brand_column: str = "品牌"
    sku_category_column: str = "新分类"
    sku_second_category_column: str = "商品二级分类"
    stage_column: str = "段位"

    # ===== 归一化维度字段 =====
    date_column: str = "Date"
    year_column: str = "年"
    quarter_label_column: str = "季度"
    quarter_sort_column: str = "季度排序"
    month_label_column: str = "月"
    month_sort_column: str = "月排序值"
    week_label_column: str = "周"
    week_sort_column: str = "周排序值"
    day_label_column: str = "日"
    line_column: str = "品线分类"

    # ===== 归一化指标字段 =====
    ad_cost_column: str = "广告费用"
    ad_impression_column: str = "广告展现"
    ad_click_column: str = "广告点击"
    ad_order_row_column: str = "广告订单行"
    ad_gmv_column: str = "广告GMV"
    ad_new_customer_column: str = "广告新客"
    ad_cart_column: str = "广告加购数"

    # ===== 通用占位 =====
    blank_text: str = "(空白)"
    unknown_text: str = "未知"

    # ===== 展示列 =====
    classification_columns: list[str] = field(
        default_factory=lambda: [
            "词性分类",
            "词性二级分类",
            "关键词",
            "月",
            "广告费用",
            "花费占比%",
            "ROI-kw",
            "CPC-kw",
            "CTR-kw",
            "点击数",
            "总订单金额",
        ]
    )
    total_columns: list[str] = field(
        default_factory=lambda: [
            "词性分类",
            "词性二级分类",
            "关键词",
            "广告费用",
            "花费占比%",
            "ROI-kw",
            "CPC-kw",
            "CTR-kw",
            "点击数",
            "总订单金额",
        ]
    )
    time_columns: list[str] = field(
        default_factory=lambda: [
            "词性分类",
            "词性二级分类",
            "关键词",
            "周",
            "日",
            "广告展现",
            "广告点击",
            "广告费用",
            "广告订单行",
            "广告GMV",
            "广告新客",
            "广告加购数",
            "广告商品单价",
            "广告CPC",
            "广告CTR",
            "广告CVR",
            "广告ROI",
            "广告加购率",
            "广告CPA",
            "广告新客成本",
            "广告总加购成本",
            "花费占比%",
            "广告GMV占比",
        ]
    )

    @property
    def source_usecols(self) -> dict[str, list[str]]:
        """返回关键词分析事实表的最小读取列。

        Returns:
            业务数据源别名到字段列表的映射。
        """
        return {
            "keyword_fact": [
                self.fact_date_column,
                self.fact_scene_column,
                self.fact_sku_column,
                self.fact_sku_name_column,
                self.fact_keyword_column,
                self.fact_impression_column,
                self.fact_click_column,
                self.fact_cost_column,
                self.fact_order_row_column,
                self.fact_gmv_column,
                self.fact_cart_column,
                self.fact_new_customer_column,
            ],
        }

    @property
    def tag_usecols(self) -> dict[str, list[str]]:
        """返回打标文件的基础读取列。

        Returns:
            打标表别名到字段列表的映射。可选列由 service 层按真实表头补充。
        """
        return {
            "keyword_tag": [
                self.keyword_column,
                self.keyword_category_column,
            ],
            "channel_tag": [
                self.channel_scene_column,
                self.plan_aggregate_column,
                self.new_channel_column,
                self.channel_type_column,
            ],
            "sku_tag": [
                self.sku_id_column,
                self.sku_product_name_column,
                self.brand_column,
                self.sku_category_column,
            ],
        }


DEFAULT_CONFIG = AppConfig()
