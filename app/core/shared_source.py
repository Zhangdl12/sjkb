"""Shared uploaded workbook state for all dashboard pages."""

from hashlib import md5

import streamlit as st


SHARED_SOURCE_NAME_KEY = "shared_source_name"
SHARED_SOURCE_BYTES_KEY = "shared_source_bytes"
SHARED_SOURCE_TOKEN_KEY = "shared_source_token"


def set_shared_source(file_name: str, file_bytes: bytes) -> None:
    """Persist the uploaded source file in the current Streamlit session."""

    st.session_state[SHARED_SOURCE_NAME_KEY] = file_name
    st.session_state[SHARED_SOURCE_BYTES_KEY] = file_bytes
    st.session_state[SHARED_SOURCE_TOKEN_KEY] = md5(file_bytes).hexdigest()


def clear_shared_source() -> None:
    """Remove the shared source file from the current session."""

    for key in (
        SHARED_SOURCE_NAME_KEY,
        SHARED_SOURCE_BYTES_KEY,
        SHARED_SOURCE_TOKEN_KEY,
    ):
        st.session_state.pop(key, None)


def has_shared_source() -> bool:
    """Return whether a shared source is available in the current session."""

    return (
        SHARED_SOURCE_NAME_KEY in st.session_state
        and SHARED_SOURCE_BYTES_KEY in st.session_state
        and SHARED_SOURCE_TOKEN_KEY in st.session_state
    )


def get_shared_source_name() -> str | None:
    """Return the current shared source file name."""

    return st.session_state.get(SHARED_SOURCE_NAME_KEY)


def get_shared_source_bytes() -> bytes | None:
    """Return the raw bytes of the current shared source file."""

    return st.session_state.get(SHARED_SOURCE_BYTES_KEY)


def get_shared_source_token() -> str | None:
    """Return the stable cache token of the current shared source file."""

    return st.session_state.get(SHARED_SOURCE_TOKEN_KEY)
