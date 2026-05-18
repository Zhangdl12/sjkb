import importlib.util
import unittest
from pathlib import Path

import pandas as pd

from app.dashboards.channel_analysis.config import AppConfig
from app.dashboards.channel_analysis.metrics import (
    build_period_summary,
    build_period_total,
    resolve_period_columns,
)
from app.dashboards.channel_analysis.processor import build_channel_analysis_dataset
from app.dashboards.channel_analysis.ui import _build_styler


PAGE_MODULE_PATH = Path(__file__).resolve().parents[1] / "pages" / "04_渠道分析.py"
SPEC = importlib.util.spec_from_file_location("channel_analysis_page", PAGE_MODULE_PATH)
channel_analysis_page = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(channel_analysis_page)


class TestChannelAnalysisMetrics(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AppConfig()

    def test_build_dataset_merges_plan_sku_and_time_fields(self) -> None:
        cfg = self.config
        result = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)

        known_row = result[result[cfg.ad_sku_id_column] == 1001].iloc[0]
        missing_row = result[result[cfg.ad_sku_id_column] == 9999].iloc[0]

        self.assertEqual(known_row[cfg.year_column], 2025)
        self.assertEqual(known_row[cfg.quarter_label_column], "Q1")
        self.assertEqual(known_row[cfg.month_label_column], "M1")
        self.assertEqual(known_row[cfg.week_label_column], "W1")
        self.assertEqual(known_row[cfg.day_label_column], "2025/1/1")
        self.assertEqual(known_row[cfg.new_channel_column], "站外广告")
        self.assertEqual(known_row[cfg.channel_type_column], "RTB")
        self.assertEqual(known_row[cfg.plan_aggregate_column], "计划A")
        self.assertEqual(known_row[cfg.brand_column], "惠氏")
        self.assertEqual(known_row[cfg.category_column], "奶粉")
        self.assertEqual(known_row[cfg.sku_product_name_column], "SKU表商品名")
        self.assertEqual(missing_row[cfg.new_channel_column], cfg.unknown_text)
        self.assertEqual(missing_row[cfg.brand_column], cfg.unknown_text)
        self.assertEqual(missing_row[cfg.sku_product_name_column], "广告商品C")

    def test_build_period_summary_calculates_channel_metrics(self) -> None:
        cfg = self.config
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)

        result = build_period_summary(dataset, "month", cfg)
        row = result[
            (result[cfg.period_label_column] == "M1")
            & (result[cfg.new_channel_column] == "站外广告")
        ].iloc[0]

        self.assertEqual(result.columns.tolist(), cfg.display_columns)
        self.assertEqual(row["广告费用"], 100)
        self.assertAlmostEqual(row["花费占比%"], 100 / 300, places=4)
        self.assertEqual(row["广告订单行"], 10)
        self.assertEqual(row["广告GMV"], 400)
        self.assertAlmostEqual(row["广告GMV占比"], 400 / 1000, places=4)
        self.assertAlmostEqual(row["广告ROI"], 4.0, places=4)
        self.assertAlmostEqual(row["广告CPC"], 2.0, places=4)
        self.assertAlmostEqual(row["广告CVR"], 10 / 50, places=4)
        self.assertAlmostEqual(row["广告CTR"], 50 / 1000, places=4)
        self.assertEqual(row["广告新客"], 5)
        self.assertAlmostEqual(row["广告新客成本"], 20.0, places=4)

    def test_roi_change_ratio_follows_current_period_and_channel(self) -> None:
        cfg = self.config
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)

        result = build_period_summary(dataset, "month", cfg)
        feb_row = result[
            (result[cfg.period_label_column] == "M2")
            & (result[cfg.new_channel_column] == "站外广告")
        ].iloc[0]

        self.assertAlmostEqual(feb_row["广告ROI"], 3.0, places=4)
        self.assertAlmostEqual(feb_row["ROI环比"], -0.25, places=4)

    def test_build_period_total_calculates_top_total_rows(self) -> None:
        cfg = self.config
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)

        result = build_period_total(dataset, "month", cfg)
        total_row = result.iloc[0]

        self.assertEqual(len(result), 1)
        self.assertEqual(result.columns.tolist(), cfg.display_columns)
        self.assertEqual(total_row[cfg.period_label_column], "总计")
        self.assertEqual(total_row[cfg.new_channel_column], "总计")
        self.assertEqual(total_row["广告费用"], 350)
        self.assertEqual(total_row["花费占比%"], 1.0)
        self.assertEqual(total_row["广告订单行"], 33)
        self.assertEqual(total_row["广告GMV"], 1150)
        self.assertEqual(total_row["广告GMV占比"], 1.0)
        self.assertAlmostEqual(total_row["广告ROI"], 1150 / 350, places=4)
        self.assertAlmostEqual(total_row["广告CPC"], 350 / 160, places=4)
        self.assertAlmostEqual(total_row["广告CVR"], 33 / 160, places=4)
        self.assertAlmostEqual(total_row["广告CTR"], 160 / 3500, places=4)
        self.assertEqual(total_row["广告新客"], 15)
        self.assertAlmostEqual(total_row["广告新客成本"], 350 / 15, places=4)
        self.assertTrue(pd.isna(total_row["ROI环比"]))

    def test_zero_denominator_returns_zero(self) -> None:
        cfg = self.config
        df = pd.DataFrame(
            {
                cfg.year_column: [2025],
                cfg.month_label_column: ["M1"],
                cfg.month_sort_column: [1],
                cfg.new_channel_column: ["站外广告"],
                cfg.ad_cost_column: [0],
                cfg.ad_order_row_column: [0],
                cfg.ad_gmv_column: [0],
                cfg.ad_click_column: [0],
                cfg.ad_impression_column: [0],
                cfg.ad_new_customer_column: [0],
            }
        )

        result = build_period_summary(df, "month", cfg).iloc[0]

        self.assertEqual(result["广告ROI"], 0.0)
        self.assertEqual(result["广告CPC"], 0.0)
        self.assertEqual(result["广告CVR"], 0.0)
        self.assertEqual(result["广告CTR"], 0.0)
        self.assertEqual(result["广告新客成本"], 0.0)

    def test_period_total_zero_denominator_returns_zero(self) -> None:
        cfg = self.config
        df = pd.DataFrame(
            {
                cfg.year_column: [2025],
                cfg.month_label_column: ["M1"],
                cfg.month_sort_column: [1],
                cfg.ad_cost_column: [0],
                cfg.ad_order_row_column: [0],
                cfg.ad_gmv_column: [0],
                cfg.ad_click_column: [0],
                cfg.ad_impression_column: [0],
                cfg.ad_new_customer_column: [0],
            }
        )

        result = build_period_total(df, "month", cfg).iloc[0]

        self.assertEqual(result[cfg.period_label_column], "总计")
        self.assertEqual(result[cfg.new_channel_column], "总计")
        self.assertEqual(result["花费占比%"], 1.0)
        self.assertEqual(result["广告GMV占比"], 1.0)
        self.assertEqual(result["广告ROI"], 0.0)
        self.assertEqual(result["广告CPC"], 0.0)
        self.assertEqual(result["广告CVR"], 0.0)
        self.assertEqual(result["广告CTR"], 0.0)
        self.assertEqual(result["广告新客成本"], 0.0)

    def test_period_mapping_contains_five_tabs(self) -> None:
        cfg = self.config
        period_tabs = channel_analysis_page.get_period_tabs(cfg)

        self.assertEqual([label for label, _ in period_tabs], ["年", "季度", "月", "周", "日"])
        self.assertEqual(channel_analysis_page.resolve_selected_period("月", period_tabs), "month")
        self.assertEqual(resolve_period_columns("year", cfg)[0], cfg.year_column)
        self.assertEqual(resolve_period_columns("quarter", cfg)[0], cfg.quarter_label_column)
        self.assertEqual(resolve_period_columns("month", cfg)[0], cfg.month_label_column)
        self.assertEqual(resolve_period_columns("week", cfg)[0], cfg.week_label_column)
        self.assertEqual(resolve_period_columns("day", cfg)[0], cfg.day_label_column)

    def test_filter_fields_include_time_and_business_dimensions(self) -> None:
        cfg = self.config
        fields = channel_analysis_page.build_filter_fields(cfg)
        columns = [field.column for field in fields]

        self.assertEqual(
            columns,
            [
                cfg.year_column,
                cfg.quarter_label_column,
                cfg.month_label_column,
                cfg.week_label_column,
                cfg.day_label_column,
                cfg.channel_type_column,
                cfg.new_channel_column,
                cfg.plan_aggregate_column,
                cfg.brand_column,
                cfg.category_column,
                cfg.sku_product_name_column,
            ],
        )
        self.assertTrue(fields[0].default_latest)
        self.assertEqual(fields[0].control, "single_select")

    def test_build_period_tables_returns_summary_and_total(self) -> None:
        cfg = self.config
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)

        summary_df, total_df = channel_analysis_page.build_period_tables(dataset, "month", cfg)

        self.assertGreater(len(summary_df), 0)
        self.assertEqual(len(total_df), 1)
        self.assertEqual(total_df.iloc[0][cfg.period_label_column], "总计")
        self.assertEqual(total_df.iloc[0][cfg.new_channel_column], "总计")

    def test_build_styler_sets_readable_cell_background_for_dark_mode(self) -> None:
        cfg = self.config
        df = pd.DataFrame(
            {
                cfg.period_label_column: ["2026"],
                cfg.new_channel_column: ["站外广告"],
                "广告费用": [100],
                "ROI环比": [0.1],
            }
        )

        html = _build_styler(df).to_html()

        self.assertIn("background-color: #ffffff", html)
        self.assertIn("color: #111111", html)


