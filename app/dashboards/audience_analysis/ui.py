"""人群分析页面 AgGrid 渲染函数。"""

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, DataReturnMode, GridUpdateMode, JsCode


PERCENT_COLUMNS = {"花费占比%", "CTR-kw", "广告CTR", "广告CVR", "广告加购率", "广告GMV占比"}
INTEGER_COLUMNS = {"点击数", "广告展现", "广告点击", "广告订单行", "广告新客", "广告加购数"}
ROI_COLUMNS = {"ROI-kw", "广告ROI"}
COST_COLUMNS = {"广告费用", "CPC-kw", "广告CPC", "广告CPA", "广告新客成本", "广告总加购成本"}
GMV_COLUMNS = {"总订单金额", "广告GMV", "广告商品单价"}
DIMENSION_COLUMNS = {"人群分类", "人群名称", "月", "周", "日"}

THOUSAND_FORMATTER = JsCode(
    """
    function(params) {
        const value = Number(params.value || 0);
        return value.toLocaleString(undefined, {maximumFractionDigits: 2});
    }
    """
)

PERCENT_FORMATTER = JsCode(
    """
    function(params) {
        const value = Number(params.value || 0) * 100;
        const absValue = Math.abs(value);
        if (value !== 0 && absValue < 0.01) {
            return value.toLocaleString(undefined, {minimumFractionDigits: 6, maximumFractionDigits: 6}) + '%';
        }
        if (value !== 0 && absValue < 1) {
            return value.toLocaleString(undefined, {minimumFractionDigits: 4, maximumFractionDigits: 4}) + '%';
        }
        return value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) + '%';
    }
    """
)

INTEGER_FORMATTER = JsCode(
    """
    function(params) {
        const value = Number(params.value || 0);
        return Math.round(value).toLocaleString();
    }
    """
)

NUMBER_TOOLTIP = JsCode(
    """
    function(params) {
        if (params.value === null || params.value === undefined || params.value === '') {
            return '';
        }
        const value = Number(params.value);
        if (!Number.isFinite(value)) {
            return String(params.value);
        }
        return value.toLocaleString(undefined, {maximumFractionDigits: 8});
    }
    """
)

PERCENT_TOOLTIP = JsCode(
    """
    function(params) {
        if (params.value === null || params.value === undefined || params.value === '') {
            return '';
        }
        const value = Number(params.value) * 100;
        if (!Number.isFinite(value)) {
            return String(params.value);
        }
        return value.toLocaleString(undefined, {minimumFractionDigits: 6, maximumFractionDigits: 6}) + '%';
    }
    """
)


def render_classification_table(title: str, df: pd.DataFrame, key: str) -> None:
    """渲染人群分类树形表。

    Args:
        title: 表格标题。
        df: 带 path 列的人群分类汇总表。
        key: Streamlit 组件 key。

    Returns:
        None。
    """

    st.markdown(f"### {title}")
    if df.empty:
        render_empty_state("当前筛选条件下没有可展示的人群分类数据。")
        return
    _render_aggrid(
        df,
        _build_tree_grid_options(
            df,
            hidden_columns={"path", "人群分类", "人群名称", "月"},
            group_header="人群分类 > 人群名称 > 月",
        ),
        key,
    )


def render_time_table(title: str, df: pd.DataFrame, key: str) -> None:
    """渲染时间渠道树形表。

    Args:
        title: 表格标题。
        df: 带 path 列的时间渠道表。
        key: Streamlit 组件 key。

    Returns:
        None。
    """

    st.markdown(f"### {title}")
    if df.empty:
        render_empty_state("当前筛选条件下没有可展示的时间渠道数据。")
        return
    _render_aggrid(
        df,
        _build_tree_grid_options(
            df,
            hidden_columns={"path", "人群分类", "人群名称", "周", "日"},
            group_header="人群分类 > 人群名称 > 周 > 日",
        ),
        key,
    )


def render_total_table(df: pd.DataFrame) -> None:
    """渲染当前筛选范围总计行。

    Args:
        df: 总计表。

    Returns:
        None。
    """

    st.markdown("### 总计")
    if df.empty:
        render_empty_state("当前筛选条件下没有可展示的总计数据。")
        return
    _render_aggrid(df, _build_plain_grid_options(df), "audience_analysis_total_grid", height=110)


