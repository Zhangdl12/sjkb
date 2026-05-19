import importlib.util
import unittest
from pathlib import Path

import pandas as pd

from app.dashboards.cps_analysis.config import AppConfig
from app.dashboards.cps_analysis.processor import build_cps_analysis_dataset
from app.dashboards.cps_analysis.service import build_cps_analysis_payload, build_filter_summary
from app.dashboards.cps_analysis.tree_builder import build_cps_tree_summary
from app.dashboards.cps_analysis.ui import _build_column_def, _build_tree_grid_options


PAGE_MODULE_PATH = Path(__file__).resolve().parents[1] / "pages" / "06_CPS分析.py"
SPEC = importlib.util.spec_from_file_location("cps_analysis_page", PAGE_MODULE_PATH)
cps_analysis_page = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(cps_analysis_page)


class TestCpsAnalysis(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AppConfig()

    def test_build_dataset_merges_sku_tag_and_adds_time_fields(self) -> None:
        cfg = self.config
        result = build_cps_analysis_dataset(_build_source_tables(cfg), cfg)

        tagged_row = result[result[cfg.sku_column] == "1001"].iloc[0]
        unknown_row = result[result[cfg.sku_column] == "9999"].iloc[0]

        self.assertEqual(len(result), 4)
        self.assertEqual(tagged_row[cfg.product_name_column], "启赋蓝钻")
        self.assertEqual(tagged_row[cfg.brand_column], "惠氏")
        self.assertEqual(unknown_row[cfg.product_name_column], cfg.unknown_text)
        self.assertEqual(unknown_row[cfg.brand_column], cfg.unknown_text)
        self.assertEqual(tagged_row[cfg.year_column], 2025)
        self.assertEqual(tagged_row[cfg.month_label_column], "M1")
        self.assertEqual(tagged_row[cfg.week_label_column], "W1")
        self.assertEqual(tagged_row[cfg.day_label_column], "2025/1/1")

    def test_tree_summary_has_parent_rows_and_ratio_metrics(self) -> None:
        cfg = self.config
        dataset = build_cps_analysis_dataset(_build_source_tables(cfg), cfg)
        result = build_cps_tree_summary(dataset, cfg)

        leader_row = result[result["path"] == "团长A"].iloc[0]
        day_row = result[result["path"] == "团长A||2025/1/1"].iloc[0]
        product_row = result[result["path"] == "团长A||2025/1/1||启赋蓝钻"].iloc[0]
        zero_row = result[result["path"] == "团长B||2025/1/3||启赋有机"].iloc[0]
        unknown_row = result[result["path"] == "团长A||2025/1/2||未知"].iloc[0]

        self.assertEqual(leader_row[cfg.display_commission_base_column], 350)
        self.assertEqual(leader_row[cfg.display_total_commission_column], 35)
        self.assertAlmostEqual(leader_row[cfg.commission_rate_column], 35 / 350, places=4)
        self.assertEqual(day_row[cfg.display_commission_base_column], 300)
        self.assertEqual(day_row[cfg.display_total_commission_column], 30)
        self.assertEqual(product_row[cfg.display_commission_base_column], 300)
        self.assertEqual(product_row[cfg.display_total_commission_column], 30)
        self.assertAlmostEqual(product_row[cfg.commission_rate_column], 0.1, places=4)
        self.assertEqual(zero_row[cfg.commission_rate_column], 0.0)
        self.assertEqual(unknown_row[cfg.display_commission_base_column], 50)
        self.assertEqual(unknown_row[cfg.display_total_commission_column], 5)

    def test_payload_applies_filters_and_page_helpers_are_stable(self) -> None:
        cfg = self.config
        dataset = build_cps_analysis_dataset(_build_source_tables(cfg), cfg)
        fields = cps_analysis_page.build_filter_fields(cfg)
        payload = build_cps_analysis_payload(
            {"dataset": dataset},
            {cfg.leader_column: ["团长A"]},
            fields,
            cfg,
        )

        self.assertFalse(payload.tree_df.empty)
        self.assertIn("团长A", payload.tree_df["path"].tolist())
        self.assertNotIn("团长B", payload.tree_df["path"].tolist())
        self.assertEqual(fields[0].column, cfg.year_column)
        self.assertEqual(fields[0].control, "single_select")

    def test_filter_summary_and_grid_options_are_stable(self) -> None:
        cfg = self.config
        summary = build_filter_summary({cfg.leader_column: ["团长A"], cfg.year_column: 2025})
        grid_options = _build_tree_grid_options(
            pd.DataFrame(
                {
                    "path": ["团长A"],
                    cfg.display_commission_base_column: [100],
                    cfg.commission_rate_column: [0.1],
                }
            ),
            hidden_columns={"path"},
            group_header="团长 > 日期 > 产品",
        )
        percent_column = _build_column_def(cfg.commission_rate_column)
        amount_column = _build_column_def(cfg.display_commission_base_column)

        self.assertEqual(summary, (("年", (2025,)), ("所属计划/活动", ("团长A",))))
        self.assertTrue(grid_options["treeData"])
        self.assertEqual(grid_options["groupDefaultExpanded"], 0)
        self.assertIn("valueFormatter", percent_column)
        self.assertIn("tooltipValueGetter", percent_column)
        self.assertIn("valueFormatter", amount_column)
        self.assertIn("tooltipValueGetter", amount_column)


def _build_source_tables(cfg: AppConfig) -> dict[str, pd.DataFrame]:
    return {
        "cps": pd.DataFrame(
            {
                cfg.sku_column: [1001, "1001.0", 9999, 1002],
                cfg.date_source_column: [20250101, "2025/1/1", 20250102, 20250103],
                cfg.leader_column: ["团长A", "团长A", "团长A", "团长B"],
                cfg.commission_base_column: [100, 200, 50, 0],
                cfg.total_commission_column: [10, 20, 5, 3],
            }
        ),
        "sku_tag": pd.DataFrame(
            {
                cfg.sku_id_column: [1001, 1002],
                cfg.product_name_column: ["启赋蓝钻", "启赋有机"],
                cfg.brand_column: ["惠氏", "惠氏"],
            }
        ),
    }


if __name__ == "__main__":
    unittest.main()
