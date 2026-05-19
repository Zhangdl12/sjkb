"""
共享数据源和打标文件管理首页。

这是整个看板系统的入口页面。用户在这里上传一次 Excel 文件，
文件内容会被保存到 Streamlit 的会话状态（session_state）中，
后续所有看板页面共享这份数据，无需重复上传。

数据流：
  上传业务数据源 Excel → set_shared_source() → session_state → 各页面读取业务数据
  上传打标 Excel → set_tag_source() → session_state → 标签检验表读取打标数据
"""
import streamlit as st

from app.core.shared_source import (
    clear_tag_source,
    clear_shared_source,
    get_tag_source_name,
    get_shared_source_name,
    set_tag_source,
    set_shared_source,
)


def main() -> None:
    # ========== 页面基本设置 ==========
    # layout="wide" 让页面使用宽屏布局，给后面的看板表格留更多空间
    st.set_page_config(page_title="看板数据源管理", page_icon="📁", layout="wide")
    st.title("看板数据源管理")
    st.caption("先在这里上传业务数据源；标签检验表还需要额外上传打标文件。")

    # ========== 文件上传区域 ==========
    # 两个上传控件分别保存到不同的 session_state 键，避免业务数据源和打标文件互相覆盖。
    source_file = st.file_uploader(
        "上传业务数据源 Excel",
        type=["xlsx", "xls"],
        key="business_source_uploader",
    )
    if source_file is not None:
        # 将文件名和原始字节保存到 session_state，getvalue() 获取上传文件的完整字节内容。
        set_shared_source(source_file.name, source_file.getvalue())
        st.success(f"已加载业务数据源：`{source_file.name}`")

    tag_file = st.file_uploader(
        "上传打标 Excel（标签检验表使用）",
        type=["xlsx", "xls"],
        key="tag_source_uploader",
    )
    if tag_file is not None:
        # 打标文件独立保存，标签检验表会从这里读取关键词、人群、商品三类打标 sheet。
        set_tag_source(tag_file.name, tag_file.getvalue())
        st.success(f"已加载打标文件：`{tag_file.name}`")

    # ========== 当前数据源状态 ==========
    current_source = get_shared_source_name()
    if current_source:
        # 已有数据源：显示文件名 + 提供清除按钮
        st.info(f"当前业务数据源：`{current_source}`")
        if st.button("清除业务数据源"):
            clear_shared_source()
            st.rerun()  # 清除后刷新页面，回到"未上传"状态
    else:
        # 尚未上传：提示用户先上传
        st.warning("当前尚未上传业务数据源。请先上传文件，再进入侧栏中的看板页面。")

    current_tag_source = get_tag_source_name()
    if current_tag_source:
        # 打标文件仅标签检验表强依赖，其他看板不需要它也能继续使用。
        st.info(f"当前打标文件：`{current_tag_source}`")
        if st.button("清除打标文件"):
            clear_tag_source()
            st.rerun()
    else:
        st.warning("当前尚未上传打标文件。标签检验表需要上传后才能使用。")

    # ========== 使用说明 ==========
    st.markdown("### 使用说明")
    st.markdown(
        "\n".join(
            [
                "1. 在本页上传业务数据源 Excel，系统会把文件保存在当前会话中。",
                "2. 标签检验表还需要上传打标 Excel，用于关键词、人群、SKU 分类匹配。",
                "3. 广告数据汇总等分析页会复用当前业务数据源；部分页面还会复用打标文件。",
                "4. 后续新增看板时，只需要新增 `pages/*.py` 和对应的看板配置模块。",
            ]
        )
    )


if __name__ == "__main__":
    main()