def _build_source_tables(cfg: AppConfig) -> dict[str, pd.DataFrame]:
    return {
        "ad": pd.DataFrame(
            {
                cfg.ad_date_column: [20250101, 20250102, 20250201, 20250103],
                cfg.ad_plan_type_column: ["计划1", "计划2", "计划1", "缺失计划"],
                cfg.ad_sku_id_column: [1001, 1002, 1001, 9999],
                cfg.ad_product_name_column: ["广告商品A", "广告商品B", "广告商品A", "广告商品C"],
                cfg.ad_cost_column: [100, 200, 50, 0],
                cfg.ad_order_row_column: [10, 20, 3, 0],
                cfg.ad_gmv_column: [400, 600, 150, 0],
                cfg.ad_click_column: [50, 100, 10, 0],
                cfg.ad_impression_column: [1000, 2000, 500, 0],
                cfg.ad_new_customer_column: [5, 10, 0, 0],
            }
        ),
        "plan": pd.DataFrame(
            {
                cfg.plan_type_column: ["计划1", "计划2"],
                cfg.plan_aggregate_column: ["计划A", "计划B"],
                cfg.new_channel_column: ["站外广告", "站内广告"],
                cfg.channel_type_column: ["RTB", "搜索"],
            }
        ),
        "sku": pd.DataFrame(
            {
                cfg.sku_id_column: [1001, 1002],
                cfg.sku_product_name_column: ["SKU表商品名", "SKU表商品B"],
                cfg.category_column: ["奶粉", "营养品"],
                cfg.brand_column: ["惠氏", "启赋"],
            }
        ),
    }


if __name__ == "__main__":
    unittest.main()
