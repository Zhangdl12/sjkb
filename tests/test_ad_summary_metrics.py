import unittest

import pandas as pd

from app.dashboards.ad_summary.config import AppConfig
from app.dashboards.ad_summary.metrics import (
    _build_change_ratio,
    _build_yoy_ratio,
    build_period_summary,
)
from app.dashboards.ad_summary.processor import build_ad_summary_dataset


class TestAdSummaryMetrics(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AppConfig()

    def test_build_ad_summary_dataset_merges_ad_shop_and_target_fields(self) -> None:
        cfg = self.config
        tables = {
            "ad": pd.DataFrame(
                {
                    cfg.ad_date_column: [20250101],
                    cfg.ad_plan_type_column: ["京东定向"],
                    cfg.ad_sku_id_column: [1001],
                    cfg.ad_product_name_column: ["A"],
                    cfg.ad_cost_column: [100],
                    cfg.ad_gmv_column: [400],
                    cfg.ad_click_column: [50],
                }
            ),
            "shop": pd.DataFrame(
                {
                    cfg.shop_date_column: [pd.Timestamp("2025-01-01")],
                    cfg.shop_sku_id_column: [1001],
                    cfg.shop_pv_column: [1000],
                    cfg.shop_visitor_column: [200],
                    cfg.shop_buyer_column: [20],
                    cfg.shop_order_count_column: [25],
                    cfg.shop_item_count_column: [30],
                    cfg.shop_gmv_column: [500],
                    cfg.shop_brand_column: ["惠氏"],
                }
            ),
            "sku": pd.DataFrame(
                {
                    cfg.sku_id_column: [1001],
                    cfg.category_column: ["店铺"],
                    cfg.brand_column: ["惠氏"],
                }
            ),
            "plan": pd.DataFrame(
                {
                    cfg.plan_type_column: ["京东定向"],
                    cfg.plan_aggregate_column: ["头条渠道"],
                    cfg.new_channel_column: ["站外广告"],
                    cfg.channel_type_column: ["RTB"],
                }
            ),
            "target": pd.DataFrame(
                {
                    cfg.target_date_column: [pd.Timestamp("2025-01-01")],
                    cfg.target_gmv_column: [800],
                    cfg.target_sku_id_column: [1001],
                }
            ),
        }

        result = build_ad_summary_dataset(tables, cfg)

        row = result.iloc[0]
        self.assertEqual(row[cfg.quarter_label_column], "Q1")
        self.assertEqual(row[cfg.month_label_column], "M1")
        self.assertEqual(row[cfg.week_label_column], "W1")
        self.assertEqual(row[cfg.day_label_column], "2025/1/1")
        self.assertEqual(row[cfg.channel_type_column], "RTB")
        self.assertEqual(row[cfg.plan_aggregate_column], "头条渠道")
        self.assertEqual(row[cfg.brand_column], "惠氏")
        self.assertEqual(row[cfg.category_column], "店铺")
        self.assertEqual(row[cfg.shop_target_column], 800)
        self.assertEqual(row[cfg.shop_gmv_column], 500)

    def test_build_period_summary_returns_expected_columns_and_values(self) -> None:
        cfg = self.config
        daily_df = pd.DataFrame(
            {
                cfg.year_column: [2024, 2025, 2025],
                cfg.quarter_label_column: ["Q1", "Q1", "Q1"],
                cfg.quarter_sort_column: [1, 1, 1],
                cfg.month_label_column: ["M1", "M1", "M1"],
                cfg.month_sort_column: [1, 1, 1],
                cfg.week_label_column: ["W1", "W1", "W2"],
                cfg.week_sort_column: [1, 1, 2],
                cfg.day_label_column: ["2024/1/1", "2025/1/1", "2025/1/2"],
                cfg.date_column: pd.to_datetime(["2024-01-01", "2025-01-01", "2025-01-02"]),
                cfg.channel_type_column: ["RTB", "RTB", "RTB"],
                cfg.new_channel_column: ["站外广告", "站外广告", "站外广告"],
                cfg.brand_column: ["惠氏", "惠氏", "惠氏"],
                cfg.category_column: ["店铺", "店铺", "店铺"],
                cfg.product_name_column: ["A", "A", "A"],
                cfg.plan_aggregate_column: ["头条渠道", "头条渠道", "头条渠道"],
                cfg.ad_cost_column: [40, 100, 120],
                cfg.ad_gmv_column: [80, 400, 240],
                cfg.shop_gmv_column: [100, 500, 300],
                cfg.ad_click_column: [10, 50, 30],
                cfg.shop_pv_column: [100, 1000, 600],
                cfg.shop_visitor_column: [50, 200, 100],
                cfg.shop_buyer_column: [5, 20, 10],
                cfg.shop_order_count_column: [6, 25, 12],
                cfg.shop_item_count_column: [8, 30, 15],
                cfg.shop_target_column: [120, 800, 200],
            }
        )

        result = build_period_summary(daily_df, "month", cfg)

        self.assertEqual(result.columns.tolist(), cfg.display_columns)

        month_2025 = result[result[cfg.period_label_column] == "M1"].iloc[0]
        self.assertEqual(month_2025["广告费用"], 220)
        self.assertEqual(month_2025["投放GMV"], 640)
        self.assertEqual(month_2025["店铺GMV"], 800)
        self.assertAlmostEqual(month_2025["广告GMV贡献"], 0.8, places=4)
        self.assertAlmostEqual(month_2025["广告ROI"], 640 / 220, places=4)
        self.assertAlmostEqual(month_2025["费比"], 220 / 800, places=4)
        self.assertAlmostEqual(month_2025["店铺完成进度"], 0.8, places=4)
        self.assertAlmostEqual(month_2025["PV贡献"], 80 / 1600, places=4)
        self.assertAlmostEqual(month_2025["人均访问数"], 1600 / 300, places=4)
        self.assertAlmostEqual(month_2025["转化率"], 30 / 300, places=4)
        self.assertAlmostEqual(month_2025["人均子订单量"], 37 / 30, places=4)
        self.assertAlmostEqual(month_2025["均单商品数"], 45 / 37, places=4)
        self.assertAlmostEqual(month_2025["商品单价"], 800 / 45, places=4)
        self.assertEqual(month_2025[cfg.shop_gmv_tail_column], 800)
        self.assertAlmostEqual(month_2025["消耗环比"], (220 / 40) - 1, places=4)
        self.assertAlmostEqual(month_2025["投放GMV环比"], (640 / 80) - 1, places=4)
        self.assertAlmostEqual(month_2025["店铺GMV环比"], (800 / 100) - 1, places=4)
        self.assertAlmostEqual(
            month_2025[cfg.shop_gmv_ratio_tail_column],
            (800 / 100) - 1,
            places=4,
        )
        self.assertAlmostEqual(month_2025["广告点击季度同比"], (80 / 10) - 1, places=4)

    def test_build_period_summary_day_progress_uses_daily_target(self) -> None:
        cfg = self.config
        daily_df = pd.DataFrame(
            {
                cfg.year_column: [2025, 2025],
                cfg.quarter_label_column: ["Q1", "Q1"],
                cfg.quarter_sort_column: [1, 1],
                cfg.month_label_column: ["M1", "M1"],
                cfg.month_sort_column: [1, 1],
                cfg.week_label_column: ["W1", "W1"],
                cfg.week_sort_column: [1, 1],
                cfg.day_label_column: ["2025/1/1", "2025/1/2"],
                cfg.date_column: pd.to_datetime(["2025-01-01", "2025-01-02"]),
                cfg.channel_type_column: ["RTB", "RTB"],
                cfg.new_channel_column: ["站外广告", "站外广告"],
                cfg.brand_column: ["惠氏", "惠氏"],
                cfg.category_column: ["店铺", "店铺"],
                cfg.product_name_column: ["A", "A"],
                cfg.plan_aggregate_column: ["头条渠道", "头条渠道"],
                cfg.ad_cost_column: [100, 120],
                cfg.ad_gmv_column: [400, 240],
                cfg.shop_gmv_column: [500, 300],
                cfg.ad_click_column: [50, 30],
                cfg.shop_pv_column: [1000, 600],
                cfg.shop_visitor_column: [200, 100],
                cfg.shop_buyer_column: [20, 10],
                cfg.shop_order_count_column: [25, 12],
                cfg.shop_item_count_column: [30, 15],
                cfg.shop_target_column: [800, 200],
            }
        )

        result = build_period_summary(daily_df, "day", cfg)
        day_2 = result[result[cfg.period_label_column] == "2025/1/2"].iloc[0]

        self.assertEqual(day_2["店铺GMV目标"], 200)
        self.assertAlmostEqual(day_2["店铺完成进度"], 1.5, places=4)

    def test_build_change_ratio_returns_zero_for_none_na_zero_and_blank(self) -> None:
        series = pd.Series([100.0, None, pd.NA, "", 0, 200.0])

        result = _build_change_ratio(series)

        self.assertEqual(result.tolist(), [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    def test_build_period_summary_handles_missing_roi_source_without_error(self) -> None:
        cfg = self.config
        daily_df = pd.DataFrame(
            {
                cfg.year_column: [2025, 2025, 2025],
                cfg.quarter_label_column: ["Q1", "Q1", "Q1"],
                cfg.quarter_sort_column: [1, 1, 1],
                cfg.month_label_column: ["M1", "M1", "M1"],
                cfg.month_sort_column: [1, 1, 1],
                cfg.week_label_column: ["W1", "W1", "W1"],
                cfg.week_sort_column: [1, 1, 1],
                cfg.day_label_column: ["2025/1/1", "2025/1/2", "2025/1/3"],
                cfg.date_column: pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
                cfg.channel_type_column: ["RTB", "RTB", "RTB"],
                cfg.new_channel_column: ["站外广告", "站外广告", "站外广告"],
                cfg.brand_column: ["惠氏", "惠氏", "惠氏"],
                cfg.category_column: ["店铺", "店铺", "店铺"],
                cfg.product_name_column: ["A", "A", "A"],
                cfg.plan_aggregate_column: ["头条渠道", "头条渠道", "头条渠道"],
                cfg.ad_cost_column: [100, None, 50],
                cfg.ad_gmv_column: [400, 200, 0],
                cfg.shop_gmv_column: [500, 300, 100],
                cfg.ad_click_column: [50, 30, 10],
                cfg.shop_pv_column: [1000, 600, 200],
                cfg.shop_visitor_column: [200, 100, 50],
                cfg.shop_buyer_column: [20, 10, 5],
                cfg.shop_order_count_column: [25, 12, 6],
                cfg.shop_item_count_column: [30, 15, 8],
                cfg.shop_target_column: [800, 200, 100],
            }
        )

        result = build_period_summary(daily_df, "day", cfg)
        day_2 = result[result[cfg.period_label_column] == "2025/1/2"].iloc[0]

        self.assertEqual(day_2["广告ROI"], 0.0)
        self.assertTrue(pd.notna(day_2["ROI环比"]))

    def test_build_yoy_ratio_returns_zero_when_previous_year_missing(self) -> None:
        cfg = self.config
        grouped_df = pd.DataFrame(
            {
                cfg.year_column: [2025],
                cfg.month_label_column: ["M1"],
                cfg.month_sort_column: [1],
                cfg.ad_click_column: [50],
            }
        )

        result = _build_yoy_ratio(
            grouped_df,
            value_column=cfg.ad_click_column,
            period_column=cfg.month_label_column,
            sort_column=cfg.month_sort_column,
            config=cfg,
        )

        self.assertEqual(result.tolist(), [0.0])


if __name__ == "__main__":
    unittest.main()
