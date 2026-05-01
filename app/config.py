"""应用配置模块。

这个文件集中维护项目里的稳定约定：
1. Excel 中使用的工作表名；
2. 核心字段名；
3. 页面默认展示需要的筛选维度和透视维度；
4. 数据清洗时用于兜底的默认值。

这样做的好处是，后续如果 Excel 字段、sheet 名称或默认分组规则调整，
只需要优先看这里，而不必在业务代码里全局搜索硬编码字符串。
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppConfig:
    """描述整个看板应用的静态配置。"""

    # Excel 工作表名称。
    plan_sheet: str = "计划类型匹配表"
    creative_sheet: str = "数据中心-创意数据"
    sku_sheet: str = "商品匹配表"

    # 原始事实表和维度表中的关键字段名。
    plan_type_column: str = "计划类型"
    campaign_column: str = "推广计划"
    sku_id_column: str = "跟单SKU ID"
    jd_sku_id_column: str = "京东skuID"
    category_column: str = "分类"
    new_product_channel_column: str = "新产品渠道"
    channel_type_column: str = "渠道类型"
    aitamei_column: str = "爱他美判断"
    date_column: str = "日期"
    year_column: str = "年"
    month_column: str = "月"
    day_column: str = "日"

    impressions_column: str = "展现数"
    clicks_column: str = "点击数"
    cost_column: str = "花费"
    gmv_column: str = "总订单金额"
    orders_column: str = "总订单行"

    # 数据清洗失败或维度未匹配时的默认展示值。
    unknown_channel: str = "未知渠道"
    unknown_channel_type: str = "未知渠道类型"
    unknown_category: str = "未知分类"
    other_aitamei: str = "其他"
    aitamei_value: str = "爱他美抢量"
    aitamei_keyword: str = "爱他美"

    # 页面支持的全部筛选维度。
    filter_columns: list[str] = field(
        default_factory=lambda: [
            "年",
            "月",
            "日",
            "渠道类型",
            "新产品渠道",
            "分类",
            "爱他美判断",
        ]
    )
    time_filter_columns: list[str] = field(
        default_factory=lambda: ["年", "月", "日"]
    )
    business_filter_columns: list[str] = field(
        default_factory=lambda: ["渠道类型", "新产品渠道", "分类", "爱他美判断"]
    )
    default_pivot_group_by: list[str] = field(
        default_factory=lambda: ["新产品渠道"]
    )


DEFAULT_CONFIG = AppConfig()
