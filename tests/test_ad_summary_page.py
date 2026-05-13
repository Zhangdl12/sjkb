import importlib.util
import unittest
from pathlib import Path

import pandas as pd

from app.dashboards.ad_summary.config import AppConfig


PAGE_MODULE_PATH = Path(__file__).resolve().parents[1] / "pages" / "03_广告数据汇总.py"
SPEC = importlib.util.spec_from_file_location("ad_summary_page", PAGE_MODULE_PATH)
ad_summary_page = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ad_summary_page)


class TestAdSummaryPage(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AppConfig()

    def test_drop_day_click_yoy_column_only_affects_day_period(self) -> None:
        df = pd.DataFrame(
            {
                "周期": ["M1"],
                "广告点击季度同比": [0.5],
                "广告点击": [10],
            }
        )

        day_df = ad_summary_page._drop_day_click_yoy_column(df, "day")
        month_df = ad_summary_page._drop_day_click_yoy_column(df, "month")

        self.assertNotIn("广告点击季度同比", day_df.columns)
        self.assertIn("广告点击季度同比", month_df.columns)

    def test_build_yoy_selections_uses_period_time_scope(self) -> None:
        cfg = self.config
        selections = {
            cfg.year_column: 2025,
            cfg.quarter_label_column: ["Q1"],
            cfg.month_label_column: ["M1"],
            cfg.week_label_column: ["W1"],
            cfg.day_label_column: ["2025/1/1"],
        }

        yoy_selections = ad_summary_page._build_yoy_selections(selections, cfg)

        self.assertEqual(yoy_selections[cfg.year_column], [2024, 2025])
        self.assertEqual(yoy_selections[cfg.day_label_column], ["2025/1/1", "2024/1/1"])

    def test_build_period_yoy_source_df_skips_day_period(self) -> None:
        cfg = self.config
        df = pd.DataFrame(
            {
                cfg.year_column: [2024, 2025],
                cfg.day_label_column: ["2024/1/1", "2025/1/1"],
            }
        )
        filter_fields = (
            ad_summary_page.FilterField(
                cfg.year_column,
                group="时间",
                sort_values=True,
                control="single_select",
                default_latest=True,
            ),
            ad_summary_page.FilterField(cfg.day_label_column, label="日期", group="时间", sort_values=True),
        )
        selections = {
            cfg.year_column: 2025,
            cfg.day_label_column: ["2025/1/1"],
        }

        day_yoy_df = ad_summary_page._build_period_yoy_source_df(df, selections, filter_fields, cfg, "day")
        month_yoy_df = ad_summary_page._build_period_yoy_source_df(df, selections, filter_fields, cfg, "month")

        self.assertIsNone(day_yoy_df)
        self.assertEqual(month_yoy_df[cfg.day_label_column].tolist(), ["2024/1/1", "2025/1/1"])

    def test_shop_metric_selections_ignore_ad_side_dimensions(self) -> None:
        cfg = self.config
        selections = {
            cfg.year_column: 2025,
            cfg.quarter_label_column: ["Q1"],
            cfg.channel_type_column: ["RTB"],
            cfg.new_channel_column: ["站外广告"],
            cfg.brand_column: ["惠氏"],
        }

        shop_metric_selections = {
            column: value
            for column, value in selections.items()
            if column
            not in {
                cfg.channel_type_column,
                cfg.new_channel_column,
            }
        }

        self.assertNotIn(cfg.channel_type_column, shop_metric_selections)
        self.assertNotIn(cfg.new_channel_column, shop_metric_selections)
        self.assertIn(cfg.brand_column, shop_metric_selections)


if __name__ == "__main__":
    unittest.main()
