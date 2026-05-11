"""
共享数据源管理首页。

这是整个看板系统的入口页面。用户在这里上传一次 Excel 文件，
文件内容会被保存到 Streamlit 的会话状态（session_state）中，
后续所有看板页面共享这份数据，无需重复上传。

数据流：
  上传 Excel → set_shared_source() → session_state → 各页面通过 get_* 函数读取
"""
import streamlit as st

from app.core.shared_source import (
    clear_shared_source,
    get_shared_source_name,
    set_shared_source,
)


def main() -> None:
    # ========== 页面基本设置 ==========
    # layout="wide" 让页面使用宽屏布局，给后面的看板表格留更多空间
    st.set_page_config(page_title="看板数据源管理", page_icon="📁", layout="wide")
    st.title("看板数据源管理")
    st.caption("先在这里上传一次 Excel 数据源，随后再从侧栏进入各个看板页面。")

    # ========== 文件上传区域 ==========
    # file_uploader 返回 None 直到用户选择了文件
    # type 限制只能上传 Excel 格式
    uploaded_file = st.file_uploader("上传共享 Excel 数据源", type=["xlsx", "xls"])
    if uploaded_file is not None:
        # 将文件名和原始字节保存到 session_state
        # getvalue() 获取上传文件的完整字节内容
        set_shared_source(uploaded_file.name, uploaded_file.getvalue())
        st.success(f"已加载共享数据源：`{uploaded_file.name}`")

    # ========== 当前数据源状态 ==========
    current_source = get_shared_source_name()
    if current_source:
        # 已有数据源：显示文件名 + 提供清除按钮
        st.info(f"当前共享数据源：`{current_source}`")
        if st.button("清除当前数据源"):
            clear_shared_source()
            st.rerun()  # 清除后刷新页面，回到"未上传"状态
    else:
        # 尚未上传：提示用户先上传
        st.warning("当前尚未上传共享数据源。请先上传文件，再进入侧栏中的看板页面。")

    # ========== 使用说明 ==========
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
