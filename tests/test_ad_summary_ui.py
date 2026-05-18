import unittest

import pandas as pd

from app.dashboards.ad_summary.config import AppConfig
from app.dashboards.ad_summary.ui import _build_styler, _get_click_yoy_label, _get_column_config


class TestAdSummaryUi(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AppConfig()

    def test_get_click_yoy_label_matches_period_dimension(self) -> None:
        self.assertEqual(_get_click_yoy_label("quarter"), "广告点击季度同比")
        self.assertEqual(_get_click_yoy_label("month"), "广告点击月度同比")
        self.assertEqual(_get_click_yoy_label("week"), "广告点击周度同比")
        self.assertEqual(_get_click_yoy_label("day"), "广告点击同比")

    def test_get_column_config_uses_period_specific_click_yoy_label(self) -> None:
        month_df = pd.DataFrame({"广告点击季度同比": [0.1], self.config.shop_gmv_tail_column: [1]})
        month_config = _get_column_config(month_df, self.config, "month")
        self.assertEqual(month_config["广告点击季度同比"]["label"], "广告点击月度同比")

    def test_get_column_config_skips_missing_click_yoy_column(self) -> None:
        day_df = pd.DataFrame(
            {
                "周期": ["2025/1/1"],
                "广告点击": [10],
                self.config.shop_gmv_tail_column: [100],
                self.config.shop_gmv_ratio_tail_column: [0.1],
            }
        )

        day_config = _get_column_config(day_df, self.config, "day")

        self.assertNotIn("广告点击季度同比", day_config)

    def test_build_styler_handles_missing_click_yoy_column(self) -> None:
        df = pd.DataFrame(
            {
                self.config.period_label_column: ["2025/1/1"],
                "广告点击": [10],
                "消耗环比": [0.1],
                self.config.shop_gmv_tail_column: [100],
                self.config.shop_gmv_ratio_tail_column: [0.1],
            }
        )

        styler = _build_styler(df, self.config)

        self.assertIsNotNone(styler)

    def test_build_styler_sets_readable_cell_background_for_dark_mode(self) -> None:
        df = pd.DataFrame(
            {
                self.config.period_label_column: ["2025/1/1"],
                "广告点击": [10],
                "广告ROI": [2.5],
            }
        )

        html = _build_styler(df, self.config).to_html()

        self.assertIn("background-color: #ffffff", html)
        self.assertIn("color: #111111", html)


if __name__ == "__main__":
    unittest.main()
