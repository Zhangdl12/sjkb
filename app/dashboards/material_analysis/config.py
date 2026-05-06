"""Configuration for the material analysis dashboard."""

from dataclasses import dataclass

from app.core.filters import FilterField
from app.core.page_runner import DashboardPageConfig


@dataclass(frozen=True)
class AppConfig:
    """Static workbook and field configuration for material analysis."""

    plan_sheet: str = "计划类型匹配表"
    creative_sheet: str = "数据中心-创意数据"
    sku_sheet: str = "商品匹配表"

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

    unknown_channel: str = "未知渠道"
    unknown_channel_type: str = "未知渠道类型"
    unknown_category: str = "未知分类"
    other_aitamei: str = "其他"
    aitamei_value: str = "爱他美抢量"
    aitamei_keyword: str = "爱他美"


DEFAULT_CONFIG = AppConfig()


def build_page_config() -> DashboardPageConfig:
    """Build the page runner config for this dashboard."""

    from app.dashboards.material_analysis.metrics import (
        build_pivot_table,
        calculate_summary_metrics,
    )
    from app.dashboards.material_analysis.processor import build_analysis_dataset
    from app.dashboards.material_analysis.ui import (
        render_detail_section,
        render_empty_state,
        render_pivot_table,
        render_summary,
    )

    return DashboardPageConfig(
        page_title="素材分析",
        page_icon="📊",
        page_header="创意素材数据洞察看板",
        page_description="当前页面会复用首页上传的共享 Excel 数据源。",
        required_sheets={
            "plan": DEFAULT_CONFIG.plan_sheet,
            "creative": DEFAULT_CONFIG.creative_sheet,
            "sku": DEFAULT_CONFIG.sku_sheet,
        },
        filter_fields=(
            FilterField(DEFAULT_CONFIG.year_column, group="时间维度", sort_values=True),
            FilterField(DEFAULT_CONFIG.month_column, group="时间维度", sort_values=True),
            FilterField(DEFAULT_CONFIG.day_column, group="时间维度", sort_values=True),
            FilterField(DEFAULT_CONFIG.channel_type_column, group="业务维度"),
            FilterField(DEFAULT_CONFIG.new_product_channel_column, group="业务维度"),
            FilterField(
                DEFAULT_CONFIG.category_column,
                label="商品分类",
                group="业务维度",
            ),
            FilterField(DEFAULT_CONFIG.aitamei_column, group="业务维度"),
        ),
        default_pivot_group_by=(DEFAULT_CONFIG.new_product_channel_column,),
        context=DEFAULT_CONFIG,
        build_dataset=build_analysis_dataset,
        build_metrics=calculate_summary_metrics,
        build_pivot_table=build_pivot_table,
        render_summary=render_summary,
        render_pivot_table=render_pivot_table,
        render_detail_section=render_detail_section,
        render_empty_state=render_empty_state,
    )


MATERIAL_ANALYSIS_CONFIG = build_page_config()
