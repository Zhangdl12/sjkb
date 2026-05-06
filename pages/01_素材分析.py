"""Material analysis dashboard page."""

from app.core.page_runner import run_dashboard_page
from app.dashboards.material_analysis.config import MATERIAL_ANALYSIS_CONFIG


def main() -> None:
    """Run the material analysis dashboard."""

    run_dashboard_page(MATERIAL_ANALYSIS_CONFIG)


if __name__ == "__main__":
    main()
