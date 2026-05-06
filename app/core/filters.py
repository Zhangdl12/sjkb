"""Generic sidebar filter helpers."""

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st


@dataclass(frozen=True)
class FilterField:
    """Definition of a single sidebar filter widget."""

    column: str
    label: str | None = None
    group: str = "筛选条件"
    sort_values: bool = False
    default_all: bool = True


def build_filter_options(
    df: pd.DataFrame,
    fields: list[FilterField] | tuple[FilterField, ...],
) -> dict[str, list[Any]]:
    """Build filter option lists for all configured fields."""

    return {
        field.column: _extract_options(df, field.column, field.sort_values)
        for field in fields
    }


def render_sidebar_filters(
    df: pd.DataFrame,
    fields: list[FilterField] | tuple[FilterField, ...],
    title: str = "维度筛选器",
    key_prefix: str = "dashboard_filter",
) -> dict[str, list[Any]]:
    """Render grouped sidebar filters with dynamic downstream narrowing."""

    st.sidebar.header(title)
    selections: dict[str, list[Any]] = {}

    grouped_fields: OrderedDict[str, list[FilterField]] = OrderedDict()
    for field in fields:
        grouped_fields.setdefault(field.group, []).append(field)

    for group_name, group_fields in grouped_fields.items():
        st.sidebar.subheader(group_name)
        for field in group_fields:
            filtered_df = apply_filters(df, selections, fields)
            options = _extract_options(filtered_df, field.column, field.sort_values)
            state_key = f"{key_prefix}_{field.column}"
            previous_selection = st.session_state.get(state_key, [])
            default = [value for value in previous_selection if value in options]
            if not default and field.default_all:
                default = options

            selections[field.column] = st.sidebar.multiselect(
                field.label or field.column,
                options=options,
                default=default,
                key=state_key,
            )

    return selections


def apply_filters(
    df: pd.DataFrame,
    selections: dict[str, list[Any]],
    fields: list[FilterField] | tuple[FilterField, ...],
) -> pd.DataFrame:
    """Apply active sidebar filters in field order."""

    filtered_df = df.copy()
    for field in fields:
        selected_values = selections.get(field.column, [])
        if selected_values and field.column in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[field.column].isin(selected_values)]
    return filtered_df


def _extract_options(df: pd.DataFrame, column: str, sort_values: bool) -> list[Any]:
    """Extract unique option values for one filter column."""

    if column not in df.columns:
        return []

    values = df[column].dropna().unique().tolist()
    if sort_values:
        values = sorted(values)
    return values
