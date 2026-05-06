"""Data processing for the material analysis dashboard."""

import numpy as np
import pandas as pd

from app.dashboards.material_analysis.config import AppConfig
from app.dashboards.material_analysis.loader import SourceTables


class DataProcessingError(Exception):
    """Raised when source data cannot be transformed into the analysis table."""


def build_analysis_dataset(
    tables: SourceTables | dict[str, pd.DataFrame], config: AppConfig
) -> pd.DataFrame:
    """Build the analysis-ready dataset from the uploaded workbook."""

    try:
        source_tables = _normalize_source_tables(tables)
        creative_df = source_tables.creative.copy()
        plan_df = source_tables.plan.copy()
        sku_df = source_tables.sku.copy()

        is_aitamei = creative_df[config.campaign_column].astype(str).str.contains(
            config.aitamei_keyword,
            na=False,
        )
        creative_df[config.aitamei_column] = np.where(
            is_aitamei,
            config.aitamei_value,
            config.other_aitamei,
        )

        plan_df = plan_df[
            [
                config.plan_type_column,
                config.new_product_channel_column,
                config.channel_type_column,
            ]
        ].drop_duplicates(subset=[config.plan_type_column])

        creative_df = pd.merge(
            creative_df,
            plan_df,
            on=config.plan_type_column,
            how="left",
        )
        creative_df[config.new_product_channel_column] = creative_df[
            config.new_product_channel_column
        ].fillna(config.unknown_channel)
        creative_df[config.channel_type_column] = creative_df[
            config.channel_type_column
        ].fillna(config.unknown_channel_type)

        merged_df = pd.merge(
            creative_df,
            sku_df[[config.jd_sku_id_column, config.category_column]],
            left_on=config.sku_id_column,
            right_on=config.jd_sku_id_column,
            how="left",
        )
        merged_df[config.category_column] = merged_df[config.category_column].fillna(
            config.unknown_category
        )

        merged_df[config.date_column] = pd.to_datetime(
            merged_df[config.date_column].astype(str),
            format="%Y%m%d",
            errors="coerce",
        )
        merged_df[config.year_column] = merged_df[config.date_column].dt.year
        merged_df[config.month_column] = merged_df[config.date_column].dt.month
        merged_df[config.day_column] = merged_df[config.date_column].apply(
            _format_day_value
        )

        return merged_df
    except KeyError as exc:
        raise DataProcessingError(
            f"数据缺少必要字段: {exc}. 请检查原表字段名是否与配置一致。"
        ) from exc
    except Exception as exc:
        raise DataProcessingError(
            "数据处理报错: "
            f"{exc}\n(请检查原表中是否存在 '日期'、'推广计划'、'跟单SKU ID' 等基础列名)"
        ) from exc


def _normalize_source_tables(
    tables: SourceTables | dict[str, pd.DataFrame],
) -> SourceTables:
    """Support both legacy SourceTables and generic sheet mappings."""

    if isinstance(tables, SourceTables):
        return tables

    return SourceTables(
        creative=tables["creative"],
        plan=tables["plan"],
        sku=tables["sku"],
    )


def _format_day_value(value: pd.Timestamp) -> str | float:
    """Format day values as `YYYY/M/D` strings for filtering."""

    if pd.isna(value):
        return np.nan
    return f"{value.year}/{value.month}/{value.day}"
