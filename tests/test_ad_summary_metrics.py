import importlib.util
import unittest
from pathlib import Path

import pandas as pd

from app.dashboards.ad_summary.config import AppConfig
from app.dashboards.ad_summary.metrics import (
    _build_change_ratio,
    build_period_summary,
    build_summary_and_total,
    build_total_row_for_scope,
)
from app.dashboards.ad_summary.processor import build_ad_summary_dataset


PAGE_MODULE_PATH = Path(__file__).resolve().parents[1] / "pages" / "02_广告数据汇总.py"
SPEC = importlib.util.spec_from_file_location("ad_summary_page_for_metrics", PAGE_MODULE_PATH)
ad_summary_page = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ad_summary_page)


class TestAdSummaryMetrics(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AppConfig()

    def _build_tables(self) -> dict[str, pd.DataFrame]:
        cfg = self.config
        return {
            "station": pd.DataFrame(
                {
                    cfg.station_date_column: [20250101],
                    cfg.station_scene_column: ["商品推广"],
                    cfg.station_sku_column: [1001],
                    cfg.station_sku_name_column: ["原商品名"],
                    cfg.station_cost_column: [100],
                    cfg.station_impression_column: [1000],
                    cfg.station_click_column: [50],
                    cfg.station_order_row_column: [10],
                    cfg.station_gmv_column: [400],
                    cfg.station_cart_column: [5],
                    cfg.station_new_customer_column: [2],
                }
            ),
            "brand": pd.DataFrame(
                {
                    cfg.brand_date_column: [pd.Timestamp("2025-01-01")],
                    cfg.brand_cost_column: [20],
                    cfg.brand_impression_column: [200],
                    cfg.brand_click_column: [10],
                    cfg.brand_exposure_column: [300],
                    cfg.brand_exposure_click_column: [12],
                    cfg.brand_order_row_column: [3],
                    cfg.brand_gmv_column: [120],
                    cfg.brand_cart_column: [1],
                }
            ),
            "cps": pd.DataFrame(
                {
                    cfg.cps_sku_column: ["1001"],
                    cfg.cps_date_column: ["2025-01-01"],
                    cfg.cps_gmv_column: [80],
                    cfg.cps_cost_column: [8],
                    cfg.cps_order_row_column: [2],
                }
            ),
            "sitewide": pd.DataFrame(
                {
                    cfg.sitewide_date_column: [20250101],
                    cfg.sitewide_cost_column: [30],
                    cfg.sitewide_gmv_column: [90],
                    cfg.sitewide_order_row_column: [3],
                    cfg.sitewide_impression_column: [300],
                    cfg.sitewide_click_column: [15],
                    cfg.sitewide_new_customer_column: [1],
                }
            ),
            "shop": pd.DataFrame(
                {
                    cfg.shop_date_column: [pd.Timestamp("2025-01-01")],
                    cfg.shop_sku_id_column: [1001],
                    cfg.shop_product_name_column: ["店铺商品名"],
                    cfg.shop_brand_column: ["店铺品牌"],
                    cfg.shop_pv_source_column: [1000],
                    cfg.shop_visitor_source_column: [200],
                    cfg.shop_buyer_source_column: [20],
                    cfg.shop_item_count_source_column: [30],
                    cfg.shop_gmv_source_column: [500],
                }
            ),
            "channel_tag": pd.DataFrame(
                {
                    cfg.channel_scene_column: ["商品推广", "京挑客", "搜索品专", "全站营销"],
                    cfg.plan_aggregate_column: ["搜索计划", "其他", "其他", "其他"],
                    cfg.new_channel_column: ["搜索快车", "京挑客", "搜索品专", "全站营销"],
                    cfg.channel_type_column: ["搜索", "CPS", "品专", "全站"],
                }
            ),
            "sku_tag": pd.DataFrame(
                {
                    cfg.sku_tag_id_column: [1001],
                    cfg.sku_tag_name_column: ["商品A"],
                    cfg.sku_tag_brand_column: ["雀巢"],
                    cfg.sku_tag_category_column: ["启护"],
                }
            ),
        }

    def test_build_ad_summary_dataset_normalizes_new_sources_and_tags(self) -> None:
        cfg = self.config
        result = build_ad_summary_dataset(self._build_tables(), cfg)

        station_row = result[result[cfg.plan_aggregate_column] == "搜索计划"].iloc[0]
        cps_row = result[result[cfg.new_channel_column] == "京挑客"].iloc[0]
        brand_row = result[result[cfg.new_channel_column] == "搜索品专"].iloc[0]
        sitewide_row = result[result[cfg.new_channel_column] == "全站营销"].iloc[0]
        shop_row = result[result[cfg.source_type_column] == cfg.shop_source_type].iloc[0]

        self.assertEqual(station_row[cfg.product_name_column], "商品A")
        self.assertEqual(station_row[cfg.category_column], "启护")
        self.assertEqual(station_row[cfg.brand_column], "雀巢")
        self.assertEqual(station_row[cfg.channel_type_column], "搜索")
        self.assertEqual(station_row[cfg.new_channel_column], "搜索快车")
        self.assertEqual(cps_row[cfg.product_name_column], "商品A")
        self.assertEqual(cps_row[cfg.ad_cost_column], 8)
        self.assertEqual(cps_row[cfg.plan_aggregate_column], "其他")
        self.assertEqual(cps_row[cfg.channel_type_column], "CPS")
        self.assertEqual(brand_row[cfg.plan_aggregate_column], "其他")
        self.assertEqual(brand_row[cfg.channel_type_column], "品专")
        self.assertEqual(sitewide_row[cfg.plan_aggregate_column], "其他")
        self.assertEqual(sitewide_row[cfg.channel_type_column], "全站")
        self.assertEqual(shop_row[cfg.shop_gmv_column], 500)
        self.assertEqual(shop_row[cfg.year_column], 2025)
        self.assertEqual(shop_row[cfg.month_label_column], "M1")

    def test_synthetic_scene_sources_take_channel_values_from_tag_sheet(self) -> None:
        cfg = self.config
        tables = self._build_tables()
        tables["channel_tag"] = pd.DataFrame(
            {
                cfg.channel_scene_column: ["商品推广", "京挑客", "搜索品专", "全站营销"],
                cfg.plan_aggregate_column: ["搜索计划", "联盟计划", "品专计划", "全站计划"],
                cfg.new_channel_column: ["搜索快车", "京挑客渠道", "搜索品专渠道", "全站营销渠道"],
                cfg.channel_type_column: ["搜索", "CPS渠道", "品专渠道", "全站渠道"],
            }
        )

        result = build_ad_summary_dataset(tables, cfg)
        cps_row = result[result[cfg.ad_cost_column] == 8].iloc[0]
        brand_row = result[result[cfg.ad_cost_column] == 20].iloc[0]
        sitewide_row = result[result[cfg.ad_cost_column] == 30].iloc[0]

        self.assertEqual(cps_row[cfg.plan_aggregate_column], "联盟计划")
        self.assertEqual(cps_row[cfg.new_channel_column], "京挑客渠道")
        self.assertEqual(cps_row[cfg.channel_type_column], "CPS渠道")
        self.assertEqual(brand_row[cfg.plan_aggregate_column], "品专计划")
        self.assertEqual(brand_row[cfg.new_channel_column], "搜索品专渠道")
        self.assertEqual(brand_row[cfg.channel_type_column], "品专渠道")
        self.assertEqual(sitewide_row[cfg.plan_aggregate_column], "全站计划")
        self.assertEqual(sitewide_row[cfg.new_channel_column], "全站营销渠道")
        self.assertEqual(sitewide_row[cfg.channel_type_column], "全站渠道")

    def test_build_ad_summary_dataset_keeps_year_as_integer_with_missing_dates(self) -> None:
        cfg = self.config
        tables = self._build_tables()
        tables["cps"].loc[0, cfg.cps_date_column] = None

        result = build_ad_summary_dataset(tables, cfg)
        valid_years = result[cfg.year_column].dropna().unique().tolist()

        self.assertEqual(str(result[cfg.year_column].dtype), "Int64")
        self.assertEqual(valid_years, [2025])

    def test_build_period_summary_recalculates_metrics_after_sum(self) -> None:
        cfg = self.config
        detail_df = build_ad_summary_dataset(self._build_tables(), cfg)

        result = build_period_summary(detail_df, "month", cfg, shop_metric_df=detail_df)
        row = result.iloc[0]

        self.assertEqual(result.columns.tolist(), cfg.display_columns)
        self.assertEqual(row["广告费用"], 158)
        self.assertEqual(row["投放GMV"], 690)
        self.assertEqual(row["店铺GMV"], 500)
        self.assertEqual(row["广告点击"], 75)
        self.assertAlmostEqual(row["广告GMV贡献"], 690 / 500, places=4)
        self.assertAlmostEqual(row["广告ROI"], 690 / 158, places=4)
        self.assertAlmostEqual(row["费比"], 158 / 500, places=4)
        self.assertAlmostEqual(row["PV贡献"], 75 / 1000, places=4)
        self.assertAlmostEqual(row["店铺转化率"], 20 / 200, places=4)
        self.assertAlmostEqual(row["商品单价"], 500 / 30, places=4)
        self.assertEqual(row["店铺GMV目标"], 0)
        self.assertEqual(row["店铺完成进度"], 0)

    def test_shop_metrics_ignore_ad_dimensions_but_keep_product_scope(self) -> None:
        cfg = self.config
        detail_df = build_ad_summary_dataset(self._build_tables(), cfg)
        selections = {
            cfg.year_column: 2025,
            cfg.new_channel_column: ["搜索快车"],
            cfg.product_name_column: ["商品A"],
        }
        filter_fields = ad_summary_page.build_filter_fields(cfg)
        filtered_df = ad_summary_page.apply_filters(detail_df, selections, filter_fields)
        shop_df = ad_summary_page.apply_filters(
            detail_df,
            ad_summary_page.build_shop_metric_selections(selections, cfg),
            filter_fields,
        )

        result = build_period_summary(filtered_df, "month", cfg, shop_metric_df=shop_df)
        row = result.iloc[0]

        self.assertEqual(row["广告费用"], 100)
        self.assertEqual(row["投放GMV"], 400)
        self.assertEqual(row["店铺GMV"], 500)
        self.assertEqual(row["PV"], 1000)

    def test_build_total_row_uses_zero_target_when_target_source_missing(self) -> None:
        cfg = self.config
        detail_df = build_ad_summary_dataset(self._build_tables(), cfg)

        total_df = build_total_row_for_scope(detail_df, cfg, detail_df)
        row = total_df.iloc[0]

        self.assertEqual(row[cfg.period_label_column], "总计")
        self.assertEqual(row["店铺GMV目标"], 0)
        self.assertEqual(row["店铺完成进度"], 0)
        self.assertTrue(pd.isna(row["消耗环比"]))
        self.assertTrue(pd.isna(row[cfg.shop_gmv_ratio_tail_column]))

    def test_build_summary_and_total_uses_period_scope_only(self) -> None:
        cfg = self.config
        detail_df = build_ad_summary_dataset(self._build_tables(), cfg)
        next_month = detail_df.copy()
        next_month[cfg.date_column] = next_month[cfg.date_column] + pd.DateOffset(months=1)
        next_month[cfg.month_label_column] = "M2"
        next_month[cfg.month_sort_column] = 2
        combined_df = pd.concat([detail_df, next_month], ignore_index=True)

        summary_df, total_df = build_summary_and_total(combined_df, "month", cfg, shop_metric_df=combined_df)

        self.assertEqual(summary_df[cfg.period_label_column].tolist(), ["M1", "M2"])
        self.assertEqual(total_df.iloc[0]["广告费用"], 316)
        self.assertEqual(total_df.iloc[0]["店铺GMV"], 1000)

    def test_build_change_ratio_returns_zero_for_invalid_previous(self) -> None:
        series = pd.Series([100.0, None, pd.NA, "", 0, 200.0])

        result = _build_change_ratio(series)

        self.assertEqual(result.tolist(), [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])


if __name__ == "__main__":
    unittest.main()
