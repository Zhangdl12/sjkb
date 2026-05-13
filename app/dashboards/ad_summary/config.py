from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppConfig:
    # ===== 工作表 =====
    ad_sheet: str = "数据中心-产品数据"
    shop_sheet: str = "品牌商智-商品数据"
    sku_sheet: str = "商品匹配表"
    plan_sheet: str = "计划类型匹配表"
    target_sheet: str = "店铺规划表"

    required_sheets: dict[str, str] = field(
        default_factory=lambda: {
            "ad": "数据中心-产品数据",
            "shop": "品牌商智-商品数据",
            "sku": "商品匹配表",
            "plan": "计划类型匹配表",
            "target": "店铺规划表",
        }
    )

    # ===== 原始字段 =====
    ad_date_column: str = "日期"
    ad_plan_type_column: str = "计划类型"
    ad_sku_id_column: str = "跟单SKU ID"
    ad_product_name_column: str = "跟单SKU名称"
    ad_cost_column: str = "总费用"
    ad_gmv_column: str = "总订单金额"
    ad_click_column: str = "点击数"

    shop_date_column: str = "时间"
    shop_sku_id_column: str = "SKU"
    shop_pv_column: str = "浏览量"
    shop_visitor_column: str = "访客数"
    shop_buyer_column: str = "成交人数"
    shop_order_count_column: str = "成交单量"
    shop_item_count_column: str = "成交商品件数"
    shop_gmv_column: str = "成交金额"
    shop_brand_column: str = "品牌"

    sku_id_column: str = "京东skuID"
    sku_product_name_column: str = "商品名称"
    category_column: str = "分类"
    brand_column: str = "品牌"

    plan_type_column: str = "计划类型"
    plan_aggregate_column: str = "计划聚合"
    new_channel_column: str = "新产品渠道"
    channel_type_column: str = "渠道类型"

    target_date_column: str = "日期"
    target_gmv_column: str = "GMV目标"
    target_sku_id_column: str = "sku"

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
    product_name_column: str = "商品名称"
    shop_target_column: str = "店铺GMV目标"
    period_label_column: str = "周期"
    period_sort_column: str = "周期排序"

    # ===== 尾部重复展示列，内部唯一命名 =====
    shop_gmv_tail_column: str = "店铺GMV_尾部"
    shop_gmv_ratio_tail_column: str = "店铺GMV环比_尾部"

    unknown_text: str = "未知"

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
            "人均访问数",
            "转化率",
            "人均子订单量",
            "均单商品数",
            "商品单价",
            "店铺GMV_尾部",
            "店铺GMV环比_尾部",
        ]
    )


DEFAULT_CONFIG = AppConfig()
