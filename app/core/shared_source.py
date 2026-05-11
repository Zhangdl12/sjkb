"""
管理所有看板共享上传数据源的会话状态。

核心机制：
  利用 Streamlit 的 st.session_state（类似服务端 session）存储上传的 Excel 文件，
  使首页上传的文件可以被所有看板页面访问。

存储的三个键（均在 session_state 中）：
  - shared_source_name  : 原始文件名（如 "惠氏数据源(新).xlsx"），用于页面展示
  - shared_source_bytes : 文件的原始字节内容，用于解析 Excel
  - shared_source_token : md5(bytes).hexdigest()，作为缓存标识，防止相同文件重复解析

使用方式：
  # 首页：保存上传的文件
  set_shared_source(file.name, file.getvalue())

  # 看板页面：检查并读取
  if has_shared_source():
      name = get_shared_source_name()
      bytes_data = get_shared_source_bytes()
      token = get_shared_source_token()
"""
from hashlib import md5

import streamlit as st

# ========== session_state 键名常量 ==========
# 所有模块通过这三个常量引用同一个 session_state 键，避免硬编码字符串
SHARED_SOURCE_NAME_KEY = "shared_source_name"
SHARED_SOURCE_BYTES_KEY = "shared_source_bytes"
SHARED_SOURCE_TOKEN_KEY = "shared_source_token"


def set_shared_source(file_name: str, file_bytes: bytes) -> None:
    """首页调用：把用户上传的 Excel 文件保存到当前会话。

    Args:
        file_name: 上传文件的原始名称（仅用于显示，不参与文件读取）
        file_bytes: 文件的完整字节内容
    """
    st.session_state[SHARED_SOURCE_NAME_KEY] = file_name
    st.session_state[SHARED_SOURCE_BYTES_KEY] = file_bytes
    # md5 哈希生成唯一标识，用作缓存键 —— 相同文件不会重复解析
    st.session_state[SHARED_SOURCE_TOKEN_KEY] = md5(file_bytes).hexdigest()


def clear_shared_source() -> None:
    """从当前会话中移除共享数据源（用户点击"清除"按钮时调用）。"""
    for key in (
        SHARED_SOURCE_NAME_KEY,
        SHARED_SOURCE_BYTES_KEY,
        SHARED_SOURCE_TOKEN_KEY,
    ):
        st.session_state.pop(key, None)  # pop(key, None) 避免 key 不存在时报错


def has_shared_source() -> bool:
    """检查当前会话是否已上传共享数据源。

    每个看板页面在启动时必须先调用此函数。如果返回 False，
    说明用户还没有在首页上传文件，页面应显示提示并 stop()。
    """
    return (
        SHARED_SOURCE_NAME_KEY in st.session_state
        and SHARED_SOURCE_BYTES_KEY in st.session_state
        and SHARED_SOURCE_TOKEN_KEY in st.session_state
    )


def get_shared_source_name() -> str | None:
    """获取共享数据源的文件名（如不存在则返回 None）。"""
    return st.session_state.get(SHARED_SOURCE_NAME_KEY)


def get_shared_source_bytes() -> bytes | None:
    """获取共享数据源的原始字节内容（如不存在则返回 None）。"""
    return st.session_state.get(SHARED_SOURCE_BYTES_KEY)


def get_shared_source_token() -> str | None:
    """获取共享数据源的缓存标识（如不存在则返回 None）。

    返回值是文件字节的 md5 十六进制字符串，用于 load_shared_workbook 的缓存键。
    """
    return st.session_state.get(SHARED_SOURCE_TOKEN_KEY)
