import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
AD_SUMMARY_PAGE_PATH = ROOT / "pages" / "02_广告数据汇总.py"
CHANNEL_ANALYSIS_PAGE_PATH = ROOT / "pages" / "03_渠道分析.py"
KEYWORD_ANALYSIS_PAGE_PATH = ROOT / "pages" / "04_关键词分析.py"


class TestPageRadioReset(unittest.TestCase):
    def test_ad_summary_period_radio_survives_filter_reset(self) -> None:
        """验证广告汇总恢复筛选默认后仍保持当前汇总周期。"""
        app = AppTest.from_string(_build_ad_summary_app_code())

        first_run = app.run(timeout=120)
        self.assertEqual(first_run.radio[0].value, "季度汇总")

        first_run.radio[0].set_value("月度汇总")
        second_run = app.run(timeout=120)
        self.assertEqual(second_run.radio[0].value, "月度汇总")

        second_run.button[0].click()
        third_run = app.run(timeout=120)
        self.assertEqual(third_run.radio[0].value, "月度汇总")

    def test_channel_analysis_view_radio_survives_filter_reset(self) -> None:
        """验证渠道分析恢复筛选默认后仍保持当前主视图。"""
        app = AppTest.from_string(_build_channel_analysis_app_code())

        first_run = app.run(timeout=120)
        self.assertEqual(first_run.radio[0].value, "分类汇总")

        first_run.radio[0].set_value("时间渠道")
        second_run = app.run(timeout=120)
        self.assertEqual(second_run.radio[0].value, "时间渠道")

        second_run.button[0].click()
        third_run = app.run(timeout=120)
        self.assertEqual(third_run.radio[0].value, "时间渠道")

    def test_keyword_analysis_view_radio_survives_filter_reset(self) -> None:
        """验证关键词分析恢复筛选默认后仍保持当前主视图。"""
        app = AppTest.from_string(_build_keyword_analysis_app_code())

        first_run = app.run(timeout=120)
        self.assertEqual(first_run.radio[0].value, "词性汇总")

        first_run.radio[0].set_value("时间渠道")
        second_run = app.run(timeout=120)
        self.assertEqual(second_run.radio[0].value, "时间渠道")

        second_run.button[0].click()
        third_run = app.run(timeout=120)
        self.assertEqual(third_run.radio[0].value, "时间渠道")


def _build_ad_summary_app_code() -> str:
    """构造广告汇总页面的 Streamlit 测试应用代码。"""
    return f"""
import importlib.util
from pathlib import Path

import pandas as pd

PAGE_MODULE_PATH = Path(r"{AD_SUMMARY_PAGE_PATH}")
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
summary_df = pd.DataFrame({{cfg.period_label_column: ["M1"]}})
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


def _build_channel_analysis_app_code() -> str:
    """构造渠道分析页面的 Streamlit 测试应用代码。"""
    return f"""
import importlib.util
from pathlib import Path

import pandas as pd

PAGE_MODULE_PATH = Path(r"{CHANNEL_ANALYSIS_PAGE_PATH}")
SPEC = importlib.util.spec_from_file_location("channel_analysis_page_runtime", PAGE_MODULE_PATH)
channel_analysis_page = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(channel_analysis_page)

cfg = channel_analysis_page.AppConfig()
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
    cfg.line_column: ["奶粉"],
    cfg.sku_product_name_column: ["启赋"],
}})
payload = channel_analysis_page.ChannelAnalysisPayload(
    channel_df=pd.DataFrame({{cfg.new_channel_column: ["搜索快车"]}}),
    category_df=pd.DataFrame({{cfg.new_channel_column: ["搜索快车"]}}),
    time_df=pd.DataFrame({{cfg.new_channel_column: ["搜索快车"]}}),
    total_df=pd.DataFrame({{cfg.new_channel_column: ["总计"]}}),
)

