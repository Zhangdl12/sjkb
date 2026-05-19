import importlib.util
import unittest
from pathlib import Path

import pandas as pd

from app.dashboards.audience_analysis.config import AppConfig
from app.dashboards.audience_analysis.metrics import (
    build_classification_summary,
    build_time_summary,
    build_total,
)
from app.dashboards.audience_analysis.processor import build_audience_analysis_dataset
from app.dashboards.audience_analysis.service import build_audience_analysis_payload, build_filter_summary
from app.dashboards.audience_analysis.ui import _build_column_def, _build_tree_grid_options


PAGE_MODULE_PATH = Path(__file__).resolve().parents[1] / "pages" / "05_人群分析.py"
SPEC = importlib.util.spec_from_file_location("audience_analysis_page", PAGE_MODULE_PATH)
audience_analysis_page = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audience_analysis_page)


class TestAudienceAnalysis(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AppConfig()

    def test_build_dataset_merges_audience_channel_and_sku_tags(self) -> None:
        """验证人群事实表能正确关联人群、渠道和商品打标。"""
        cfg = self.config
        result = build_audience_analysis_dataset(_build_source_tables(cfg), cfg)

        row = result[result[cfg.audience_name_column] == "竞品兴趣人群"].iloc[0]
        blank_row = result[result[cfg.audience_name_column] == "未打人群"].iloc[0]

        self.assertEqual(len(result), 3)
        self.assertEqual(row[cfg.audience_category_column], "A1-竞品兴趣")
        self.assertEqual(row[cfg.new_channel_column], "站内人群")
        self.assertEqual(row[cfg.channel_type_column], "RTB")
        self.assertEqual(row[cfg.line_column], "启赋")
        self.assertEqual(row[cfg.sku_product_name_column], "启赋蓝钻")
        self.assertEqual(row[cfg.brand_column], "惠氏")
        self.assertEqual(row[cfg.sku_second_category_column], "奶粉")
        self.assertEqual(row[cfg.stage_column], "3段")
        self.assertEqual(blank_row[cfg.audience_category_column], cfg.blank_text)
        self.assertEqual(blank_row[cfg.new_channel_column], cfg.unknown_text)
        self.assertEqual(blank_row[cfg.line_column], cfg.unknown_text)
        self.assertEqual(blank_row[cfg.month_label_column], "M1")

    def test_optional_columns_can_be_missing(self) -> None:
        """验证商品二级分类和段位缺失时仍可正常构造数据。"""
        cfg = self.config
        tables = _build_source_tables(cfg)
        tables["sku_tag"] = tables["sku_tag"].drop(columns=[cfg.sku_second_category_column, cfg.stage_column])

        result = build_audience_analysis_dataset(tables, cfg)

        self.assertIn(cfg.sku_second_category_column, result.columns)
        self.assertIn(cfg.stage_column, result.columns)
        self.assertEqual(result[cfg.sku_second_category_column].fillna("").tolist(), ["", "", ""])

    def test_classification_summary_recalculates_ratio_metrics_after_sum(self) -> None:
        """验证人群分类汇总会先求和再重算占比、ROI、CPC 和 CTR。"""
        cfg = self.config
        dataset = build_audience_analysis_dataset(_build_source_tables(cfg), cfg)

        result = build_classification_summary(dataset, cfg)
        row = result[result[cfg.audience_name_column] == "竞品兴趣人群"].iloc[0]

        self.assertEqual(row["广告费用"], 150)
        self.assertAlmostEqual(row["花费占比%"], 150 / 180, places=4)
        self.assertAlmostEqual(row["ROI-kw"], 600 / 150, places=4)
        self.assertAlmostEqual(row["CPC-kw"], 150 / 75, places=4)
        self.assertAlmostEqual(row["CTR-kw"], 75 / 1500, places=4)
        self.assertEqual(row["点击数"], 75)
        self.assertEqual(row["总订单金额"], 600)

    def test_time_summary_calculates_extended_metrics_and_zero_denominator(self) -> None:
        """验证时间渠道表会重算扩展指标并稳定处理 0 分母。"""
        cfg = self.config
        dataset = build_audience_analysis_dataset(_build_source_tables(cfg), cfg)

        result = build_time_summary(dataset, cfg)
        row = result[(result[cfg.audience_name_column] == "竞品兴趣人群") & (result[cfg.day_label_column] == "2025/1/1")].iloc[0]
        zero = result[result[cfg.audience_name_column] == "未打人群"].iloc[0]

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
        """验证总计行按当前范围总量重算。"""
        cfg = self.config
        dataset = build_audience_analysis_dataset(_build_source_tables(cfg), cfg)

        total = build_total(dataset, cfg).iloc[0]

        self.assertEqual(total[cfg.audience_category_column], "总计")
        self.assertEqual(total["广告费用"], 180)
        self.assertEqual(total["花费占比%"], 1.0)
        self.assertAlmostEqual(total["ROI-kw"], 600 / 180, places=4)
        self.assertAlmostEqual(total["CPC-kw"], 180 / 75, places=4)

    def test_payload_and_page_helpers_build_expected_views(self) -> None:
        """验证页面 helper 和服务层 payload 能生成两类视图。"""
        cfg = self.config
        dataset = build_audience_analysis_dataset(_build_source_tables(cfg), cfg)

        classification_payload = build_audience_analysis_payload(
            {"dataset": dataset},
            {},
            audience_analysis_page.build_filter_fields(cfg),
            "人群分类",
            cfg,
        )
        time_payload = build_audience_analysis_payload(
            {"dataset": dataset},
            {},
            audience_analysis_page.build_filter_fields(cfg),
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
        self.assertIn("A1-竞品兴趣||竞品兴趣人群", classification_payload.classification_df["path"].tolist())
        self.assertIn("A1-竞品兴趣||竞品兴趣人群||M1", classification_payload.classification_df["path"].tolist())
        self.assertIn("A1-竞品兴趣||竞品兴趣人群||W1||2025/1/1", time_payload.time_df["path"].tolist())

    def test_filter_summary_and_grid_options_are_stable(self) -> None:
        """验证筛选摘要和树表配置稳定。"""
        cfg = self.config
        summary = build_filter_summary({cfg.audience_name_column: ["竞品兴趣人群"], cfg.year_column: 2025})
        grid_options = _build_tree_grid_options(
            pd.DataFrame({"path": ["A1-竞品兴趣"], "广告费用": [1]}),
            hidden_columns={"path"},
            group_header="人群分类 > 人群名称",
        )

        self.assertEqual(summary, (("人群名称", ("竞品兴趣人群",)), ("年", (2025,))))
        self.assertTrue(grid_options["treeData"])
        self.assertEqual(grid_options["groupDefaultExpanded"], 0)

    def test_numeric_columns_have_precise_tooltips(self) -> None:
        """验证小数值指标可以通过 tooltip 查看更完整精度。"""
        percent_column = _build_column_def("广告CTR")
        cost_column = _build_column_def("广告费用")

        self.assertIn("tooltipValueGetter", percent_column)
        self.assertIn("tooltipValueGetter", cost_column)
        self.assertIn("valueFormatter", percent_column)
        self.assertIn("valueFormatter", cost_column)

    def test_empty_payload_is_stable(self) -> None:
        """验证空数据场景不会导致页面访问 payload 属性时报错。"""
        cfg = self.config
        payload = build_audience_analysis_payload(
            {"dataset": pd.DataFrame(columns=cfg.classification_columns)},
            {},
            audience_analysis_page.build_filter_fields(cfg),
            "人群分类",
            cfg,
        )

        self.assertTrue(payload.classification_df.empty)
        self.assertTrue(payload.total_df.empty)


def _build_source_tables(cfg: AppConfig) -> dict[str, pd.DataFrame]:
    return {
        "audience_fact": pd.DataFrame(
            {
                cfg.fact_date_column: [20250101, 20250101, 20250102],
                cfg.fact_scene_column: ["站内人群", "站内人群", "未知场景"],
                cfg.fact_sku_column: [1001, 1001, 9999],
                cfg.fact_sku_name_column: ["原商品A", "原商品A", "原商品X"],
                cfg.fact_audience_name_column: ["竞品兴趣人群", "竞品兴趣人群", "未打人群"],
                cfg.fact_impression_column: [1000, 500, 0],
                cfg.fact_click_column: [50, 25, 0],
                cfg.fact_cost_column: [100, 50, 30],
                cfg.fact_order_row_column: [10, 5, 0],
                cfg.fact_gmv_column: [400, 200, 0],
                cfg.fact_cart_column: [20, 10, 0],
                cfg.fact_new_customer_column: [5, 3, 0],
            }
        ),
        "audience_tag": pd.DataFrame(
            {
                cfg.audience_name_column: ["竞品兴趣人群"],
                cfg.audience_category_column: ["A1-竞品兴趣"],
            }
        ),
        "channel_tag": pd.DataFrame(
            {
                cfg.channel_scene_column: ["站内人群"],
                cfg.plan_aggregate_column: ["人群计划"],
                cfg.new_channel_column: ["站内人群"],
                cfg.channel_type_column: ["RTB"],
            }
        ),
        "sku_tag": pd.DataFrame(
            {
                cfg.sku_id_column: [1001],
                cfg.sku_product_name_column: ["启赋蓝钻"],
                cfg.brand_column: ["惠氏"],
                cfg.sku_category_column: ["启赋"],
                cfg.sku_second_category_column: ["奶粉"],
                cfg.stage_column: ["3段"],
            }
        ),
    }


if __name__ == "__main__":
    unittest.main()
