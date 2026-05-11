"""
看板开发示例 — 说明如何新增一个业务看板。

本页面是给开发者看的文档，不展示实际数据。
以代码示例 + 文字说明的形式展示新增看板的标准步骤。
"""
import streamlit as st

from app.core.shared_source import get_shared_source_name, has_shared_source


def main() -> None:
    st.set_page_config(page_title="看板开发示例", page_icon="🧩", layout="wide")
    st.title("看板开发示例")
    st.caption("这个页面用于说明如何新增一个业务看板入口，作为后续扩展时的参考。")

    # 展示当前数据源状态（让开发者了解共享机制）
    if has_shared_source():
        st.info(f"当前共享数据源：`{get_shared_source_name()}`")
    else:
        st.warning("当前还没有共享数据源。正式业务看板会要求先在首页上传 Excel 文件。")

    # ========== 新增看板步骤 ==========
    st.markdown("## 新增一个业务看板的步骤")
    st.markdown(
        "\n".join([
            "1. 在 `app/dashboards/<看板名称>/` 下创建目录，实现数据处理、指标计算和 UI 渲染逻辑。",
            "2. 在 `pages/` 下新增一个页面文件（如 `04_新看板.py`）。",
            "3. 页面文件中按以下步骤编写逻辑：",
        ])
    )

    # ========== 代码模板 ==========
    st.markdown(
        """```python
# 示例页面结构
import streamlit as st
from app.core.shared_source import has_shared_source, get_shared_source_bytes, ...
from app.core.loader import load_shared_workbook, select_required_sheets
from app.core.filters import FilterField, render_sidebar_filters, apply_filters

def main():
    # 1. 页面设置
    st.set_page_config(page_title="...", page_icon="...", layout="wide")
    st.title("...")

    # 2. 检查共享数据源
    if not has_shared_source():
        st.warning("请先在首页上传共享数据源。")
        st.stop()

    # 3. 加载工作簿 → 提取工作表 → 加工数据
    workbook = load_shared_workbook(...)
    tables = select_required_sheets(workbook, {"别名": "工作表名"})
    df = build_dataset(tables, config)

    # 4. 筛选器（如不需要可跳过）
    selections = render_sidebar_filters(df, filter_fields)
    filtered_df = apply_filters(df, selections, filter_fields)

    # 5. 空数据检查
    if filtered_df.empty:
        render_empty_state()
        return

    # 6. 计算指标 → 构建透视 → 渲染 UI
    metrics = calculate_metrics(filtered_df)
    pivot = build_pivot(filtered_df)
    render_summary(metrics)
    render_pivot_table(pivot)
    render_detail_section(filtered_df)

if __name__ == "__main__":
    main()
```"""
    )

    # ========== 工具函数速查 ==========
    st.markdown(
        "\n".join([
            "4. 工具函数来自 `app/core/`：",
            "   - `shared_source.py` — 获取共享 Excel 文件的会话状态",
            "   - `loader.py` — 加载工作簿、按别名提取工作表",
            "   - `filters.py` — 侧边栏联动筛选器",
            "5. 不需要修改 `main.py`、`app/core/` 中的任何文件或其他页面。",
        ])
    )


if __name__ == "__main__":
    main()
