from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppConfig:
    """广告数据汇总的字段、工作表和展示配置。

    本配置只维护字段名，不写业务逻辑。业务数据源和打标文件拆开读取，
    是为了让页面能够分别缓存大数据源和小打标表。
    """

    # ===== 业务数据源工作表 =====
    station_sheet: str = "站内外数据源"
    brand_sheet: str = "品专数据源"
    cps_sheet: str = "CPS数据源"
    sitewide_sheet: str = "全站营销数据源"
    shop_sheet: str = "店铺商智销售"

    required_sheets: dict[str, str] = field(
        default_factory=lambda: {
            "station": "站内外数据源",
            "brand": "品专数据源",
            "cps": "CPS数据源",
            "sitewide": "全站营销数据源",
            "shop": "店铺商智销售",
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

    # ===== 站内外字段 =====
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

    # ===== 品专字段 =====
    brand_date_column: str = "转化日期"
    brand_cost_column: str = "花费"
    brand_impression_column: str = "展现数"
    brand_click_column: str = "点击数"
    brand_exposure_column: str = "曝光数"
    brand_exposure_click_column: str = "曝光点击数"
    brand_order_row_column: str = "总订单行（成交口径）"
    brand_gmv_column: str = "总订单金额（成交口径）"
    brand_cart_column: str = "总加购数"

    # ===== CPS 字段 =====
    cps_sku_column: str = "商品编号"
    cps_date_column: str = "下单日期"
    cps_gmv_column: str = "计佣金额"
    cps_cost_column: str = "总佣金"
    cps_order_row_column: str = "商品数量"

    # ===== 全站营销字段 =====
    sitewide_date_column: str = "日期"
    sitewide_cost_column: str = "花费"
    sitewide_gmv_column: str = "全站交易额"
    sitewide_order_row_column: str = "全站订单行"
    sitewide_impression_column: str = "核心位置展现量"
    sitewide_click_column: str = "核心位置点击量"
    sitewide_new_customer_column: str = "180天未购新客数"

    # ===== 店铺商智销售字段 =====
    shop_date_column: str = "时间"
    shop_sku_id_column: str = "SKU"
    shop_product_name_column: str = "商品名称"
    shop_brand_column: str = "品牌"
    shop_pv_source_column: str = "浏览量"
    shop_visitor_source_column: str = "访客数"
    shop_buyer_source_column: str = "成交人数"
    shop_item_count_source_column: str = "成交商品件数"
    shop_gmv_source_column: str = "成交金额"

    # ===== 打标字段 =====
    channel_scene_column: str = "营销场景"
    plan_aggregate_column: str = "计划聚合"
    new_channel_column: str = "新产品渠道"
    channel_type_column: str = "渠道类型"
    sku_tag_id_column: str = "京东skuID"
    sku_tag_name_column: str = "商品名称"
    sku_tag_brand_column: str = "品牌"
    sku_tag_category_column: str = "新分类"

    # ===== 归一化后的维度字段 =====
    source_type_column: str = "_source_type"
    ad_source_type: str = "ad"
    shop_source_type: str = "shop"
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
    ad_sku_id_column: str = "跟单SKU ID"
    product_name_column: str = "商品名称"
    category_column: str = "新分类"
    brand_column: str = "投放品牌"

    # ===== 归一化后的基础指标字段 =====
    ad_cost_column: str = "广告费用"
    ad_impression_column: str = "广告展现"
    ad_click_column: str = "广告点击"
    ad_order_row_column: str = "广告订单行"
    ad_gmv_column: str = "投放GMV"
    ad_cart_column: str = "广告加购数"
    ad_new_customer_column: str = "广告新客"
    shop_gmv_column: str = "店铺GMV"
    shop_target_column: str = "店铺GMV目标"
    shop_pv_column: str = "PV"
    shop_visitor_column: str = "访客数"
    shop_buyer_column: str = "成交人数"
    shop_item_count_column: str = "成交商品件数"

    # ===== 尾部重复展示列，内部唯一命名 =====
    shop_gmv_tail_column: str = "店铺GMV_尾部"
    shop_gmv_ratio_tail_column: str = "店铺GMV环比_尾部"

    blank_text: str = "(空白)"

    display_columns: list[str] = field(
        default_factory=lambda: [
            "周期",
            "广告费用",
            "投放GMV",
            "店铺GMV",
            "广告GMV贡献",
            "广告ROI",
            "费比",
            "消耗环比",
            "投放GMV环比",
            "店铺GMV环比",
            "ROI环比",
            "费比环比",
            "店铺GMV目标",
            "店铺完成进度",
            "广告点击",
            "广告点击季度同比",
            "PV贡献",
            "PV",
            "店铺转化率",
            "商品单价",
            "店铺GMV_尾部",
            "店铺GMV环比_尾部",
        ]
    )

    @property
    def source_usecols(self) -> dict[str, list[str]]:
        """返回广告汇总业务数据源需要读取的最小列集合。

        Returns:
            别名到列名列表的映射，传给 pandas.read_excel(usecols=...)。
        """
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
            "brand": [
                self.brand_date_column,
                self.brand_cost_column,
                self.brand_impression_column,
                self.brand_click_column,
                self.brand_exposure_column,
                self.brand_exposure_click_column,
                self.brand_order_row_column,
                self.brand_gmv_column,
                self.brand_cart_column,
            ],
            "cps": [
                self.cps_sku_column,
                self.cps_date_column,
                self.cps_gmv_column,
                self.cps_cost_column,
                self.cps_order_row_column,
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
            "shop": [
                self.shop_date_column,
                self.shop_sku_id_column,
                self.shop_product_name_column,
                self.shop_brand_column,
                self.shop_pv_source_column,
                self.shop_visitor_source_column,
                self.shop_buyer_source_column,
                self.shop_item_count_source_column,
                self.shop_gmv_source_column,
            ],
        }

    @property
    def tag_usecols(self) -> dict[str, list[str]]:
        """返回广告汇总打标文件需要读取的最小列集合。

        Returns:
            别名到列名列表的映射，传给 pandas.read_excel(usecols=...)。
        """
        return {
            "channel_tag": [
                self.channel_scene_column,
                self.plan_aggregate_column,
                self.new_channel_column,
                self.channel_type_column,
            ],
            "sku_tag": [
                self.sku_tag_id_column,
                self.sku_tag_name_column,
                self.sku_tag_brand_column,
                self.sku_tag_category_column,
            ],
        }


DEFAULT_CONFIG = AppConfig()
