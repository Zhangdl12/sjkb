import unittest

import pandas as pd

from app.dashboards.tag_validation.config import AppConfig
from app.dashboards.tag_validation.processor import build_sku_dataset
from app.dashboards.tag_validation.tree_builder import (
    build_audience_tree_payload,
    build_keyword_tree_payload,
    build_sku_tree_payload,
)
from app.dashboards.tag_validation.ui import _build_tree_grid_options


class TestTagValidationSkuName(unittest.TestCase):
    def test_build_sku_dataset_includes_product_name_from_match_table(self) -> None:
        config = AppConfig()
        tables = {
            "sku_match": pd.DataFrame(
                {
                    config.sku_match_id_column: ["1001", "1002"],
                    config.sku_category_column: ["奶粉", "零食"],
                    "商品名称": ["启赋蕴淳", "小饼干"],
                }
            ),
            "sku_fact": pd.DataFrame(
                {
                    config.sku_fact_id_column: ["1001", "1001", "9999"],
                    config.sku_cost_column: [100, 60, 20],
                }
            ),
        }

        result = build_sku_dataset(tables, config)

        self.assertEqual(
            list(result.columns),
            [
                config.display_sku_category_column,
                config.sku_fact_id_column,
                config.display_sku_cost_column,
                config.sku_name_column,
            ],
        )
        self.assertEqual(
            result.loc[
                result[config.sku_fact_id_column] == "1001", config.sku_name_column
            ].tolist(),
            ["启赋蕴淳", "启赋蕴淳"],
        )
        self.assertEqual(
            result.loc[
                result[config.sku_fact_id_column] == "9999", config.sku_name_column
            ].tolist(),
            [""],
        )

    def test_build_sku_tree_payload_keeps_product_name_only_on_child_rows(self) -> None:
        config = AppConfig()
        sku_df = pd.DataFrame(
            {
                config.display_sku_category_column: ["奶粉", "奶粉", config.blank_category],
                config.sku_fact_id_column: ["1001", "1001", "9999"],
                config.display_sku_cost_column: [100, 60, 20],
                config.sku_name_column: ["启赋蕴淳", "启赋蕴淳", ""],
            }
        )

        tree_df = build_sku_tree_payload(sku_df, [], config).tree_df

        parent_row = tree_df.loc[tree_df["path"] == "奶粉"].iloc[0]
        child_row = tree_df.loc[tree_df["path"] == "奶粉||1001"].iloc[0]

        self.assertEqual(parent_row[config.sku_fact_id_column], "")
        self.assertEqual(parent_row[config.sku_name_column], "")
        self.assertEqual(child_row[config.sku_fact_id_column], "1001")
        self.assertEqual(child_row[config.sku_name_column], "启赋蕴淳")
        self.assertEqual(child_row[config.display_sku_cost_column], 160.0)

    def test_sku_grid_options_include_product_name_column(self) -> None:
        config = AppConfig()

        grid_options = _build_tree_grid_options(
            category_column_name=config.display_sku_category_column,
            cost_column_name=config.display_sku_cost_column,
            extra_columns=[
                {
                    "field": config.sku_fact_id_column,
                    "headerName": config.sku_fact_id_column,
                },
                {
                    "field": config.sku_name_column,
                    "headerName": config.display_sku_name_column,
                }
            ],
        )

        column_fields = [column["field"] for column in grid_options["columnDefs"]]

        self.assertEqual(
            column_fields,
            [
                config.sku_fact_id_column,
                config.sku_name_column,
                config.display_sku_cost_column,
                "path",
            ],
        )

    def test_sku_grid_options_can_hide_child_text_in_tree_column(self) -> None:
        config = AppConfig()

        grid_options = _build_tree_grid_options(
            category_column_name=config.display_sku_category_column,
            cost_column_name=config.display_sku_cost_column,
            auto_group_inner_renderer="mock-renderer",
        )

        self.assertEqual(
            grid_options["autoGroupColumnDef"]["cellRendererParams"]["innerRenderer"],
            "mock-renderer",
        )

    def test_keyword_tree_payload_keeps_keyword_only_on_child_rows(self) -> None:
        config = AppConfig()
        keyword_df = pd.DataFrame(
            {
                config.display_keyword_category_column: ["品牌词", "品牌词", config.blank_category],
                config.keyword_column: ["启赋", "启赋", "蓝臻"],
                config.display_keyword_cost_column: [100, 60, 20],
            }
        )

        tree_df = build_keyword_tree_payload(keyword_df, [], config).tree_df

        parent_row = tree_df.loc[tree_df["path"] == "品牌词"].iloc[0]
        child_row = tree_df.loc[tree_df["path"] == "品牌词||启赋"].iloc[0]

        self.assertEqual(parent_row[config.keyword_column], "")
        self.assertEqual(child_row[config.keyword_column], "启赋")
        self.assertEqual(child_row[config.display_keyword_cost_column], 160.0)

    def test_audience_tree_payload_keeps_audience_name_only_on_child_rows(self) -> None:
        config = AppConfig()
        audience_df = pd.DataFrame(
            {
                config.display_audience_category_column: ["宝妈", "宝妈", config.blank_category],
                config.audience_name_column: ["高潜宝妈", "高潜宝妈", "泛人群"],
                config.display_audience_cost_column: [100, 60, 20],
            }
        )

        tree_df = build_audience_tree_payload(audience_df, [], config).tree_df

        parent_row = tree_df.loc[tree_df["path"] == "宝妈"].iloc[0]
        child_row = tree_df.loc[tree_df["path"] == "宝妈||高潜宝妈"].iloc[0]

        self.assertEqual(parent_row[config.audience_name_column], "")
        self.assertEqual(child_row[config.audience_name_column], "高潜宝妈")
        self.assertEqual(child_row[config.display_audience_cost_column], 160.0)

    def test_keyword_grid_options_include_keyword_column(self) -> None:
        config = AppConfig()

        grid_options = _build_tree_grid_options(
            category_column_name=config.display_keyword_category_column,
            cost_column_name=config.display_keyword_cost_column,
            extra_columns=[
                {
                    "field": config.keyword_column,
                    "headerName": config.keyword_column,
                }
            ],
            auto_group_inner_renderer="mock-renderer",
        )

        column_fields = [column["field"] for column in grid_options["columnDefs"]]

        self.assertEqual(
            column_fields,
            [
                config.keyword_column,
                config.display_keyword_cost_column,
                "path",
            ],
        )
        self.assertEqual(
            grid_options["autoGroupColumnDef"]["cellRendererParams"]["innerRenderer"],
            "mock-renderer",
        )

    def test_audience_grid_options_include_audience_column(self) -> None:
        config = AppConfig()

        grid_options = _build_tree_grid_options(
            category_column_name=config.display_audience_category_column,
            cost_column_name=config.display_audience_cost_column,
            extra_columns=[
                {
                    "field": config.audience_name_column,
                    "headerName": config.audience_name_column,
                }
            ],
            auto_group_inner_renderer="mock-renderer",
        )

        column_fields = [column["field"] for column in grid_options["columnDefs"]]

        self.assertEqual(
            column_fields,
            [
                config.audience_name_column,
                config.display_audience_cost_column,
                "path",
            ],
        )
        self.assertEqual(
            grid_options["autoGroupColumnDef"]["cellRendererParams"]["innerRenderer"],
            "mock-renderer",
        )


if __name__ == "__main__":
    unittest.main()
