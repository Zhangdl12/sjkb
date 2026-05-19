from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppConfig:
    """渠道分析页面的工作表、字段和展示配置。"""

    # ===== 业务数据源工作表 =====
    station_sheet: str = "站内外数据源"
    cps_sheet: str = "CPS数据源"
    brand_sheet: str = "品专数据源"
    sitewide_sheet: str = "全站营销数据源"

    required_sheets: dict[str, str] = field(
        default_factory=lambda: {
            "station": "站内外数据源",
            "cps": "CPS数据源",
            "brand": "品专数据源",
            "sitewide": "全站营销数据源",
        }
    )

    # ===== 打标工作表 =====
    channel_tag_sheet: str = "渠道打标"
    sku_tag_sheet: str = "商品打标"

    required_tag_sheets: dict[str, str] = field(
        default_factory=lambda: {
            "channel_tag": "渠道打标",
            "sku_tag": "商品打标",
        }
    )

    # ===== 原始字段 =====
    station_date_column: str = "日期"
    station_scene_column: str = "营销场景"
    station_sku_column: str = "跟单SKU ID"
    station_sku_name_column: str = "跟单SKU名称"
    station_cost_column: str = "花费"
    station_impression_column: str = "展现数"
    station_click_column: str = "点击数"
    station_order_row_column: str = "总订单行"
    station_gmv_column: str = "总订单金额"
    station_cart_column: str = "总加购数"
    station_new_customer_column: str = "下单新客数"

    cps_sku_column: str = "商品编号"
    cps_date_column: str = "下单日期"
    cps_gmv_column: str = "计佣金额"
    cps_cost_column: str = "总佣金"
    cps_order_row_column: str = "商品数量"

    brand_date_column: str = "转化日期"
    brand_cost_column: str = "花费"
    brand_impression_column: str = "展现数"
    brand_click_column: str = "点击数"
    brand_order_row_column: str = "总订单行（成交口径）"
    brand_gmv_column: str = "总订单金额（成交口径）"
    brand_cart_column: str = "总加购数"

    sitewide_date_column: str = "日期"
    sitewide_cost_column: str = "花费"
    sitewide_gmv_column: str = "全站交易额"
    sitewide_order_row_column: str = "全站订单行"
    sitewide_impression_column: str = "核心位置展现量"
    sitewide_click_column: str = "核心位置点击量"
    sitewide_new_customer_column: str = "180天未购新客数"

    channel_scene_column: str = "营销场景"
    plan_aggregate_column: str = "计划聚合"
    new_channel_column: str = "新产品渠道"
    channel_type_column: str = "渠道类型"

    sku_id_column: str = "京东skuID"
    sku_product_name_column: str = "商品名称"
    sku_category_column: str = "新分类"
    brand_column: str = "品牌"

    # ===== 归一化字段 =====
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
    period_label_column: str = "周期"

    ad_cost_column: str = "广告费用"
    ad_impression_column: str = "广告展现"
    ad_click_column: str = "广告点击"
    ad_order_row_column: str = "广告订单行"
    ad_gmv_column: str = "广告GMV"
    ad_new_customer_column: str = "广告新客"
    ad_cart_column: str = "广告加购数"

    synthetic_cps_scene: str = "京挑客"
    synthetic_brand_scene: str = "搜索品专"
    synthetic_sitewide_scene: str = "全站营销"
    unknown_text: str = "未知"

    summary_columns: list[str] = field(
        default_factory=lambda: [
            "广告费用",
            "花费占比%",
            "广告订单行",
            "广告GMV",
            "广告GMV占比",
            "广告ROI",
            "ROI月环比",
            "广告CPC",
            "广告CVR",
            "广告CTR",
            "广告新客",
            "广告新客成本",
        ]
    )

    time_columns: list[str] = field(
        default_factory=lambda: [
            "月",
            "日",
            "新产品渠道",
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
            "广告新客浓度",
            "广告总加购成本",
            "花费占比%",
            "广告GMV占比",
        ]
    )

    @property
    def source_usecols(self) -> dict[str, list[str]]:
        """返回业务数据源的最小读取列。"""
        return {
            "station": [
                self.station_date_column,
                self.station_scene_column,
                self.station_sku_column,
                self.station_sku_name_column,
                self.station_cost_column,
                self.station_impression_column,
                self.station_click_column,
                self.station_order_row_column,
                self.station_gmv_column,
                self.station_cart_column,
                self.station_new_customer_column,
            ],
            "cps": [
                self.cps_sku_column,
                self.cps_date_column,
                self.cps_gmv_column,
                self.cps_cost_column,
                self.cps_order_row_column,
            ],
            "brand": [
                self.brand_date_column,
                self.brand_cost_column,
                self.brand_impression_column,
                self.brand_click_column,
                self.brand_order_row_column,
                self.brand_gmv_column,
                self.brand_cart_column,
            ],
            "sitewide": [
                self.sitewide_date_column,
                self.sitewide_cost_column,
                self.sitewide_gmv_column,
                self.sitewide_order_row_column,
                self.sitewide_impression_column,
                self.sitewide_click_column,
                self.sitewide_new_customer_column,
            ],
        }

    @property
    def tag_usecols(self) -> dict[str, list[str]]:
        """返回打标文件的最小读取列。"""
        return {
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
