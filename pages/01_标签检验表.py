"""
标签检验表看板 — 关键词 / 人群 / SKU 标签分类 + 费用统计。

包含三个标签页：
  标签 1「关键词标签检验」：
    - 数据源：关键词匹配表 + 数据中心-关键词数据
    - 树形结构：词性分类 → 关键词，按费用降序
  标签 2「人群标签检验」：
    - 数据源：人群匹配表 + 数据中心-店铺人群数据
    - 树形结构：人群分类 → 人群名称，按费用降序
  标签 3「SKU标签检验」：
    - 数据源：商品匹配表 + 数据中心-产品数据
    - 树形结构：分类 → 投放产品SKU，按费用降序

三个标签共享同一个 Excel 工作簿（load_shared_workbook 只执行一次），
但各自独立加工数据、构建树形结构、渲染 AgGrid 表格。
"""
import streamlit as st

from app.core.loader import load_shared_workbook, select_required_sheets
from app.core.shared_source import (
    get_shared_source_bytes,
    get_shared_source_name,
    get_shared_source_token,
    has_shared_source,
)
from app.dashboards.tag_validation.config import AppConfig
from app.dashboards.tag_validation.processor import (
    build_audience_dataset,
    build_keyword_dataset,
    build_sku_dataset,
)
from app.dashboards.tag_validation.tree_builder import (
    build_audience_tree_payload,
    build_keyword_tree_payload,
    build_sku_tree_payload,
)
from app.dashboards.tag_validation.ui import (
    render_audience_summary,
    render_audience_table,
    render_empty_state,
    render_keyword_table,
    render_sku_summary,
    render_sku_table,
    render_summary,
)


def main() -> None:
    # ========== 1. 初始化配置 ==========
    cfg = AppConfig()

    # ========== 2. 页面基本设置 ==========
    st.set_page_config(page_title="标签检验表", page_icon="🏷️", layout="wide")
    st.title("标签检验表")
    st.caption("关键词 + 人群 + SKU 标签检验，数据来自首页上传的共享 Excel。")

    # ========== 3. 检查共享数据源 ==========
    if not has_shared_source():
        st.warning("请先在首页上传共享数据源，然后再进入当前看板。")
        st.stop()

    source_name = get_shared_source_name()
    st.caption(f"当前共享数据源：`{source_name}`")

    # ========== 4. 加载工作簿（一次性加载全部 6 张工作表） ==========
    workbook = load_shared_workbook(
        get_shared_source_bytes(), source_name, get_shared_source_token()
    )
    tables = select_required_sheets(workbook, cfg.required_sheets)

    # ========== 5. 标签页切换 ==========
    tab_keyword, tab_audience, tab_sku = st.tabs(
        ["关键词标签检验", "人群标签检验", "SKU标签检验"]
    )

    # ---------- 标签 1: 关键词标签检验 ----------
    with tab_keyword:
        keyword_df = build_keyword_dataset(tables, cfg)

        if keyword_df.empty:
            render_empty_state("当前关键词数据为空，无法展示关键词标签检验表。")
        else:
            keyword_tree = build_keyword_tree_payload(keyword_df, [], cfg) # 构造两级关键词树形表数据(词性分类关键词)
            render_summary(None)  # 渲染标签检验表标题
            render_keyword_table(keyword_tree)   # 渲染关键词标签检验表

    # ---------- 标签 2: 人群标签检验 ----------
    with tab_audience:
        audience_df = build_audience_dataset(tables, cfg)

        if audience_df.empty:
            render_empty_state("当前人群数据为空，无法展示人群标签检验表。")
        else:
            audience_tree = build_audience_tree_payload(audience_df, [], cfg)
            render_audience_summary() # 渲染人群标签检验表标题
            render_audience_table(audience_tree) # 渲染人群标签检验表

    # ---------- 标签 3: SKU 标签检验 ----------
    with tab_sku:
        sku_df = build_sku_dataset(tables, cfg)

        if sku_df.empty:
            render_empty_state("当前SKU数据为空，无法展示SKU标签检验表。")
        else:
            sku_tree = build_sku_tree_payload(sku_df, [], cfg)
            render_sku_summary() # 渲染SKU标签检验表标题
            render_sku_table(sku_tree) # 渲染SKU标签检验表


if __name__ == "__main__":
    main()
