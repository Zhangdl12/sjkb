"""Root entrypoint for shared data source management."""

import streamlit as st

from app.core.shared_source import (
    clear_shared_source,
    get_shared_source_name,
    set_shared_source,
)


def main() -> None:
    """Render the shared data source management page."""

    st.set_page_config(page_title="看板数据源管理", page_icon="📁", layout="wide")
    st.title("看板数据源管理")
    st.caption("先在这里上传一次 Excel 数据源，随后再从侧栏进入各个看板页面。")

    uploaded_file = st.file_uploader("上传共享 Excel 数据源", type=["xlsx", "xls"])
    if uploaded_file is not None:
        set_shared_source(uploaded_file.name, uploaded_file.getvalue())
        st.success(f"已加载共享数据源：`{uploaded_file.name}`")

    current_source = get_shared_source_name()
    if current_source:
        st.info(f"当前共享数据源：`{current_source}`")
        if st.button("清除当前数据源"):
            clear_shared_source()
            st.rerun()
    else:
        st.warning("当前尚未上传共享数据源。请先上传文件，再进入侧栏中的看板页面。")

    st.markdown("### 使用说明")
    st.markdown(
        "\n".join(
            [
                "1. 在本页上传 Excel 文件，系统会把文件保存在当前会话中。",
                "2. 侧栏中的业务页面会共享这份数据源，不需要重复上传。",
                "3. 后续新增看板时，只需要新增 `pages/*.py` 和对应的看板配置模块。",
            ]
        )
    )


if __name__ == "__main__":
    main()
