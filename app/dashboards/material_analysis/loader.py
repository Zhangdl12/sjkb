"""Workbook loading helpers for the material analysis dashboard."""

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from app.core.loader import DataLoadError, load_excel_sheets
from app.dashboards.material_analysis.config import AppConfig


@dataclass(frozen=True)
class SourceTables:
    """Named source tables used by the material analysis dashboard."""

    creative: pd.DataFrame
    plan: pd.DataFrame
    sku: pd.DataFrame


def load_source_tables(
    file_source: str | Path | bytes | BinaryIO, config: AppConfig
) -> SourceTables:
    """Load the three source sheets required by material analysis."""

    sheets = load_excel_sheets(
        file_source,
        {
            "plan": config.plan_sheet,
            "creative": config.creative_sheet,
            "sku": config.sku_sheet,
        },
    )
    return SourceTables(
        creative=sheets["creative"],
        plan=sheets["plan"],
        sku=sheets["sku"],
    )
