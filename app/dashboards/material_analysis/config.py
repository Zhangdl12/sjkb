"""
素材分析看板的工作表和字段配置。

AppConfig 是冻结 dataclass（frozen=True），实例化后不可修改。
这样所有看板相关模块引用同一个配置对象，保证列名一致性。

数据表（3 张）：
  - plan_sheet / creative_sheet / sku_sheet —— Excel 中的工作表名

维度列（用于筛选和透视）：
  - 时间维度：年/月/日（从日期列派生）
  - 业务维度：渠道类型、新产品渠道、商品分类、爱他美判断

指标列（用于汇总计算）：
  - 展现数、点击数、花费、总订单金额、总订单行
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """素材分析看板使用的工作表和字段配置。"""

    # ===== Excel 工作表名 =====
    plan_sheet: str = "计划类型匹配表"
    creative_sheet: str = "数据中心-创意数据"
    sku_sheet: str = "商品匹配表"

    # ===== 源数据列名 =====
    plan_type_column: str = "计划类型"         # 用于关联计划 → 渠道
    campaign_column: str = "推广计划"          # 用于判断是否爱他美品牌
    sku_id_column: str = "跟单SKU ID"         # 用于关联商品分类
    jd_sku_id_column: str = "京东skuID"       # 商品匹配表中的 SKU ID
    date_column: str = "日期"                  # 原始日期（%Y%m%d 格式字符串）

    # ===== 派生维度列 =====
    category_column: str = "分类"              # 商品分类（来自商品匹配表）
    new_product_channel_column: str = "新产品渠道"  # 渠道名称（来自计划类型匹配表）
    channel_type_column: str = "渠道类型"       # 渠道类型（来自计划类型匹配表）
    aitamei_column: str = "爱他美判断"          # 是否爱他美品牌（派生标记列）
    year_column: str = "年"                    # 从日期列派生的年份
    month_column: str = "月"                   # 从日期列派生的月份
    day_column: str = "日"                     # 从日期列派生的格式化日期

    # ===== 指标列 =====
    impressions_column: str = "展现数"
    clicks_column: str = "点击数"
    cost_column: str = "花费"
    gmv_column: str = "总订单金额"
    orders_column: str = "总订单行"

    # ===== 分类标记常量 =====
    unknown_channel: str = "未知渠道"          # 计划类型匹配不到的渠道
    unknown_channel_type: str = "未知渠道类型"  # 匹配不到的渠道类型
    unknown_category: str = "未知分类"          # 商品匹配不到的分类
    other_aitamei: str = "其他"                # 非爱他美品牌的标记值
    aitamei_value: str = "爱他美抢量"           # 爱他美品牌的标记值
    aitamei_keyword: str = "爱他美"             # 用于判断品牌的关键词


DEFAULT_CONFIG = AppConfig()
