import unittest
from io import BytesIO
from pathlib import Path

import pandas as pd

from app.core.loader import load_shared_sheets
from app.dashboards.ad_summary.config import AppConfig as AdSummaryConfig
from app.dashboards.channel_analysis.config import AppConfig as ChannelAnalysisConfig
from app.dashboards.material_analysis.config import AppConfig as MaterialAnalysisConfig


class TestLoadingOptimization(unittest.TestCase):
    def test_load_shared_sheets_limits_columns_by_alias(self) -> None:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame(
                {
                    "日期": [20250101],
                    "推广计划": ["计划A"],
                    "花费": [10],
                    "无关列": ["不应读取"],
                }
            ).to_excel(writer, sheet_name="数据中心-创意数据", index=False)

        tables = load_shared_sheets(
            buffer.getvalue(),
            "demo.xlsx",
            "demo-token",
            {"creative": "数据中心-创意数据"},
            {"creative": ["日期", "推广计划", "花费"]},
        )

        self.assertEqual(list(tables["creative"].columns), ["日期", "推广计划", "花费"])

    def test_dashboard_configs_declare_required_columns(self) -> None:
        material_config = MaterialAnalysisConfig()
        ad_config = AdSummaryConfig()
        channel_config = ChannelAnalysisConfig()

        self.assertEqual(
            material_config.source_usecols["creative"],
            [
                material_config.date_column,
                material_config.campaign_column,
                material_config.plan_type_column,
                material_config.sku_id_column,
                material_config.impressions_column,
                material_config.clicks_column,
                material_config.cost_column,
                material_config.gmv_column,
                material_config.orders_column,
            ],
        )
        self.assertIn(ad_config.shop_gmv_source_column, ad_config.source_usecols["shop"])
        self.assertIn(ad_config.station_scene_column, ad_config.source_usecols["station"])
        self.assertIn(ad_config.sku_tag_id_column, ad_config.tag_usecols["sku_tag"])
        self.assertIn(ad_config.channel_scene_column, ad_config.tag_usecols["channel_tag"])
        self.assertIn(channel_config.ad_impression_column, channel_config.source_usecols["ad"])

    def test_ad_summary_config_uses_new_source_sheets(self) -> None:
        ad_config = AdSummaryConfig()

        self.assertEqual(
            ad_config.required_sheets,
            {
                "station": "站内外数据源",
                "brand": "品专数据源",
                "cps": "CPS数据源",
                "sitewide": "全站营销数据源",
                "shop": "店铺商智销售",
            },
        )
        self.assertEqual(
            ad_config.required_tag_sheets,
            {"channel_tag": "渠道打标", "sku_tag": "商品打标"},
        )

    def test_business_pages_do_not_load_entire_workbook(self) -> None:
        page_dir = Path(__file__).resolve().parents[1] / "pages"
        page_paths = sorted(page_dir.glob("*.py"))

        for path in page_paths:
            source = path.read_text(encoding="utf-8")
            with self.subTest(page=path.name):
                self.assertNotIn("load_shared_workbook(", source)
                self.assertNotIn("select_required_sheets(", source)


if __name__ == "__main__":
    unittest.main()