def render_empty_state(message: str = "当前数据为空，无法展示人群分析表。") -> None:
    """渲染空结果提示。

    Args:
        message: 展示给用户的提示文案。

    Returns:
        None。
    """

    st.warning(message)


def _build_plain_grid_options(df: pd.DataFrame) -> dict:
    """构造普通 AgGrid 表格配置。

    Args:
        df: 当前展示表。

    Returns:
        AgGrid gridOptions 字典。
    """

    return {
        "animateRows": False,
        "suppressAggFuncInHeader": True,
        "defaultColDef": {"sortable": True, "resizable": True, "filter": False},
        "columnDefs": [_build_column_def(column) for column in df.columns],
    }


def _build_tree_grid_options(df: pd.DataFrame, hidden_columns: set[str], group_header: str) -> dict:
    """构造树形 AgGrid 表格配置。

    Args:
        df: 带 path 列的展示表。
        hidden_columns: 需要隐藏的维度列。
        group_header: 树列标题。

    Returns:
        支持 treeData 的 AgGrid gridOptions 字典。
    """

    return {
        "treeData": True,
        "animateRows": False,
        "groupDefaultExpanded": 0,
        "getDataPath": JsCode("function(data) { return String(data.path || '').split('||'); }"),
        "suppressAggFuncInHeader": True,
        "autoGroupColumnDef": {
            "headerName": group_header,
            "minWidth": 320,
            "cellRendererParams": {"suppressCount": True},
        },
        "defaultColDef": {"sortable": True, "resizable": True, "filter": False},
        "columnDefs": [_build_column_def(column, hide=column in hidden_columns) for column in df.columns],
    }


def _build_column_def(column: str, hide: bool = False) -> dict:
    """按字段名构造 AgGrid 列定义。

    Args:
        column: DataFrame 列名。
        hide: 是否隐藏该列。

    Returns:
        单列 columnDef 配置。
    """

    column_def: dict = {"field": column, "headerName": column, "hide": hide, "minWidth": 120}
    if column == "path":
        column_def["hide"] = True
        return column_def
    if column in PERCENT_COLUMNS:
        # 百分比主显示保持紧凑；当数值过小时自动增加小数位，悬停 tooltip 展示完整百分比。
        column_def.update(
            {
                "type": "numericColumn",
                "width": 130,
                "valueFormatter": PERCENT_FORMATTER,
                "tooltipValueGetter": PERCENT_TOOLTIP,
            }
        )
    elif column in INTEGER_COLUMNS:
        column_def.update(
            {"type": "numericColumn", "width": 120, "valueFormatter": INTEGER_FORMATTER, "tooltipValueGetter": NUMBER_TOOLTIP}
        )
    elif column in ROI_COLUMNS:
        column_def.update(
            {"type": "numericColumn", "width": 130, "valueFormatter": THOUSAND_FORMATTER, "tooltipValueGetter": NUMBER_TOOLTIP}
        )
    elif column in COST_COLUMNS:
        column_def.update(
            {"type": "numericColumn", "width": 130, "valueFormatter": THOUSAND_FORMATTER, "tooltipValueGetter": NUMBER_TOOLTIP}
        )
    elif column in GMV_COLUMNS:
        column_def.update(
            {"type": "numericColumn", "width": 140, "valueFormatter": THOUSAND_FORMATTER, "tooltipValueGetter": NUMBER_TOOLTIP}
        )
    if column in DIMENSION_COLUMNS and column in {"人群分类", "人群名称"}:
        column_def["pinned"] = "left"
    return column_def


def _render_aggrid(df: pd.DataFrame, grid_options: dict, key: str, height: int | None = None) -> None:
    """按统一参数渲染 AgGrid。

    Args:
        df: 展示 DataFrame。
        grid_options: AgGrid gridOptions 配置。
        key: Streamlit 组件 key。
        height: 可选表格高度。

    Returns:
        None。
    """

    AgGrid(
        df,
        gridOptions=grid_options,
        height=height or _get_height(df),
        update_mode=GridUpdateMode.NO_UPDATE,
        data_return_mode=DataReturnMode.AS_INPUT,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True,
        fit_columns_on_grid_load=True,
        theme="streamlit",
        key=key,
    )


def _get_height(df: pd.DataFrame) -> int:
    """根据行数计算表格高度。

    Args:
        df: 展示 DataFrame。

    Returns:
        AgGrid 高度像素值。
    """

    return max(220, min(760, 72 + len(df) * 34))
