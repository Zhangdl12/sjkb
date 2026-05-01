"""Streamlit 展示模块。

这个模块只负责“怎么展示”，不负责“数据怎么来”或“指标怎么算”。
这样页面样式调整时，不会误伤业务逻辑。
"""

import pandas as pd
import streamlit as st

from app.config import AppConfig
from app.metrics import SummaryMetrics


def render_sidebar_filters(
    filter_options: dict[str, list], config: AppConfig
) -> dict[str, list]:
    """渲染左侧筛选器，并返回用户当前选择。"""

    st.sidebar.header("🎛️ 维度筛选器")

    selections: dict[str, list] = {}

    st.sidebar.subheader("📅 时间维度")
    for column in config.time_filter_columns:
        options = filter_options.get(column, [])
        # 默认全选，保持与原单文件版本一致：用户进入页面即可看到全量数据。
        selections[column] = st.sidebar.multiselect(
            column,
            options=options,
            default=options,
        )

    st.sidebar.subheader("🏢 业务维度")
    for column in config.business_filter_columns:
        options = filter_options.get(column, [])
        if not options:
            # 如果该维度没有数据，直接跳过，不渲染空控件。
            continue

        # “分类”在页面上显示为“商品分类”，比原始字段名更易理解。
        label = "商品分类" if column == config.category_column else column
        selections[column] = st.sidebar.multiselect(
            label,
            options=options,
            default=options,
        )

    return selections


def render_summary(metrics: SummaryMetrics) -> None:
    """渲染页面顶部 6 个核心指标卡。"""

    st.markdown("### 📈 核心指标表现 (当前筛选范围)")

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("曝光数", f"{metrics.impressions:,.0f}")
    col2.metric("点击数", f"{metrics.clicks:,.0f}")
    col3.metric("消耗", f"¥ {metrics.cost:,.2f}")
    col4.metric("CTR (点击率)", f"{metrics.ctr * 100:.2f}%")
    col5.metric("CVR (转化率)", f"{metrics.cvr * 100:.2f}%")
    col6.metric("ROI (投资回报)", f"{metrics.roi:.2f}")


def render_pivot_table(pivot_df: pd.DataFrame) -> None:
    """渲染透视分析表，并在 UI 层负责数值格式化。"""

    st.markdown("---")
    st.markdown("### 📊 分维度透视分析")

    # 这里仅做显示格式处理，不改变原始 DataFrame 数值，方便后续复用。
    display_df = pivot_df.style.format(
        {
            "曝光数": "{:,.0f}",
            "点击数": "{:,.0f}",
            "消耗": "¥ {:,.2f}",
            "总订单金额": "¥ {:,.2f}",
            "总订单行": "{:,.0f}",
            "CTR": "{:.2%}",
            "CVR": "{:.2%}",
            "ROI": "{:.2f}",
        }
    )

    st.dataframe(display_df, width="stretch")


def render_detail_section(filtered_df: pd.DataFrame) -> None:
    """渲染明细查看与 CSV 导出区域。"""

    with st.expander("点击查看并下载筛选后的数据明细"):
        # 页面中只预览前 100 行，避免一次性渲染过多数据拖慢前端。
        st.dataframe(filtered_df.head(100).astype(str), width="stretch")
        # 使用 utf-8-sig，兼容 Excel 直接打开中文 CSV 的常见场景。
        csv_data = filtered_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 导出当前数据源明细 (CSV)",
            data=csv_data,
            file_name="素材分析_过滤后明细.csv",
            mime="text/csv",
        )


def render_empty_state() -> None:
    """渲染空结果提示。"""

    st.warning("⚠️ 当前筛选条件下无数据，请放宽筛选条件。")
