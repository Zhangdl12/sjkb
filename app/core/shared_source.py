"""管理所有看板共享上传数据源的会话状态。"""

from hashlib import md5

import streamlit as st


SHARED_SOURCE_NAME_KEY = "shared_source_name"
SHARED_SOURCE_BYTES_KEY = "shared_source_bytes"
SHARED_SOURCE_TOKEN_KEY = "shared_source_token"


def set_shared_source(file_name: str, file_bytes: bytes) -> None:
    """把上传的数据源保存到当前 Streamlit 会话中。"""

    st.session_state[SHARED_SOURCE_NAME_KEY] = file_name
    st.session_state[SHARED_SOURCE_BYTES_KEY] = file_bytes
    st.session_state[SHARED_SOURCE_TOKEN_KEY] = md5(file_bytes).hexdigest()


def clear_shared_source() -> None:
    """从当前会话中移除共享数据源。"""

    for key in (
        SHARED_SOURCE_NAME_KEY,
        SHARED_SOURCE_BYTES_KEY,
        SHARED_SOURCE_TOKEN_KEY,
    ):
        st.session_state.pop(key, None)


def has_shared_source() -> bool:
    """判断当前会话中是否已经存在共享数据源。"""

    return (
        SHARED_SOURCE_NAME_KEY in st.session_state
        and SHARED_SOURCE_BYTES_KEY in st.session_state
        and SHARED_SOURCE_TOKEN_KEY in st.session_state
    )


def get_shared_source_name() -> str | None:
    """获取当前共享数据源的文件名。"""

    return st.session_state.get(SHARED_SOURCE_NAME_KEY)


def get_shared_source_bytes() -> bytes | None:
    """获取当前共享数据源的原始字节内容。"""

    return st.session_state.get(SHARED_SOURCE_BYTES_KEY)


def get_shared_source_token() -> str | None:
    """获取当前共享数据源的缓存标识。"""

    return st.session_state.get(SHARED_SOURCE_TOKEN_KEY)