channel_analysis_page.has_shared_source = lambda: True
channel_analysis_page.has_tag_source = lambda: True
channel_analysis_page.get_shared_source_name = lambda: "mock_source.xlsx"
channel_analysis_page.get_tag_source_name = lambda: "mock_tag.xlsx"
channel_analysis_page.get_shared_source_bytes = lambda: b"source"
channel_analysis_page.get_tag_source_bytes = lambda: b"tag"
channel_analysis_page.get_shared_source_token = lambda: "source-token"
channel_analysis_page.get_tag_source_token = lambda: "tag-token"
channel_analysis_page.load_channel_analysis_dataset = lambda *args, **kwargs: detail_df.copy()
channel_analysis_page.load_channel_analysis_payload = lambda *args, **kwargs: payload
channel_analysis_page.channel_ui.render_channel_tree_table = lambda *args, **kwargs: None
channel_analysis_page.channel_ui.render_category_tree_table = lambda *args, **kwargs: None
channel_analysis_page.channel_ui.render_time_tree_table = lambda *args, **kwargs: None
channel_analysis_page.channel_ui.render_total_table = lambda *args, **kwargs: None
channel_analysis_page.channel_ui.render_empty_state = lambda *args, **kwargs: None

channel_analysis_page.main()
"""


def _build_keyword_analysis_app_code() -> str:
    """构造关键词分析页面的 Streamlit 测试应用代码。"""
    return f"""
import importlib.util
from pathlib import Path

import pandas as pd

PAGE_MODULE_PATH = Path(r"{KEYWORD_ANALYSIS_PAGE_PATH}")
SPEC = importlib.util.spec_from_file_location("keyword_analysis_page_runtime", PAGE_MODULE_PATH)
keyword_analysis_page = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(keyword_analysis_page)

cfg = keyword_analysis_page.AppConfig()
detail_df = pd.DataFrame({{
    cfg.year_column: [2025],
    cfg.quarter_label_column: ["Q1"],
    cfg.month_label_column: ["M1"],
    cfg.week_label_column: ["W1"],
    cfg.day_label_column: ["2025/1/1"],
    cfg.keyword_category_column: ["品类词"],
    cfg.keyword_second_category_column: ["品类词-奶粉"],
    cfg.keyword_column: ["奶粉"],
    cfg.channel_type_column: ["搜索"],
    cfg.new_channel_column: ["搜索快车"],
    cfg.plan_aggregate_column: ["搜索计划"],
    cfg.brand_column: ["惠氏"],
    cfg.line_column: ["奶粉"],
    cfg.sku_product_name_column: ["启赋"],
}})
payload = keyword_analysis_page.KeywordAnalysisPayload(
    classification_df=pd.DataFrame({{cfg.keyword_column: ["奶粉"]}}),
    time_df=pd.DataFrame({{cfg.keyword_column: ["奶粉"]}}),
    total_df=pd.DataFrame({{cfg.keyword_column: ["总计"]}}),
)

keyword_analysis_page.has_shared_source = lambda: True
keyword_analysis_page.has_tag_source = lambda: True
keyword_analysis_page.get_shared_source_name = lambda: "mock_source.xlsx"
keyword_analysis_page.get_tag_source_name = lambda: "mock_tag.xlsx"
keyword_analysis_page.get_shared_source_bytes = lambda: b"source"
keyword_analysis_page.get_tag_source_bytes = lambda: b"tag"
keyword_analysis_page.get_shared_source_token = lambda: "source-token"
keyword_analysis_page.get_tag_source_token = lambda: "tag-token"
keyword_analysis_page.load_keyword_analysis_dataset = lambda *args, **kwargs: detail_df.copy()
keyword_analysis_page.load_keyword_analysis_payload = lambda *args, **kwargs: payload
keyword_analysis_page.keyword_ui.render_classification_table = lambda *args, **kwargs: None
keyword_analysis_page.keyword_ui.render_time_table = lambda *args, **kwargs: None
keyword_analysis_page.keyword_ui.render_total_table = lambda *args, **kwargs: None
keyword_analysis_page.keyword_ui.render_empty_state = lambda *args, **kwargs: None

keyword_analysis_page.main()
"""


if __name__ == "__main__":
    unittest.main()
