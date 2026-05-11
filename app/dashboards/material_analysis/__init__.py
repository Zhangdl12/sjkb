"""素材分析看板实现包。"""

from app.dashboards.material_analysis.config import AppConfig, DEFAULT_CONFIG
from app.dashboards.material_analysis.loader import SourceTables
from app.dashboards.material_analysis.metrics import (
    SummaryMetrics,
    build_pivot_table,
    calculate_summary_metrics,
)
from app.dashboards.material_analysis.processor import (
    DataProcessingError,
    build_analysis_dataset,
)
from app.dashboards.material_analysis.ui import (
    render_detail_section,
    render_empty_state,
    render_pivot_table,
    render_summary,
)

__all__ = [
    "AppConfig",
    "DEFAULT_CONFIG",
    "SourceTables",
    "SummaryMetrics",
    "build_pivot_table",
    "calculate_summary_metrics",
    "DataProcessingError",
    "build_analysis_dataset",
    "render_detail_section",
    "render_empty_state",
    "render_pivot_table",
    "render_summary",
]
