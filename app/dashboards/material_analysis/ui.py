"""
素材分析看板的页面渲染函数。

四个渲染函数对应页面的四个区域：
  1. render_summary()       → 顶部 6 列指标卡（展现/点击/花费/CTR/CVR/ROI）
  2. render_pivot_table()   → 中部透视分析表（带数字格式化）
  3. render_detail_section() → 底部可展开区域（前 100 行预览 + CSV 导出按钮）
  4. render_empty_state()   → 空筛选结果时的占位提示
"""
import pandas as pd
import streamlit as st

from app.dashboards.material_analysis.metrics import SummaryMetrics


def render_summary(metrics: SummaryMetrics) -> None:
    """渲染顶部 6 列汇总指标卡。

    指标卡是 Streamlit 的 st.metric，会自动显示增量的 delta 箭头
    （这里只展示绝对值，delta 留空）。
    """
    st.markdown("### 核心指标表现（当前筛选范围）")

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("展现数", f"{metrics.impressions:,.0f}")
    col2.metric("点击数", f"{metrics.clicks:,.0f}")
    col3.metric("花费", f"¥ {metrics.cost:,.2f}")
    col4.metric("CTR", f"{metrics.ctr * 100:.2f}%")   # CTR 是小数，*100 显示百分比
    col5.metric("CVR", f"{metrics.cvr * 100:.2f}%")
    col6.metric("ROI", f"{metrics.roi:.2f}")


def render_pivot_table(pivot_df: pd.DataFrame) -> None:
    """渲染透视分析表。

    使用 st.dataframe 展示，通过 style.format 为不同列设置数字格式：
      - 展现数/点击数/订单行 → 整数千分位
      - 花费/订单金额 → 人民币千分位
      - CTR/CVR/ROI → 百分比/小数
    """
    st.markdown("---")
    st.markdown("### 分维度透视分析")

    display_df = pivot_df.style.format(
        {
            "展现数": "{:,.0f}",
            "点击数": "{:,.0f}",
            "花费": "¥ {:,.2f}",
            "总订单金额": "¥ {:,.2f}",
            "总订单行": "{:,.0f}",
            "CTR": "{:.2%}",
            "CVR": "{:.2%}",
            "ROI": "{:.2f}",
        }
    )
    st.dataframe(display_df, width="stretch")


def render_detail_section(filtered_df: pd.DataFrame) -> None:
    """渲染可展开的明细预览和 CSV 导出区域。

    - 默认折叠（with st.expander），避免占用太多页面空间
    - 只展示前 100 行（避免大数据量导致页面卡顿）
    - CSV 使用 utf-8-sig 编码（BOM 头），确保在 Excel 中正确显示中文
    """
    with st.expander("点击查看并下载筛选后的数据明细"):
        st.dataframe(filtered_df.head(100).astype(str), width="stretch")
        csv_data = filtered_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="导出当前数据明细（CSV）",
            data=csv_data,
            file_name="素材分析_过滤后明细.csv",
            mime="text/csv",
        )


def render_empty_state() -> None:
    """渲染当前筛选条件下无数据时的空结果提示。"""
    st.warning("当前筛选条件下无数据，请放宽筛选条件。")
