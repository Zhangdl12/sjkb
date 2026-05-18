"""
标签检验表看板 — 关键词 / 人群 / SKU 标签分类 + 费用统计。

包含三个标签页：
  标签 1「关键词标签检验」：
    - 事实数据：业务数据源 workbook 的“关键词数据源”
    - 打标数据：打标 workbook 的“关键词打标”
    - 树形结构：词性分类 → 关键词，按广告费用降序
  标签 2「人群标签检验」：
    - 事实数据：业务数据源 workbook 的“人群数据源”
    - 打标数据：打标 workbook 的“人群打标”
    - 树形结构：人群分类 → 人群名称，按广告费用降序
  标签 3「SKU标签检验」：
    - 事实数据：业务数据源 workbook 的“站内外数据源”
    - 打标数据：打标 workbook 的“商品打标”
    - 树形结构：新分类 → 跟单SKU ID，按广告费用降序

页面会分别加载业务数据源和打标文件两个 Excel。这样可以保持业务数据源为最新导出，
同时让打标文件独立维护、独立替换。
"""
import streamlit as st

from app.core.shared_source import (
    get_shared_source_bytes,
    get_shared_source_name,
    get_shared_source_token,
    get_tag_source_bytes,
    get_tag_source_name,
    get_tag_source_token,
    has_shared_source,
    has_tag_source,
)
from app.dashboards.tag_validation.service import load_tag_validation_payloads
from app.dashboards.tag_validation.ui import (
    render_audience_summary,
    render_audience_table,
    render_keyword_table,
    render_sku_summary,
    render_sku_table,
    render_summary,
)


def main() -> None:
    # ========== 1. 页面基本设置 ==========
    st.set_page_config(page_title="标签检验表", page_icon="🏷️", layout="wide")
    st.title("标签检验表")
    st.caption("关键词 + 人群 + SKU 标签检验，数据来自业务数据源和独立打标文件。")

    # ========== 2. 检查业务数据源和打标文件 ==========
    # 标签检验表需要两个 workbook：业务数据源提供事实数据，打标文件提供分类标签。
    if not has_shared_source():
        st.warning("请先在首页上传业务数据源，然后再进入当前看板。")
        st.stop()

    if not has_tag_source():
        st.warning("请先在首页上传打标文件，然后再进入当前看板。")
        st.stop()

    source_name = get_shared_source_name()
    tag_source_name = get_tag_source_name()
    st.caption(f"当前业务数据源：`{source_name}`")
    st.caption(f"当前打标文件：`{tag_source_name}`")

    # ========== 3. 一次性加载三类标签检验结果 ==========
    # 用户切换关键词/人群/SKU 时，Streamlit 会整页重跑。这里把耗时计算缓存到最终树表层，
    # 页面重跑只切换已经算好的小结果，不再按单选项重复解析 Excel。
    with st.spinner("正在一次性读取并计算关键词、人群、SKU 标签检验数据，请稍候..."):
        payloads = load_tag_validation_payloads(
            get_shared_source_bytes(),
            source_name or "",
            get_shared_source_token() or "",
            get_tag_source_bytes(),
            tag_source_name or "",
            get_tag_source_token() or "",
        )

    # ========== 4. 选择检验类型 ==========
    # 这里仍使用单选而不是 st.tabs，避免 Streamlit 同时渲染三个大型 AgGrid。
    validation_type = st.radio(
        "选择标签检验类型",
        ["关键词标签检验", "人群标签检验", "SKU标签检验"],
        horizontal=True,
        label_visibility="collapsed",
    )

    # ========== 5. 按当前类型渲染已缓存的树表 ==========
    if validation_type == "关键词标签检验":
        render_summary(None)
        render_keyword_table(payloads.keyword)

    elif validation_type == "人群标签检验":
        render_audience_summary()
        render_audience_table(payloads.audience)

    else:
        render_sku_summary()
        render_sku_table(payloads.sku)


if __name__ == "__main__":
    main()
