import importlib.util
import unittest
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from app.dashboards.ad_summary.config import AppConfig


PAGE_MODULE_PATH = Path(__file__).resolve().parents[1] / "pages" / "02_广告数据汇总.py"
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
            cfg.channel_type_column: ["搜索"],
            cfg.new_channel_column: ["搜索快车"],
            cfg.plan_aggregate_column: ["搜索计划"],
            cfg.brand_column: ["雀巢"],
            cfg.product_name_column: ["商品A"],
        }

        shop_metric_selections = ad_summary_page.build_shop_metric_selections(selections, cfg)

        self.assertNotIn(cfg.channel_type_column, shop_metric_selections)
        self.assertNotIn(cfg.new_channel_column, shop_metric_selections)
        self.assertNotIn(cfg.plan_aggregate_column, shop_metric_selections)
        self.assertIn(cfg.brand_column, shop_metric_selections)
        self.assertIn(cfg.product_name_column, shop_metric_selections)

    def test_filter_fields_include_new_tag_dimensions(self) -> None:
        cfg = self.config
        filter_columns = [field.column for field in ad_summary_page.build_filter_fields(cfg)]

        self.assertIn(cfg.plan_aggregate_column, filter_columns)
        self.assertIn(cfg.new_channel_column, filter_columns)
        self.assertIn(cfg.channel_type_column, filter_columns)
        self.assertIn(cfg.category_column, filter_columns)
        self.assertIn(cfg.brand_column, filter_columns)

    def test_period_options_resolve_selected_period(self) -> None:
        period_options = ad_summary_page.get_period_options()

        self.assertEqual(
            period_options,
            (
                ("季度汇总", "quarter"),
                ("月度汇总", "month"),
                ("周度汇总", "week"),
                ("日度汇总", "day"),
            ),
        )
        self.assertEqual(
            ad_summary_page._resolve_selected_period("月度汇总", period_options),
            "month",
        )

    def test_period_radio_keeps_current_selection_after_rerun(self) -> None:
        """验证页面级汇总周期单选在普通 rerun 后保持当前选择。"""
        cfg = self.config
        detail_df = pd.DataFrame(
            {
                cfg.year_column: [2025],
                cfg.quarter_label_column: ["Q1"],
                cfg.month_label_column: ["M1"],
                cfg.week_label_column: ["W1"],
                cfg.day_label_column: ["2025/1/1"],
                cfg.channel_type_column: ["搜索"],
                cfg.new_channel_column: ["搜索快车"],
                cfg.plan_aggregate_column: ["搜索计划"],
                cfg.brand_column: ["惠氏"],
                cfg.category_column: ["奶粉"],
                cfg.product_name_column: ["启赋"],
            }
        )
        summary_df = pd.DataFrame({cfg.period_label_column: ["W1"]})
        total_df = pd.DataFrame({cfg.period_label_column: ["总计"]})

        app_code = f"""
import importlib.util
from pathlib import Path

import pandas as pd

PAGE_MODULE_PATH = Path(r"{PAGE_MODULE_PATH}")
SPEC = importlib.util.spec_from_file_location("ad_summary_page_runtime", PAGE_MODULE_PATH)
ad_summary_page = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ad_summary_page)

cfg = ad_summary_page.AppConfig()
detail_df = pd.DataFrame({{
    cfg.year_column: [2025],
    cfg.quarter_label_column: ["Q1"],
    cfg.month_label_column: ["M1"],
    cfg.week_label_column: ["W1"],
    cfg.day_label_column: ["2025/1/1"],
    cfg.channel_type_column: ["搜索"],
    cfg.new_channel_column: ["搜索快车"],
    cfg.plan_aggregate_column: ["搜索计划"],
    cfg.brand_column: ["惠氏"],
    cfg.category_column: ["奶粉"],
    cfg.product_name_column: ["启赋"],
}})
summary_df = pd.DataFrame({{cfg.period_label_column: ["W1"]}})
total_df = pd.DataFrame({{cfg.period_label_column: ["总计"]}})

ad_summary_page.has_shared_source = lambda: True
ad_summary_page.has_tag_source = lambda: True
ad_summary_page.get_shared_source_name = lambda: "mock_source.xlsx"
ad_summary_page.get_tag_source_name = lambda: "mock_tag.xlsx"
ad_summary_page.load_current_source_sheets = lambda required_sheets, usecols: {{}}
ad_summary_page.load_current_tag_sheets = lambda required_sheets, usecols: {{}}
ad_summary_page.build_ad_summary_dataset = lambda tables, config: detail_df.copy()
ad_summary_page.ad_metrics.build_summary_and_total = (
    lambda filtered_df, period, config, shop_metric_df=None, yoy_source_df=None, include_click_yoy=True: (
        summary_df.copy(),
        total_df.copy(),
    )
)
ad_summary_page.ad_ui.render_summary_table = lambda *args, **kwargs: None
ad_summary_page.ad_ui.render_total_table = lambda *args, **kwargs: None
ad_summary_page.ad_ui.render_empty_state = lambda *args, **kwargs: None

ad_summary_page.main()
"""

        app = AppTest.from_string(app_code)

        first_run = app.run(timeout=120)
        self.assertEqual(first_run.radio[0].value, "季度汇总")

        first_run.radio[0].set_value("周度汇总")
        second_run = app.run(timeout=120)
        self.assertEqual(second_run.radio[0].value, "周度汇总")

        third_run = app.run(timeout=120)
        self.assertEqual(third_run.radio[0].value, "周度汇总")


if __name__ == "__main__":
    unittest.main()
