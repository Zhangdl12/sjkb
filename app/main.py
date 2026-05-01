"""应用主入口模块。

主流程只负责“组装”：
1. 初始化 Streamlit 页面；
2. 读取并缓存分析宽表；
3. 让 UI 收集筛选条件；
4. 调用 processor 和 metrics 完成过滤与计算；
5. 交给 UI 渲染结果。
"""

import pandas as pd
import streamlit as st

from app.config import DEFAULT_CONFIG
from app.data_loader import DataLoadError, load_source_tables
from app.metrics import build_pivot_table, calculate_summary_metrics
from app.processor import (
    DataProcessingError,
    apply_filters,
    build_analysis_dataset,
    build_filter_options,
)
from app.ui import (
    render_detail_section,
    render_empty_state,
    render_pivot_table,
    render_sidebar_filters,
    render_summary,
)


def main() -> None:
    """看板应用的主执行流程。"""

    st.set_page_config(page_title="素材分析数据看板", layout="wide")
    st.title("创意素材数据洞察看板")

    uploaded_file = st.file_uploader("上传 Excel 文件", type=["xlsx", "xls"])
    if uploaded_file is None:
        st.info("请先上传 Excel 文件，再开始查看分析结果。")
        st.stop()

    st.caption(f"当前数据源：`{uploaded_file.name}`")

    try:
        df = load_analysis_dataset(uploaded_file.getvalue(), uploaded_file.name)
    except (DataLoadError, DataProcessingError) as exc:
        st.error(str(exc))
        st.stop()

    filter_options = build_filter_options(df, DEFAULT_CONFIG)
    selections = render_sidebar_filters(filter_options, DEFAULT_CONFIG)
    filtered_df = apply_filters(df, selections, DEFAULT_CONFIG)

    if filtered_df.empty:
        render_empty_state()
        return

    summary_metrics = calculate_summary_metrics(filtered_df, DEFAULT_CONFIG)
    pivot_df = build_pivot_table(
        filtered_df, DEFAULT_CONFIG.default_pivot_group_by, DEFAULT_CONFIG
    )

    render_summary(summary_metrics)
    render_pivot_table(pivot_df)
    render_detail_section(filtered_df)


@st.cache_data
def load_analysis_dataset(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    """加载并缓存全量分析宽表。"""

    # 文件名保留在缓存参数中，便于切换同内容不同文件名时也能正确区分。
    _ = file_name
    tables = load_source_tables(file_bytes, DEFAULT_CONFIG)
    return build_analysis_dataset(tables, DEFAULT_CONFIG)


if __name__ == "__main__":
    main()
