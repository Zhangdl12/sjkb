"""素材分析看板页面入口。"""

from app.core.page_runner import run_dashboard_page
from app.dashboards.material_analysis.config import MATERIAL_ANALYSIS_CONFIG


def main() -> None:
    """运行素材分析看板页面。"""

    run_dashboard_page(MATERIAL_ANALYSIS_CONFIG)


if __name__ == "__main__":
    main()
