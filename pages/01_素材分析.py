"""
素材分析看板 — 创意素材数据洞察。

功能：
  对广告创意数据进行多维度分析，包含：
  - 7 个筛选器（年/月/日 时间维度 + 渠道/分类/爱他美 业务维度）
  - 6 项核心指标卡（展现数、点击数、花费、CTR、CVR、ROI）
  - 按维度分组的透视表（默认按"新产品渠道"分组）
  - 筛选后明细数据预览和 CSV 导出

数据加工流程（在 build_analysis_dataset 中）：
  1. 根据"推广计划"列判断是否为爱他美品牌
  2. 用"计划类型匹配表"补充渠道分类信息
  3. 用"商品匹配表"补充商品分类信息
  4. 解析日期列（%Y%m%d 格式），生成年/月/日三个派生列

依赖的 Excel 工作表：
  - 计划类型匹配表 → 别名 plan
  - 数据中心-创意数据 → 别名 creative
  - 商品匹配表 → 别名 sku
"""
import streamlit as st

from app.core.filters import FilterField, apply_filters, render_sidebar_filters
from app.core.loader import load_shared_workbook, select_required_sheets
from app.core.shared_source import (
    get_shared_source_bytes,
    get_shared_source_name,
    get_shared_source_token,
    has_shared_source,
)
from app.dashboards.material_analysis.config import AppConfig
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


def main() -> None:
    # ========== 1. 初始化配置 ==========
    # AppConfig 是冻结 dataclass，包含所有工作表名和列名的映射常量
    cfg = AppConfig()

    # ========== 2. 页面基本设置 ==========
    st.set_page_config(page_title="素材分析", page_icon="📊", layout="wide")
    st.title("创意素材数据洞察看板")
    st.caption("复用首页上传的共享 Excel 数据源。")

    # ========== 3. 检查共享数据源 ==========
    # 用户必须先回到首页上传 Excel，否则后续步骤无法执行
    if not has_shared_source():
        st.warning("请先在首页上传共享数据源，然后再进入当前看板。")
        st.stop()  # stop() 后，页面后续代码不会执行

    source_name = get_shared_source_name()
    st.caption(f"当前共享数据源：`{source_name}`")

    # ========== 4. 加载工作簿 → 提取工作表 → 加工数据 ==========
    # Step 4a: 从 session_state 获取字节数据并缓存解析整个 Excel
    workbook = load_shared_workbook(
        get_shared_source_bytes(), source_name, get_shared_source_token()
    )
    # Step 4b: 从工作簿中提取本看板需要的 3 张工作表（按别名访问）
    tables = select_required_sheets(workbook, {
        "plan": cfg.plan_sheet,         # 计划类型匹配表
        "creative": cfg.creative_sheet,  # 数据中心-创意数据
        "sku": cfg.sku_sheet,           # 商品匹配表
    })
    # Step 4c: 合并 + 派生列 + 分类标记 → 分析宽表
    df = build_analysis_dataset(tables, cfg)

    # ========== 5. 侧边栏筛选器 ==========
    # filter_fields 定义筛选器的显示顺序和分组
    # 时间维度（年→月→日，选项排序）+ 业务维度（渠道→新产品渠道→商品分类→爱他美判断）
    filter_fields = (
        FilterField(cfg.year_column, group="时间维度", sort_values=True),
        FilterField(cfg.month_column, group="时间维度", sort_values=True),
        FilterField(cfg.day_column, group="时间维度", sort_values=True),
        FilterField(cfg.channel_type_column, group="业务维度"),
        FilterField(cfg.new_product_channel_column, group="业务维度"),
        FilterField(cfg.category_column, label="商品分类", group="业务维度"),
        FilterField(cfg.aitamei_column, group="业务维度"),
    )
    # render_sidebar_filters 渲染侧边栏 → 返回用户选择
    # apply_filters 应用选择 → 返回筛选后的 DataFrame
    selections = render_sidebar_filters(df, filter_fields, key_prefix="素材分析")
    filtered_df = apply_filters(df, selections, filter_fields)

    # ========== 6. 空数据检查 ==========
    if filtered_df.empty:
        render_empty_state()
        return  # 不执行后续渲染

    # ========== 7. 指标计算与透视表构建 ==========
    # 顶部汇总指标（展现/点击/花费/CTR/CVR/ROI）
    metrics = calculate_summary_metrics(filtered_df, cfg)
    # 分组透视表（默认按"新产品渠道"分组，汇总各项指标）
    pivot = build_pivot_table(filtered_df, [cfg.new_product_channel_column], cfg)

    # ========== 8. 渲染 UI ==========
    render_summary(metrics)        # 6 列指标卡
    render_pivot_table(pivot)       # 分组透视表
    render_detail_section(filtered_df)  # 可展开的明细预览 + CSV 导出


if __name__ == "__main__":
    main()
