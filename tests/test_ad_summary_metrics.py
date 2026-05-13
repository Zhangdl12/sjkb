import unittest

import pandas as pd

from app.dashboards.ad_summary.config import AppConfig
from app.dashboards.ad_summary.metrics import (
    _build_change_ratio,
    _build_yoy_ratio,
    build_period_summary,
    build_summary_and_total,
    build_total_row_for_scope,
    filter_detail_by_summary_scope,
)
from app.dashboards.ad_summary.processor import build_ad_summary_dataset
from app.dashboards.ad_summary.ui import _build_styler


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
                    cfg.product_name_column: ["SKU表商品名"],
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
        self.assertEqual(row[cfg.product_name_column], "SKU表商品名")
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

    def test_filter_detail_by_summary_scope_uses_summary_period_values(self) -> None:
        cfg = self.config
        detail_df = pd.DataFrame(
            {
                cfg.quarter_label_column: ["Q1", "Q2", "Q3"],
                cfg.month_label_column: ["M1", "M2", "M3"],
                cfg.week_label_column: ["W1", "W2", "W3"],
                cfg.day_label_column: ["2025/1/1", "2025/1/2", "2025/1/3"],
            }
        )
        summary_df = pd.DataFrame({cfg.period_label_column: ["Q1", "Q2"]})

        scoped_df = filter_detail_by_summary_scope(detail_df, summary_df, "quarter", cfg)

        self.assertEqual(scoped_df[cfg.quarter_label_column].tolist(), ["Q1", "Q2"])

    def test_build_total_row_for_scope_recalculates_metrics_from_scoped_detail(self) -> None:
        cfg = self.config
        scoped_detail_df = pd.DataFrame(
            {
                cfg.ad_cost_column: [100, 200],
                cfg.ad_gmv_column: [400, 200],
                cfg.shop_gmv_column: [500, 300],
                cfg.shop_target_column: [800, 200],
                cfg.ad_click_column: [50, 30],
                cfg.shop_pv_column: [1000, 600],
                cfg.shop_visitor_column: [200, 100],
                cfg.shop_buyer_column: [20, 10],
                cfg.shop_order_count_column: [25, 12],
                cfg.shop_item_count_column: [30, 15],
            }
        )

        total_row_df = build_total_row_for_scope(scoped_detail_df, cfg)
        total_row = total_row_df.iloc[0]

        self.assertEqual(total_row[cfg.period_label_column], "总计")
        self.assertEqual(total_row["广告费用"], 300)
        self.assertEqual(total_row["投放GMV"], 600)
        self.assertEqual(total_row["店铺GMV"], 800)
        self.assertAlmostEqual(total_row["广告GMV贡献"], 600 / 800, places=4)
        self.assertAlmostEqual(total_row["广告ROI"], 600 / 300, places=4)
        self.assertAlmostEqual(total_row["费比"], 300 / 800, places=4)
        self.assertAlmostEqual(total_row["店铺完成进度"], 800 / 1000, places=4)
        self.assertEqual(total_row[cfg.shop_gmv_tail_column], 800)
        self.assertTrue(pd.isna(total_row["消耗环比"]))
        self.assertTrue(pd.isna(total_row["广告点击季度同比"]))
        self.assertTrue(pd.isna(total_row[cfg.shop_gmv_ratio_tail_column]))

    def test_build_summary_and_total_uses_month_summary_scope_only(self) -> None:
        cfg = self.config
        detail_df = pd.DataFrame(
            {
                cfg.year_column: [2025, 2025, 2025],
                cfg.quarter_label_column: ["Q1", "Q1", "Q1"],
                cfg.quarter_sort_column: [1, 1, 1],
                cfg.month_label_column: ["M1", "M2", "M3"],
                cfg.month_sort_column: [1, 2, 3],
                cfg.week_label_column: ["W1", "W2", "W3"],
                cfg.week_sort_column: [1, 2, 3],
                cfg.day_label_column: ["2025/1/1", "2025/2/1", "2025/3/1"],
                cfg.date_column: pd.to_datetime(["2025-01-01", "2025-02-01", "2025-03-01"]),
                cfg.ad_cost_column: [100, 200, 300],
                cfg.ad_gmv_column: [400, 500, 600],
                cfg.shop_gmv_column: [500, 700, 900],
                cfg.shop_target_column: [800, 900, 1000],
                cfg.ad_click_column: [50, 60, 70],
                cfg.shop_pv_column: [1000, 1100, 1200],
                cfg.shop_visitor_column: [200, 210, 220],
                cfg.shop_buyer_column: [20, 21, 22],
                cfg.shop_order_count_column: [25, 26, 27],
                cfg.shop_item_count_column: [30, 31, 32],
            }
        )
        detail_summary_df, total_row_df = build_summary_and_total(detail_df, "month", cfg)
        total_row = total_row_df.iloc[0]

        self.assertNotIn("总计", detail_summary_df[cfg.period_label_column].tolist())
        self.assertEqual(len(total_row_df), 1)
        self.assertEqual(total_row[cfg.period_label_column], "总计")
        self.assertEqual(total_row["广告费用"], 600)
        self.assertEqual(total_row["投放GMV"], 1500)
        self.assertEqual(total_row["店铺GMV"], 2100)
        self.assertEqual(total_row["店铺GMV目标"], 2700)

    def test_build_period_summary_uses_separate_shop_scope_for_store_side_metrics(self) -> None:
        cfg = self.config
        full_df = pd.DataFrame(
            {
                cfg.year_column: [2025, 2025],
                cfg.quarter_label_column: ["Q1", "Q1"],
                cfg.quarter_sort_column: [1, 1],
                cfg.month_label_column: ["M1", "M1"],
                cfg.month_sort_column: [1, 1],
                cfg.week_label_column: ["W1", "W1"],
                cfg.week_sort_column: [1, 1],
                cfg.day_label_column: ["2025/1/1", "2025/1/1"],
                cfg.date_column: pd.to_datetime(["2025-01-01", "2025-01-01"]),
                cfg.ad_sku_id_column: [1001, 1001],
                cfg.channel_type_column: ["RTB", "CPS"],
                cfg.new_channel_column: ["站外广告", "头条广告"],
                cfg.plan_aggregate_column: ["计划A", "计划B"],
                cfg.brand_column: ["惠氏", "惠氏"],
                cfg.category_column: ["店铺", "店铺"],
                cfg.product_name_column: ["A", "A"],
                cfg.ad_cost_column: [100, 200],
                cfg.ad_gmv_column: [300, 400],
                cfg.shop_gmv_column: [1000, 1000],
                cfg.ad_click_column: [10, 20],
                cfg.shop_pv_column: [2000, 2000],
                cfg.shop_visitor_column: [500, 500],
                cfg.shop_buyer_column: [50, 50],
                cfg.shop_order_count_column: [60, 60],
                cfg.shop_item_count_column: [70, 70],
                cfg.shop_target_column: [800, 800],
            }
        )
        filtered_detail_df = full_df[full_df[cfg.channel_type_column] == "RTB"].copy()

        result = build_period_summary(filtered_detail_df, "month", cfg, shop_metric_df=full_df)
        row = result.iloc[0]

        self.assertEqual(row["广告费用"], 100)
        self.assertEqual(row["投放GMV"], 300)
        self.assertEqual(row["广告点击"], 10)
        self.assertEqual(row["店铺GMV"], 1000)
        self.assertEqual(row["店铺GMV目标"], 800)
        self.assertEqual(row["PV"], 2000)
        self.assertAlmostEqual(row["广告GMV贡献"], 0.3, places=4)
        self.assertAlmostEqual(row["费比"], 0.1, places=4)
        self.assertAlmostEqual(row["店铺完成进度"], 1.25, places=4)

    def test_build_period_summary_store_side_metrics_ignore_plan_aggregate(self) -> None:
        cfg = self.config
        full_df = pd.DataFrame(
            {
                cfg.year_column: [2025, 2025],
                cfg.quarter_label_column: ["Q1", "Q1"],
                cfg.quarter_sort_column: [1, 1],
                cfg.month_label_column: ["M1", "M1"],
                cfg.month_sort_column: [1, 1],
                cfg.week_label_column: ["W1", "W1"],
                cfg.week_sort_column: [1, 1],
                cfg.day_label_column: ["2025/1/1", "2025/1/1"],
                cfg.date_column: pd.to_datetime(["2025-01-01", "2025-01-01"]),
                cfg.ad_sku_id_column: [1001, 1001],
                cfg.channel_type_column: ["RTB", "RTB"],
                cfg.new_channel_column: ["站外广告", "站外广告"],
                cfg.plan_aggregate_column: ["计划A", "计划B"],
                cfg.brand_column: ["惠氏", "惠氏"],
                cfg.category_column: ["店铺", "店铺"],
                cfg.product_name_column: ["A", "A"],
                cfg.ad_cost_column: [100, 200],
                cfg.ad_gmv_column: [300, 400],
                cfg.shop_gmv_column: [1000, 1000],
                cfg.ad_click_column: [10, 20],
                cfg.shop_pv_column: [2000, 2000],
                cfg.shop_visitor_column: [500, 500],
                cfg.shop_buyer_column: [50, 50],
                cfg.shop_order_count_column: [60, 60],
                cfg.shop_item_count_column: [70, 70],
                cfg.shop_target_column: [800, 800],
            }
        )
        filtered_detail_df = full_df[full_df[cfg.plan_aggregate_column] == "计划A"].copy()

        result = build_period_summary(filtered_detail_df, "month", cfg, shop_metric_df=full_df)
        row = result.iloc[0]

        self.assertEqual(row["广告费用"], 100)
        self.assertEqual(row["投放GMV"], 300)
        self.assertEqual(row["广告点击"], 10)
        self.assertEqual(row["店铺GMV"], 1000)
        self.assertEqual(row["店铺GMV目标"], 800)
        self.assertEqual(row["PV"], 2000)

    def test_build_period_summary_uses_two_year_scope_for_click_yoy(self) -> None:
        cfg = self.config
        current_year_df = pd.DataFrame(
            {
                cfg.year_column: [2025],
                cfg.quarter_label_column: ["Q1"],
                cfg.quarter_sort_column: [1],
                cfg.month_label_column: ["M1"],
                cfg.month_sort_column: [1],
                cfg.week_label_column: ["W1"],
                cfg.week_sort_column: [1],
                cfg.day_label_column: ["2025/1/1"],
                cfg.date_column: pd.to_datetime(["2025-01-01"]),
                cfg.channel_type_column: ["RTB"],
                cfg.new_channel_column: ["站外广告"],
                cfg.brand_column: ["惠氏"],
                cfg.category_column: ["店铺"],
                cfg.product_name_column: ["A"],
                cfg.plan_aggregate_column: ["头条渠道"],
                cfg.ad_cost_column: [100],
                cfg.ad_gmv_column: [400],
                cfg.shop_gmv_column: [500],
                cfg.ad_click_column: [50],
                cfg.shop_pv_column: [1000],
                cfg.shop_visitor_column: [200],
                cfg.shop_buyer_column: [20],
                cfg.shop_order_count_column: [25],
                cfg.shop_item_count_column: [30],
                cfg.shop_target_column: [800],
            }
        )
        yoy_source_df = pd.DataFrame(
            {
                cfg.year_column: [2024, 2025],
                cfg.quarter_label_column: ["Q1", "Q1"],
                cfg.quarter_sort_column: [1, 1],
                cfg.month_label_column: ["M1", "M1"],
                cfg.month_sort_column: [1, 1],
                cfg.week_label_column: ["W1", "W1"],
                cfg.week_sort_column: [1, 1],
                cfg.day_label_column: ["2024/1/1", "2025/1/1"],
                cfg.date_column: pd.to_datetime(["2024-01-01", "2025-01-01"]),
                cfg.channel_type_column: ["RTB", "RTB"],
                cfg.new_channel_column: ["站外广告", "站外广告"],
                cfg.brand_column: ["惠氏", "惠氏"],
                cfg.category_column: ["店铺", "店铺"],
                cfg.product_name_column: ["A", "A"],
                cfg.plan_aggregate_column: ["头条渠道", "头条渠道"],
                cfg.ad_cost_column: [80, 100],
                cfg.ad_gmv_column: [300, 400],
                cfg.shop_gmv_column: [450, 500],
                cfg.ad_click_column: [10, 50],
                cfg.shop_pv_column: [900, 1000],
                cfg.shop_visitor_column: [180, 200],
                cfg.shop_buyer_column: [18, 20],
                cfg.shop_order_count_column: [23, 25],
                cfg.shop_item_count_column: [28, 30],
                cfg.shop_target_column: [700, 800],
            }
        )

        result = build_period_summary(current_year_df, "month", cfg, yoy_source_df=yoy_source_df)
        row = result.iloc[0]

        self.assertEqual(len(result), 1)
        self.assertEqual(row[cfg.period_label_column], "M1")
        self.assertAlmostEqual(row["广告点击季度同比"], 4.0, places=4)

    def test_build_styler_keeps_positive_and_negative_trend_colors(self) -> None:
        cfg = self.config
        df = pd.DataFrame(
            {
                cfg.period_label_column: ["M1", "M2"],
                "广告费用": [100, 120],
                "投放GMV": [200, 220],
                "店铺GMV": [300, 320],
                "广告GMV贡献": [0.1, 0.2],
                "广告ROI": [1.1, 1.2],
                "费比": [0.1, 0.2],
                "消耗环比": [0.1, -0.2],
                "投放GMV环比": [0.1, -0.2],
                "店铺GMV环比": [0.1, -0.2],
                "ROI环比": [0.1, -0.2],
                "费比环比": [0.1, -0.2],
                "店铺GMV目标": [500, 600],
                "店铺完成进度": [0.6, 0.7],
                "广告点击": [20, 30],
                "广告点击季度同比": [0.1, -0.2],
                "PV贡献": [0.1, 0.2],
                "PV": [500, 600],
                "人均访问数": [1.2, 1.3],
                "转化率": [0.1, 0.2],
                "人均子订单量": [1.1, 1.2],
                "均单商品数": [1.3, 1.4],
                "商品单价": [100, 110],
                cfg.shop_gmv_tail_column: [300, 320],
                cfg.shop_gmv_ratio_tail_column: [0.1, -0.2],
            }
        )

        styler = _build_styler(df, cfg)
        ctx = styler._compute().ctx
        positive_cell_styles = ctx[(0, 7)]
        negative_cell_styles = ctx[(1, 7)]

        self.assertEqual(
            [value for key, value in positive_cell_styles if key == "color"][-1],
            "#008a3d",
        )
        self.assertEqual(
            [value for key, value in negative_cell_styles if key == "color"][-1],
            "#c00000",
        )


if __name__ == "__main__":
    unittest.main()
