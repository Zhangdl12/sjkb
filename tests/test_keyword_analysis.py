import importlib.util
import unittest
from pathlib import Path

import pandas as pd

from app.dashboards.keyword_analysis.config import AppConfig
from app.dashboards.keyword_analysis.metrics import (
    build_classification_summary,
    build_time_summary,
    build_total,
)
from app.dashboards.keyword_analysis.processor import build_keyword_analysis_dataset
from app.dashboards.keyword_analysis.service import build_filter_summary, build_keyword_analysis_payload
from app.dashboards.keyword_analysis.ui import _build_column_def, _build_tree_grid_options


PAGE_MODULE_PATH = Path(__file__).resolve().parents[1] / "pages" / "04_关键词分析.py"
SPEC = importlib.util.spec_from_file_location("keyword_analysis_page", PAGE_MODULE_PATH)
keyword_analysis_page = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(keyword_analysis_page)


class TestKeywordAnalysis(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AppConfig()

    def test_build_dataset_merges_keyword_channel_and_sku_tags(self) -> None:
        cfg = self.config
        result = build_keyword_analysis_dataset(_build_source_tables(cfg), cfg)

        row = result[result[cfg.keyword_column] == "奶粉"].iloc[0]
        blank_row = result[result[cfg.keyword_column] == "未打词"].iloc[0]

        self.assertEqual(len(result), 3)
        self.assertEqual(row[cfg.keyword_category_column], "品类词")
        self.assertEqual(row[cfg.keyword_second_category_column], "品类词-奶粉")
        self.assertEqual(row[cfg.new_channel_column], "常规推广-关键词")
        self.assertEqual(row[cfg.channel_type_column], "站内")
        self.assertEqual(row[cfg.line_column], "启赋")
        self.assertEqual(row[cfg.sku_product_name_column], "启赋蓝钻")
        self.assertEqual(row[cfg.brand_column], "惠氏")
        self.assertEqual(row[cfg.sku_second_category_column], "奶粉")
        self.assertEqual(row[cfg.stage_column], "3段")
        self.assertEqual(blank_row[cfg.keyword_category_column], cfg.blank_text)
        self.assertEqual(blank_row[cfg.year_column], 2025)
        self.assertEqual(blank_row[cfg.month_label_column], "M1")
        self.assertEqual(blank_row[cfg.day_label_column], "2025/1/2")

    def test_optional_columns_can_be_missing(self) -> None:
        cfg = self.config
        tables = _build_source_tables(cfg)
        tables["keyword_tag"] = tables["keyword_tag"].drop(columns=[cfg.keyword_second_category_column])
        tables["sku_tag"] = tables["sku_tag"].drop(columns=[cfg.sku_second_category_column, cfg.stage_column])

        result = build_keyword_analysis_dataset(tables, cfg)

        self.assertIn(cfg.keyword_second_category_column, result.columns)
        self.assertIn(cfg.sku_second_category_column, result.columns)
        self.assertIn(cfg.stage_column, result.columns)
        self.assertEqual(result[cfg.keyword_second_category_column].fillna("").tolist(), ["", "", ""])

    def test_classification_summary_recalculates_ratio_metrics_after_sum(self) -> None:
        cfg = self.config
        dataset = build_keyword_analysis_dataset(_build_source_tables(cfg), cfg)

        result = build_classification_summary(dataset, cfg)
        row = result[result[cfg.keyword_column] == "奶粉"].iloc[0]

        self.assertEqual(row["广告费用"], 150)
        self.assertAlmostEqual(row["花费占比%"], 150 / 180, places=4)
        self.assertAlmostEqual(row["ROI-kw"], 600 / 150, places=4)
        self.assertAlmostEqual(row["CPC-kw"], 150 / 75, places=4)
        self.assertAlmostEqual(row["CTR-kw"], 75 / 1500, places=4)
        self.assertEqual(row["点击数"], 75)
        self.assertEqual(row["总订单金额"], 600)

    def test_time_summary_calculates_extended_metrics_and_zero_denominator(self) -> None:
        cfg = self.config
        dataset = build_keyword_analysis_dataset(_build_source_tables(cfg), cfg)

        result = build_time_summary(dataset, cfg)
        row = result[(result[cfg.keyword_column] == "奶粉") & (result[cfg.day_label_column] == "2025/1/1")].iloc[0]
        zero = result[result[cfg.keyword_column] == "未打词"].iloc[0]

        self.assertEqual(result.columns.tolist(), cfg.time_columns)
        self.assertEqual(row["广告展现"], 1500)
        self.assertEqual(row["广告点击"], 75)
        self.assertEqual(row["广告费用"], 150)
        self.assertEqual(row["广告订单行"], 15)
        self.assertEqual(row["广告GMV"], 600)
        self.assertEqual(row["广告新客"], 8)
        self.assertEqual(row["广告加购数"], 30)
        self.assertAlmostEqual(row["广告商品单价"], 40.0, places=4)
        self.assertAlmostEqual(row["广告CPC"], 2.0, places=4)
        self.assertAlmostEqual(row["广告CTR"], 75 / 1500, places=4)
        self.assertAlmostEqual(row["广告CVR"], 15 / 75, places=4)
        self.assertAlmostEqual(row["广告ROI"], 4.0, places=4)
        self.assertAlmostEqual(row["广告加购率"], 30 / 75, places=4)
        self.assertAlmostEqual(row["广告CPA"], 10.0, places=4)
        self.assertAlmostEqual(row["广告新客成本"], 150 / 8, places=4)
        self.assertAlmostEqual(row["广告总加购成本"], 5.0, places=4)
        self.assertEqual(zero["广告ROI"], 0.0)
        self.assertEqual(zero["广告CPC"], 0.0)
        self.assertEqual(zero["广告CTR"], 0.0)

    def test_total_row_recalculates_from_filtered_scope(self) -> None:
        cfg = self.config
        dataset = build_keyword_analysis_dataset(_build_source_tables(cfg), cfg)

        total = build_total(dataset, cfg).iloc[0]

        self.assertEqual(total[cfg.keyword_category_column], "总计")
        self.assertEqual(total["广告费用"], 180)
        self.assertEqual(total["花费占比%"], 1.0)
        self.assertAlmostEqual(total["ROI-kw"], 600 / 180, places=4)
        self.assertAlmostEqual(total["CPC-kw"], 180 / 75, places=4)

    def test_payload_and_page_helpers_build_expected_views(self) -> None:
        cfg = self.config
        dataset = build_keyword_analysis_dataset(_build_source_tables(cfg), cfg)

        classification_payload = build_keyword_analysis_payload(
            {"dataset": dataset},
            {},
            keyword_analysis_page.build_filter_fields(cfg),
            "词性汇总",
            cfg,
        )
        time_payload = build_keyword_analysis_payload(
            {"dataset": dataset},
            {},
            keyword_analysis_page.build_filter_fields(cfg),
            "时间渠道",
            cfg,
        )

        self.assertFalse(classification_payload.classification_df.empty)
        self.assertFalse(classification_payload.total_df.empty)
        self.assertTrue(classification_payload.time_df.empty)
        self.assertTrue(time_payload.classification_df.empty)
        self.assertTrue(time_payload.total_df.empty)
        self.assertFalse(time_payload.time_df.empty)
        self.assertIn("path", classification_payload.classification_df.columns)
        self.assertIn("path", time_payload.time_df.columns)
        self.assertIn("品类词||品类词-奶粉||奶粉", classification_payload.classification_df["path"].tolist())
        self.assertIn("品类词||品类词-奶粉||奶粉||M1", classification_payload.classification_df["path"].tolist())
        self.assertIn("品类词||奶粉||W1||2025/1/1", time_payload.time_df["path"].tolist())

    def test_filter_summary_and_grid_options_are_stable(self) -> None:
        cfg = self.config
        summary = build_filter_summary({cfg.keyword_column: ["奶粉"], cfg.year_column: 2025})
        grid_options = _build_tree_grid_options(
            pd.DataFrame({"path": ["品类词"], "广告费用": [1]}),
            hidden_columns={"path"},
            group_header="词性分类 > 关键词",
        )

        self.assertEqual(summary, (("关键词", ("奶粉",)), ("年", (2025,))))
        self.assertTrue(grid_options["treeData"])
        self.assertEqual(grid_options["groupDefaultExpanded"], 0)

    def test_numeric_columns_have_precise_tooltips(self) -> None:
        """验证关键词分析数值列支持悬停查看更完整精度。"""
        percent_column = _build_column_def("广告CTR")
        cost_column = _build_column_def("广告费用")

        self.assertIn("valueFormatter", percent_column)
        self.assertIn("tooltipValueGetter", percent_column)
        self.assertIn("valueFormatter", cost_column)
        self.assertIn("tooltipValueGetter", cost_column)


def _build_source_tables(cfg: AppConfig) -> dict[str, pd.DataFrame]:
    return {
        "keyword_fact": pd.DataFrame(
            {
                cfg.fact_date_column: [20250101, 20250101, 20250102],
                cfg.fact_scene_column: ["常规推广-关键词", "常规推广-关键词", "常规推广-关键词"],
                cfg.fact_sku_column: [1001, 1001, 1002],
                cfg.fact_sku_name_column: ["原商品A", "原商品A", "原商品B"],
                cfg.fact_keyword_column: ["奶粉", "奶粉", "未打词"],
                cfg.fact_impression_column: [1000, 500, 0],
                cfg.fact_click_column: [50, 25, 0],
                cfg.fact_cost_column: [100, 50, 30],
                cfg.fact_order_row_column: [10, 5, 0],
                cfg.fact_gmv_column: [400, 200, 0],
                cfg.fact_cart_column: [20, 10, 0],
                cfg.fact_new_customer_column: [5, 3, 0],
            }
        ),
        "keyword_tag": pd.DataFrame(
            {
                cfg.keyword_column: ["奶粉"],
                cfg.keyword_category_column: ["品类词"],
                cfg.keyword_second_category_column: ["品类词-奶粉"],
            }
        ),
        "channel_tag": pd.DataFrame(
            {
                cfg.channel_scene_column: ["常规推广-关键词"],
                cfg.plan_aggregate_column: ["常规推广"],
                cfg.new_channel_column: ["常规推广-关键词"],
                cfg.channel_type_column: ["站内"],
            }
        ),
        "sku_tag": pd.DataFrame(
            {
                cfg.sku_id_column: [1001, 1002],
                cfg.sku_product_name_column: ["启赋蓝钻", "启赋有机"],
                cfg.brand_column: ["惠氏", "惠氏"],
                cfg.sku_category_column: ["启赋", "启赋"],
                cfg.sku_second_category_column: ["奶粉", "奶粉"],
                cfg.stage_column: ["3段", "2段"],
            }
        ),
    }


if __name__ == "__main__":
    unittest.main()
