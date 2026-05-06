"""Rendering helpers for the material analysis dashboard."""

import pandas as pd
import streamlit as st

from app.dashboards.material_analysis.metrics import SummaryMetrics


def render_summary(metrics: SummaryMetrics) -> None:
    """Render the summary metric cards."""

    st.markdown("### 核心指标表现（当前筛选范围）")

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("展现数", f"{metrics.impressions:,.0f}")
    col2.metric("点击数", f"{metrics.clicks:,.0f}")
    col3.metric("花费", f"¥ {metrics.cost:,.2f}")
    col4.metric("CTR", f"{metrics.ctr * 100:.2f}%")
    col5.metric("CVR", f"{metrics.cvr * 100:.2f}%")
    col6.metric("ROI", f"{metrics.roi:.2f}")


def render_pivot_table(pivot_df: pd.DataFrame) -> None:
    """Render the pivot analysis table."""

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
    """Render the detail preview and CSV export section."""

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
    """Render the empty state for the current filter selection."""

    st.warning("当前筛选条件下无数据，请放宽筛选条件。")
