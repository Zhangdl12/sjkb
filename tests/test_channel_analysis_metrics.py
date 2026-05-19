import importlib.util
import unittest
from pathlib import Path

import pandas as pd

from app.dashboards.channel_analysis.config import AppConfig
from app.dashboards.channel_analysis.metrics import (
    build_category_summary,
    build_channel_summary,
    build_channel_total,
    build_time_channel_summary,
)
from app.dashboards.channel_analysis.processor import build_channel_analysis_dataset
from app.dashboards.channel_analysis.service import (
    add_category_tree_path,
    build_channel_analysis_payload,
    build_filter_summary,
)
from app.dashboards.channel_analysis.ui import _build_column_def, _build_plain_grid_options, _build_tree_grid_options


PAGE_MODULE_PATH = Path(__file__).resolve().parents[1] / "pages" / "03_渠道分析.py"
SPEC = importlib.util.spec_from_file_location("channel_analysis_page", PAGE_MODULE_PATH)
channel_analysis_page = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(channel_analysis_page)


class TestChannelAnalysisMetrics(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AppConfig()

    def test_build_dataset_normalizes_all_sources_and_tags(self) -> None:
        cfg = self.config
        result = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)

        station_row = result[result[cfg.new_channel_column] == "搜索快车"].iloc[0]
        cps_row = result[result[cfg.new_channel_column] == "京挑客"].iloc[0]
        brand_row = result[result[cfg.new_channel_column] == "搜索品专"].iloc[0]
        sitewide_row = result[result[cfg.new_channel_column] == "全站营销"].iloc[0]

        self.assertEqual(len(result), 5)
        self.assertEqual(station_row[cfg.line_column], "全护3大")
        self.assertEqual(station_row[cfg.sku_product_name_column], "全护3段")
        self.assertEqual(station_row[cfg.brand_column], "雀巢")
        self.assertEqual(station_row[cfg.channel_type_column], "RTB")
        self.assertEqual(cps_row[cfg.channel_type_column], "CPS")
        self.assertEqual(cps_row[cfg.line_column], "启护箱装")
        self.assertEqual(brand_row[cfg.channel_type_column], "品专")
        self.assertEqual(sitewide_row[cfg.channel_type_column], "全站")
        self.assertEqual(station_row[cfg.year_column], 2025)
        self.assertEqual(station_row[cfg.month_label_column], "M1")
        self.assertEqual(station_row[cfg.day_label_column], "2025/1/1")

    def test_channel_summary_recalculates_metrics_after_sum(self) -> None:
        cfg = self.config
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)

        result = build_channel_summary(dataset, cfg)
        row = result[result[cfg.new_channel_column] == "搜索快车"].iloc[0]

        self.assertEqual(row["广告费用"], 150)
        self.assertEqual(row["广告展现"] if "广告展现" in row else 1500, 1500)
        self.assertAlmostEqual(row["花费占比%"], 150 / 580, places=4)
        self.assertEqual(row["广告订单行"], 15)
        self.assertEqual(row["广告GMV"], 550)
        self.assertAlmostEqual(row["广告GMV占比"], 550 / 1680, places=4)
        self.assertAlmostEqual(row["广告ROI"], 550 / 150, places=4)
        self.assertAlmostEqual(row["广告CPC"], 150 / 75, places=4)
        self.assertAlmostEqual(row["广告CVR"], 15 / 75, places=4)
        self.assertAlmostEqual(row["广告CTR"], 75 / 1500, places=4)
        self.assertEqual(row["广告新客"], 8)
        self.assertAlmostEqual(row["广告新客成本"], 150 / 8, places=4)
        self.assertAlmostEqual(row["ROI月环比"], -0.25, places=4)

    def test_category_summary_uses_line_product_and_channel(self) -> None:
        cfg = self.config
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)

        result = build_category_summary(dataset, cfg)
        row = result[
            (result[cfg.month_label_column] == "M1")
            & (result[cfg.line_column] == "全护3大")
            & (result[cfg.sku_product_name_column] == "全护3段")
            & (result[cfg.new_channel_column] == "搜索快车")
        ].iloc[0]

        self.assertEqual(row["广告费用"], 100)
        self.assertEqual(row["广告订单行"], 10)
        self.assertEqual(row["广告GMV"], 400)
        self.assertAlmostEqual(row["广告ROI"], 4.0, places=4)
        self.assertAlmostEqual(row["ROI月环比"], 0.0, places=4)

    def test_time_channel_summary_calculates_extended_metrics(self) -> None:
        cfg = self.config
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)

        result = build_time_channel_summary(dataset, cfg)
        row = result[
            (result[cfg.month_label_column] == "M1")
            & (result[cfg.day_label_column] == "2025/1/1")
            & (result[cfg.new_channel_column] == "搜索快车")
        ].iloc[0]

        self.assertEqual(result.columns.tolist(), cfg.time_columns)
        self.assertEqual(len(result[(result[cfg.day_label_column] == "2025/1/1") & (result[cfg.new_channel_column] == "搜索快车")]), 1)
        self.assertEqual(row["广告展现"], 1000)
        self.assertEqual(row["广告点击"], 50)
        self.assertEqual(row["广告费用"], 100)
        self.assertEqual(row["广告订单行"], 10)
        self.assertEqual(row["广告GMV"], 400)
        self.assertEqual(row["广告新客"], 5)
        self.assertEqual(row["广告加购数"], 20)
        self.assertAlmostEqual(row["广告商品单价"], 40.0, places=4)
        self.assertAlmostEqual(row["广告CPC"], 2.0, places=4)
        self.assertAlmostEqual(row["广告CTR"], 50 / 1000, places=4)
        self.assertAlmostEqual(row["广告CVR"], 10 / 50, places=4)
        self.assertAlmostEqual(row["广告ROI"], 4.0, places=4)
        self.assertAlmostEqual(row["广告加购率"], 20 / 50, places=4)
        self.assertAlmostEqual(row["广告CPA"], 10.0, places=4)
        self.assertAlmostEqual(row["广告新客成本"], 20.0, places=4)
        self.assertAlmostEqual(row["广告新客浓度"], 5 / 10, places=4)
        self.assertAlmostEqual(row["广告总加购成本"], 5.0, places=4)

    def test_total_and_zero_denominator_are_stable(self) -> None:
        cfg = self.config
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)

        total = build_channel_total(dataset, cfg).iloc[0]
        zero = build_channel_summary(
            pd.DataFrame(
                {
                    cfg.new_channel_column: ["零值"],
                    cfg.month_label_column: ["M1"],
                    cfg.month_sort_column: [1],
                    cfg.ad_cost_column: [0],
                    cfg.ad_impression_column: [0],
                    cfg.ad_click_column: [0],
                    cfg.ad_order_row_column: [0],
                    cfg.ad_gmv_column: [0],
                    cfg.ad_new_customer_column: [0],
                    cfg.ad_cart_column: [0],
                }
            ),
            cfg,
        ).iloc[0]

        self.assertEqual(total[cfg.new_channel_column], "总计")
        self.assertEqual(total["广告费用"], 580)
        self.assertEqual(total["花费占比%"], 1.0)
        self.assertEqual(total["广告GMV占比"], 1.0)
        self.assertTrue(pd.isna(total["ROI月环比"]))
        self.assertEqual(zero["广告ROI"], 0.0)
        self.assertEqual(zero["广告CPC"], 0.0)
        self.assertEqual(zero["广告CVR"], 0.0)
        self.assertEqual(zero["广告CTR"], 0.0)
        self.assertEqual(zero["广告新客成本"], 0.0)

    def test_page_helpers_and_grid_options(self) -> None:
        cfg = self.config
        fields = channel_analysis_page.build_filter_fields(cfg)
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)
        payload = channel_analysis_page.build_display_tables(dataset, cfg)
        plain_options = _build_plain_grid_options(payload.channel_df, cfg)
        tree_options = _build_tree_grid_options(
            payload.category_df,
            hidden_columns={
                "path",
                cfg.line_column,
                cfg.sku_product_name_column,
                cfg.new_channel_column,
                cfg.month_label_column,
            },
            group_header="品线分类 > 商品名称 > 新产品渠道 > 月",
        )

        self.assertEqual(fields[0].column, cfg.year_column)
        self.assertEqual(fields[0].control, "single_select")
        self.assertFalse(payload.channel_df.empty)
        self.assertFalse(payload.category_df.empty)
        self.assertTrue(payload.time_df.empty)
        self.assertIn(cfg.new_channel_column, [column["field"] for column in plain_options["columnDefs"]])
        self.assertTrue(tree_options["treeData"])
        self.assertEqual(tree_options["groupDefaultExpanded"], 0)
        self.assertIn("path", [column["field"] for column in tree_options["columnDefs"]])

    def test_category_tree_path_uses_line_product_channel_month(self) -> None:
        cfg = self.config
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)
        category_df = add_category_tree_path(build_category_summary(dataset, cfg), cfg)

        self.assertIn("path", category_df.columns)
        self.assertIn("全护3大||全护3段||搜索快车||M1", category_df["path"].tolist())

    def test_payload_only_builds_classification_view_tables(self) -> None:
        cfg = self.config
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)
        payload = build_channel_analysis_payload(
            {"dataset": dataset},
            {},
            channel_analysis_page.build_filter_fields(cfg),
            "分类汇总",
            cfg,
        )

        self.assertFalse(payload.channel_df.empty)
        self.assertFalse(payload.category_df.empty)
        self.assertFalse(payload.total_df.empty)
        self.assertTrue(payload.time_df.empty)
        self.assertIn(cfg.month_label_column, payload.category_df.columns)
        self.assertIn("path", payload.category_df.columns)

    def test_category_tree_parent_rows_have_summary_metrics(self) -> None:
        cfg = self.config
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)
        payload = build_channel_analysis_payload(
            {"dataset": dataset},
            {},
            channel_analysis_page.build_filter_fields(cfg),
            "分类汇总",
            cfg,
        )
        line_row = payload.category_df[payload.category_df["path"] == "全护3大"].iloc[0]
        product_row = payload.category_df[payload.category_df["path"] == "全护3大||全护3段"].iloc[0]
        channel_row = payload.category_df[payload.category_df["path"] == "全护3大||全护3段||搜索快车"].iloc[0]
        month_row = payload.category_df[payload.category_df["path"] == "全护3大||全护3段||搜索快车||M1"].iloc[0]

        self.assertEqual(line_row["广告费用"], 150)
        self.assertEqual(product_row["广告费用"], 150)
        self.assertEqual(channel_row["广告费用"], 150)
        self.assertEqual(month_row["广告费用"], 100)
        self.assertAlmostEqual(channel_row["广告ROI"], 550 / 150, places=4)
        self.assertTrue(pd.isna(line_row["ROI月环比"]))
        self.assertTrue(pd.isna(product_row["ROI月环比"]))
        self.assertTrue(pd.isna(channel_row["ROI月环比"]))
        self.assertAlmostEqual(month_row["ROI月环比"], 0.0, places=4)

    def test_category_tree_contains_channel_then_month_paths(self) -> None:
        cfg = self.config
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)
        payload = build_channel_analysis_payload(
            {"dataset": dataset},
            {},
            channel_analysis_page.build_filter_fields(cfg),
            "分类汇总",
            cfg,
        )

        self.assertIn("全护3大", payload.category_df["path"].tolist())
        self.assertIn("全护3大||全护3段", payload.category_df["path"].tolist())
        self.assertIn("全护3大||全护3段||搜索快车", payload.category_df["path"].tolist())
        self.assertIn("全护3大||全护3段||搜索快车||M1", payload.category_df["path"].tolist())
        self.assertIn("全护3大||全护3段||搜索快车||M2", payload.category_df["path"].tolist())

    def test_category_tree_month_rows_keep_roi_month_change(self) -> None:
        cfg = self.config
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)
        payload = build_channel_analysis_payload(
            {"dataset": dataset},
            {},
            channel_analysis_page.build_filter_fields(cfg),
            "分类汇总",
            cfg,
        )
        first_month_row = payload.category_df[
            payload.category_df["path"] == "全护3大||全护3段||搜索快车||M1"
        ].iloc[0]
        second_month_row = payload.category_df[
            payload.category_df["path"] == "全护3大||全护3段||搜索快车||M2"
        ].iloc[0]

        self.assertAlmostEqual(first_month_row["ROI月环比"], 0.0, places=4)
        self.assertAlmostEqual(second_month_row["ROI月环比"], -0.25, places=4)

    def test_payload_only_builds_time_view_table(self) -> None:
        cfg = self.config
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)
        payload = build_channel_analysis_payload(
            {"dataset": dataset},
            {},
            channel_analysis_page.build_filter_fields(cfg),
            "时间渠道",
            cfg,
        )

        self.assertTrue(payload.channel_df.empty)
        self.assertTrue(payload.category_df.empty)
        self.assertTrue(payload.total_df.empty)
        self.assertFalse(payload.time_df.empty)
        self.assertIn("path", payload.time_df.columns)
        self.assertEqual(
            payload.time_df.columns.tolist(),
            [*cfg.time_columns, "path"],
        )

    def test_time_tree_contains_month_day_channel_paths(self) -> None:
        cfg = self.config
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)
        payload = build_channel_analysis_payload(
            {"dataset": dataset},
            {},
            channel_analysis_page.build_filter_fields(cfg),
            "时间渠道",
            cfg,
        )

        self.assertIn("M1", payload.time_df["path"].tolist())
        self.assertIn("M1||2025/1/1", payload.time_df["path"].tolist())
        self.assertIn("M1||2025/1/1||搜索快车", payload.time_df["path"].tolist())

    def test_time_tree_parent_rows_have_summary_metrics(self) -> None:
        cfg = self.config
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)
        payload = build_channel_analysis_payload(
            {"dataset": dataset},
            {},
            channel_analysis_page.build_filter_fields(cfg),
            "时间渠道",
            cfg,
        )
        month_row = payload.time_df[payload.time_df["path"] == "M1"].iloc[0]
        day_row = payload.time_df[payload.time_df["path"] == "M1||2025/1/1"].iloc[0]
        leaf_row = payload.time_df[payload.time_df["path"] == "M1||2025/1/1||搜索快车"].iloc[0]

        self.assertGreater(month_row["广告费用"], 0)
        self.assertGreater(day_row["广告费用"], 0)
        self.assertEqual(leaf_row["广告费用"], 100)

    def test_filter_summary_is_stable_for_cache_key(self) -> None:
        summary = build_filter_summary({"渠道类型": ["RTB"], "年": 2025})

        self.assertEqual(summary, (("年", (2025,)), ("渠道类型", ("RTB",))))

    def test_roi_month_change_grid_column_has_style(self) -> None:
        cfg = self.config
        dataset = build_channel_analysis_dataset(_build_source_tables(cfg), cfg)
        payload = build_channel_analysis_payload(
            {"dataset": dataset},
            {},
            channel_analysis_page.build_filter_fields(cfg),
            "分类汇总",
            cfg,
        )
        grid_options = _build_plain_grid_options(payload.channel_df, cfg)
        roi_column = [
            column for column in grid_options["columnDefs"]
            if column["field"] == "ROI月环比"
        ][0]

        self.assertIn("cellStyle", roi_column)
        self.assertIn("tooltipValueGetter", roi_column)

    def test_numeric_columns_have_precise_tooltips(self) -> None:
        """验证渠道分析数值列支持悬停查看更完整精度。"""
        percent_column = _build_column_def("广告CTR")
        cost_column = _build_column_def("广告费用")

        self.assertIn("valueFormatter", percent_column)
        self.assertIn("tooltipValueGetter", percent_column)
        self.assertIn("valueFormatter", cost_column)
        self.assertIn("tooltipValueGetter", cost_column)


