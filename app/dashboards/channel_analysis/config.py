from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppConfig:
    # ===== 工作表 =====
    ad_sheet: str = "数据中心-产品数据"
    plan_sheet: str = "计划类型匹配表"
    sku_sheet: str = "商品匹配表"

    required_sheets: dict[str, str] = field(
        default_factory=lambda: {
            "ad": "数据中心-产品数据",
            "plan": "计划类型匹配表",
            "sku": "商品匹配表",
        }
    )

    # ===== 原始字段 =====
    ad_date_column: str = "日期"
    ad_plan_type_column: str = "计划类型"
    ad_sku_id_column: str = "跟单SKU ID"
    ad_product_name_column: str = "跟单SKU名称"
    ad_cost_column: str = "总费用"
    ad_order_row_column: str = "总订单行"
    ad_gmv_column: str = "总订单金额"
    ad_click_column: str = "点击数"
    ad_impression_column: str = "展现数"
    ad_new_customer_column: str = "下单新客"

    plan_type_column: str = "计划类型"
    plan_aggregate_column: str = "计划聚合"
    new_channel_column: str = "新产品渠道"
    channel_type_column: str = "渠道类型"

    sku_id_column: str = "京东skuID"
    sku_product_name_column: str = "商品名称"
    category_column: str = "分类"
    brand_column: str = "品牌"

    # ===== 派生字段 =====
    date_column: str = "Date"
    year_column: str = "年"
    quarter_label_column: str = "季度"
    quarter_sort_column: str = "季度排序"
    month_label_column: str = "月"
    month_sort_column: str = "月排序值"
    week_label_column: str = "周"
    week_sort_column: str = "周排序值"
    day_label_column: str = "日"
    period_label_column: str = "周期"
    period_sort_column: str = "周期排序"

    unknown_text: str = "未知"

    period_tabs: tuple[tuple[str, str], ...] = (
        ("年", "year"),
        ("季度", "quarter"),
        ("月", "month"),
        ("周", "week"),
        ("日", "day"),
    )

    display_columns: list[str] = field(
        default_factory=lambda: [
            "周期",
            "新产品渠道",
            "广告费用",
            "花费占比%",
            "广告订单行",
            "广告GMV",
            "广告GMV占比",
            "广告ROI",
            "ROI环比",
            "广告CPC",
            "广告CVR",
            "广告CTR",
            "广告新客",
            "广告新客成本",
        ]
    )

    @property
    def source_usecols(self) -> dict[str, list[str]]:
        """返回渠道分析需要读取的最小列集合。

        这些字段覆盖广告指标、计划打标、商品打标和页面筛选展示。只读必要列
        可以显著减少大型 Excel 的解析成本。

        Returns:
            别名到列名列表的映射，传给 pandas.read_excel(usecols=...)。
        """
        return {
            "ad": [
                self.ad_date_column,
                self.ad_plan_type_column,
                self.ad_sku_id_column,
                self.ad_product_name_column,
                self.ad_cost_column,
                self.ad_order_row_column,
                self.ad_gmv_column,
                self.ad_click_column,
                self.ad_impression_column,
                self.ad_new_customer_column,
            ],
            "plan": [
                self.plan_type_column,
                self.plan_aggregate_column,
                self.new_channel_column,
                self.channel_type_column,
            ],
            "sku": [
                self.sku_id_column,
                self.sku_product_name_column,
                self.category_column,
                self.brand_column,
            ],
        }


DEFAULT_CONFIG = AppConfig()
