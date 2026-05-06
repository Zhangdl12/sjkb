"""新增看板示例页面。"""

import streamlit as st

from app.core.shared_source import get_shared_source_name, has_shared_source
from app.dashboards.example_dashboard.config import (
    EXAMPLE_DASHBOARD_DESCRIPTION,
    EXAMPLE_DASHBOARD_TITLE,
)


def main() -> None:
    """渲染后续新增看板的接入说明。"""

    st.set_page_config(page_title=EXAMPLE_DASHBOARD_TITLE, page_icon="🧩", layout="wide")
    st.title(EXAMPLE_DASHBOARD_TITLE)
    st.caption(EXAMPLE_DASHBOARD_DESCRIPTION)

    if has_shared_source():
        st.info(f"当前共享数据源：`{get_shared_source_name()}`")
    else:
        st.warning("当前还没有共享数据源。正式业务看板会要求先在首页上传 Excel 文件。")

    st.markdown("### 新增一个业务看板时需要做的事")
    st.markdown(
        "\n".join(
            [
                "1. 在 `app/dashboards/<dashboard_name>/config.py` 中定义一个 `DashboardPageConfig`。",
                "2. 在配置中声明 `required_sheets`、筛选字段、默认透视维度和业务处理函数。",
                "3. 在 `pages/` 下新增一个页面文件，只导入配置并调用 `run_dashboard_page()`。",
                "4. 不需要修改通用运行器、共享数据源逻辑或其他页面入口。",
            ]
        )
    )


if __name__ == "__main__":
    main()
