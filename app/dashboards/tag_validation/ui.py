"""
标签检验表看板的页面渲染函数。

渲染方式：使用 st_aggrid 渲染 AgGrid 两级树状表格。

三个标签页各有一组渲染函数，共用底层的 _build_tree_grid_options 和 _render_aggrid_tree。
"""
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, DataReturnMode, GridUpdateMode, JsCode

from app.dashboards.tag_validation.config import DEFAULT_CONFIG
from app.dashboards.tag_validation.tree_builder import (
    AudienceTreePayload,
    KeywordTreePayload,
    SkuTreePayload,
)


CHILD_TEXT_HIDDEN_RENDERER = JsCode(
    """
    function(params) {
        if (params.node && params.node.level > 0) {
            return "";
        }
        return params.value || "";
    }
    """
)

# ======================================================================
#  AgGrid 通用配置工厂
# ======================================================================

def _build_tree_grid_options(
    category_column_name: str,
    cost_column_name: str,
    extra_columns: list[dict] | None = None,
    auto_group_inner_renderer: JsCode | None = None,
) -> dict:
    """构建 AgGrid 树形表格的 gridOptions 配置。

    Args:
        category_column_name: 第一列（分组列）的表头名称
        cost_column_name: 第二列（费用列）的字段名
        extra_columns: 追加展示列配置
        auto_group_inner_renderer: 树列文本自定义渲染
    """
    extra_columns = extra_columns or []
    cell_renderer_params = {"suppressCount": True}
    if auto_group_inner_renderer is not None:
        cell_renderer_params["innerRenderer"] = auto_group_inner_renderer

    return {
        "treeData": True,
        "animateRows": False,
        "groupDefaultExpanded": 0,  # 0 = 全部折叠，-1 = 全部展开
        "getDataPath": JsCode(
            "function(data) { return String(data.path || '').split('||'); }"
        ),
        "suppressAggFuncInHeader": True,
        "autoGroupColumnDef": {
            "headerName": category_column_name,
            "minWidth": 260,
            "cellRendererParams": cell_renderer_params,
        },
        "defaultColDef": {
            "sortable": True,
            "resizable": True,
            "filter": False,
        },
        "columnDefs": [
            *extra_columns,
            {
                "field": cost_column_name,
                "headerName": cost_column_name,
                "type": "numericColumn",
                "sort": "desc",
                "width": 130,
                "valueFormatter": JsCode(
                    "function(params) { return Math.round(params.value || 0).toLocaleString(); }"
                ),
            },
            {"field": "path", "hide": True},
        ],
    }


def _render_aggrid_tree(display_df: pd.DataFrame, grid_options: dict, key: str) -> None:
    """通用的 AgGrid 树形表格渲染函数。"""
    AgGrid(
        display_df,
        gridOptions=grid_options,
        height=720,
        update_mode=GridUpdateMode.NO_UPDATE,
        data_return_mode=DataReturnMode.AS_INPUT,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True,
        fit_columns_on_grid_load=True,
        theme="streamlit",
        key=key,
    )


# ======================================================================
#  关键词标签检验 UI
# ======================================================================

def render_summary(metrics: None) -> None:
    """渲染关键词标签检验区域标题。"""
    _ = metrics
    st.markdown("### 关键词标签检验")


def render_keyword_table(payload: KeywordTreePayload) -> None:
    """渲染关键词费用树形表（词性分类 → 关键词）。"""
    config = DEFAULT_CONFIG
    if payload.tree_df.empty:
        render_empty_state("当前关键词数据为空，无法展示关键词标签检验表。")
        return

    display_df = payload.tree_df.copy()
    grid_options = _build_tree_grid_options(
        category_column_name=config.display_keyword_category_column,
        cost_column_name=config.display_keyword_cost_column,
        extra_columns=[
            {
                "field": config.keyword_column,
                "headerName": config.keyword_column,
                "minWidth": 220,
            }
        ],
        auto_group_inner_renderer=CHILD_TEXT_HIDDEN_RENDERER,
    )
    _render_aggrid_tree(display_df, grid_options, key="keyword_tag_validation_grid")


# ======================================================================
#  人群标签检验 UI
# ======================================================================

def render_audience_summary() -> None:
    """渲染人群标签检验区域标题。"""
    st.markdown("### 人群标签检验")


def render_audience_table(payload: AudienceTreePayload) -> None:
    """渲染人群费用树形表（人群分类 → 人群名称）。"""
    config = DEFAULT_CONFIG
    if payload.tree_df.empty:
        render_empty_state("当前人群数据为空，无法展示人群标签检验表。")
        return

    display_df = payload.tree_df.copy()
    grid_options = _build_tree_grid_options(
        category_column_name=config.display_audience_category_column,
        cost_column_name=config.display_audience_cost_column,
        extra_columns=[
            {
                "field": config.audience_name_column,
                "headerName": config.audience_name_column,
                "minWidth": 220,
            }
        ],
        auto_group_inner_renderer=CHILD_TEXT_HIDDEN_RENDERER,
    )
    _render_aggrid_tree(display_df, grid_options, key="audience_tag_validation_grid")


# ======================================================================
#  SKU 标签检验 UI
# ======================================================================

def render_sku_summary() -> None:
    """渲染 SKU 标签检验区域标题。"""
    st.markdown("### SKU标签检验")


def render_sku_table(payload: SkuTreePayload) -> None:
    """渲染 SKU 费用树形表（新分类 → 跟单SKU ID）。"""
    config = DEFAULT_CONFIG
    if payload.tree_df.empty:
        render_empty_state("当前SKU数据为空，无法展示SKU标签检验表。")
        return

    display_df = payload.tree_df.copy()
    grid_options = _build_tree_grid_options(
        category_column_name=config.display_sku_category_column,
        cost_column_name=config.display_sku_cost_column,
        extra_columns=[
            {
                "field": config.sku_fact_id_column,
                "headerName": config.sku_fact_id_column,
                "minWidth": 140,
            },
            {
                "field": config.sku_name_column,
                "headerName": config.display_sku_name_column,
                "minWidth": 220,
            }
        ],
        auto_group_inner_renderer=CHILD_TEXT_HIDDEN_RENDERER,
    )
    _render_aggrid_tree(display_df, grid_options, key="sku_tag_validation_grid")


# ======================================================================
#  通用 UI
# ======================================================================

def render_detail_section(filtered_df: pd.DataFrame) -> None:
    """当前阶段不渲染明细区（保留接口兼容）。"""
    _ = filtered_df


def render_empty_state(message: str = "当前数据为空，无法展示标签检验表。") -> None:
    """渲染空结果提示。"""
    st.warning(message)