def _build_source_tables(cfg: AppConfig) -> dict[str, pd.DataFrame]:
    return {
        "station": pd.DataFrame(
            {
                cfg.station_date_column: [20250101, 20250201],
                cfg.station_scene_column: ["商品推广", "商品推广"],
                cfg.station_sku_column: [1001, 1001],
                cfg.station_sku_name_column: ["原商品A", "原商品A"],
                cfg.station_cost_column: [100, 50],
                cfg.station_impression_column: [1000, 500],
                cfg.station_click_column: [50, 25],
                cfg.station_order_row_column: [10, 5],
                cfg.station_gmv_column: [400, 150],
                cfg.station_cart_column: [20, 10],
                cfg.station_new_customer_column: [5, 3],
            }
        ),
        "cps": pd.DataFrame(
            {
                cfg.cps_sku_column: [1002],
                cfg.cps_date_column: [20250101],
                cfg.cps_gmv_column: [300],
                cfg.cps_cost_column: [30],
                cfg.cps_order_row_column: [6],
            }
        ),
        "brand": pd.DataFrame(
            {
                cfg.brand_date_column: [20250101],
                cfg.brand_cost_column: [200],
                cfg.brand_impression_column: [2000],
                cfg.brand_click_column: [100],
                cfg.brand_order_row_column: [20],
                cfg.brand_gmv_column: [500],
                cfg.brand_cart_column: [30],
            }
        ),
        "sitewide": pd.DataFrame(
            {
                cfg.sitewide_date_column: [20250101],
                cfg.sitewide_cost_column: [200],
                cfg.sitewide_gmv_column: [330],
                cfg.sitewide_order_row_column: [11],
                cfg.sitewide_impression_column: [3000],
                cfg.sitewide_click_column: [150],
                cfg.sitewide_new_customer_column: [4],
            }
        ),
        "channel_tag": pd.DataFrame(
            {
                cfg.channel_scene_column: ["商品推广", "京挑客", "搜索品专", "全站营销"],
                cfg.plan_aggregate_column: ["其他", "其他", "其他", "其他"],
                cfg.new_channel_column: ["搜索快车", "京挑客", "搜索品专", "全站营销"],
                cfg.channel_type_column: ["RTB", "CPS", "品专", "全站"],
            }
        ),
        "sku_tag": pd.DataFrame(
            {
                cfg.sku_id_column: [1001, 1002],
                cfg.sku_product_name_column: ["全护3段", "启护箱装"],
                cfg.brand_column: ["雀巢", "雀巢"],
                cfg.sku_category_column: ["全护3大", "启护箱装"],
            }
        ),
    }


if __name__ == "__main__":
    unittest.main()
