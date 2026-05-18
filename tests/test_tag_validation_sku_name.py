import unittest
from hashlib import md5
from io import BytesIO

import pandas as pd

from app.core.loader import load_excel_sheets
from app.dashboards.tag_validation.config import AppConfig
from app.dashboards.tag_validation.processor import (
    build_audience_dataset,
    build_keyword_dataset,
    build_sku_dataset,
)
from app.dashboards.tag_validation.service import load_tag_validation_payloads
from app.dashboards.tag_validation.tree_builder import (
    build_audience_tree_payload,
    build_keyword_tree_payload,
    build_sku_tree_payload,
)
from app.dashboards.tag_validation.ui import _build_tree_grid_options


class TestTagValidation(unittest.TestCase):
    def test_load_excel_sheets_can_limit_columns_by_alias(self) -> None:
        buffer = BytesIO()
        source_df = pd.DataFrame({"关键词": ["奶粉"], "花费": [10], "点击数": [3]})
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            source_df.to_excel(writer, sheet_name="关键词数据源", index=False)

        tables = load_excel_sheets(
            buffer.getvalue(),
            {"keyword_fact": "关键词数据源"},
            {"keyword_fact": ["关键词", "花费"]},
        )

        self.assertEqual(list(tables["keyword_fact"].columns), ["关键词", "花费"])

    def test_load_tag_validation_payloads_builds_three_tables_once(self) -> None:
        config = AppConfig()
        source_buffer = BytesIO()
        tag_buffer = BytesIO()

        with pd.ExcelWriter(source_buffer, engine="openpyxl") as writer:
            pd.DataFrame(
                {
                    config.keyword_column: ["品牌词", "品牌词"],
                    config.keyword_cost_column: [10, 5],
                    "无关列": ["不应读取", "不应读取"],
                }
            ).to_excel(writer, sheet_name=config.keyword_fact_sheet, index=False)
            pd.DataFrame(
                {
                    config.audience_name_column: ["宝妈"],
                    config.audience_cost_column: [20],
                    "无关列": ["不应读取"],
                }
            ).to_excel(writer, sheet_name=config.audience_fact_sheet, index=False)
            pd.DataFrame(
                {
                    config.sku_fact_id_column: ["1001"],
                    config.sku_cost_column: [30],
                    "无关列": ["不应读取"],
                }
            ).to_excel(writer, sheet_name=config.sku_fact_sheet, index=False)

        with pd.ExcelWriter(tag_buffer, engine="openpyxl") as writer:
            pd.DataFrame(
                {
                    config.keyword_column: ["品牌词"],
                    config.keyword_category_column: ["品牌"],
                }
            ).to_excel(writer, sheet_name=config.keyword_tag_sheet, index=False)
            pd.DataFrame(
                {
                    config.audience_name_column: ["宝妈"],
                    config.audience_category_column: ["人群"],
                }
            ).to_excel(writer, sheet_name=config.audience_tag_sheet, index=False)
            pd.DataFrame(
                {
                    config.sku_match_id_column: ["1001"],
                    config.sku_category_column: ["SKU分类"],
                    config.sku_name_column: ["商品A"],
                }
            ).to_excel(writer, sheet_name=config.sku_tag_sheet, index=False)

        source_bytes = source_buffer.getvalue()
        tag_bytes = tag_buffer.getvalue()
        payloads = load_tag_validation_payloads(
            source_bytes,
            "source.xlsx",
            md5(source_bytes).hexdigest(),
            tag_bytes,
            "tag.xlsx",
            md5(tag_bytes).hexdigest(),
        )

        self.assertFalse(payloads.keyword.tree_df.empty)
        self.assertFalse(payloads.audience.tree_df.empty)
        self.assertFalse(payloads.sku.tree_df.empty)
        self.assertIn("品牌||品牌词", payloads.keyword.tree_df["path"].tolist())
        self.assertIn("人群||宝妈", payloads.audience.tree_df["path"].tolist())
        self.assertIn("SKU分类||1001", payloads.sku.tree_df["path"].tolist())
        keyword_child = payloads.keyword.tree_df.loc[
            payloads.keyword.tree_df["path"] == "品牌||品牌词"
        ].iloc[0]
        self.assertEqual(keyword_child[config.display_keyword_cost_column], 15.0)

    def test_config_uses_new_jd_source_and_tag_sheets(self) -> None:
        config = AppConfig()

        self.assertEqual(
            config.required_source_sheets,
            {
                "keyword_fact": "关键词数据源",
                "audience_fact": "人群数据源",
                "sku_fact": "站内外数据源",
            },
        )
        self.assertEqual(
            config.required_tag_sheets,
            {
                "keyword_tag": "关键词打标",
                "audience_tag": "人群打标",
                "sku_tag": "商品打标",
            },
        )
        self.assertEqual(
            config.source_usecols["keyword_fact"],
            [config.keyword_column, config.keyword_cost_column],
        )
        self.assertEqual(
            config.tag_usecols["sku_tag"],
            [
                config.sku_match_id_column,
                config.sku_category_column,
                config.sku_name_column,
            ],
        )

    def test_build_keyword_dataset_uses_keyword_tag_table(self) -> None:
        config = AppConfig()
        tables = {
            "keyword_fact": pd.DataFrame(
                {
                    config.keyword_column: ["婴幼儿奶粉", "未打标词"],
                    config.keyword_cost_column: [100, 20],
                }
            ),
            "keyword_tag": pd.DataFrame(
                {
                    config.keyword_column: ["婴幼儿奶粉"],
                    config.keyword_category_column: ["类目词"],
                }
            ),
        }

        result = build_keyword_dataset(tables, config)

        self.assertEqual(
            list(result.columns),
            [
                config.display_keyword_category_column,
                config.keyword_column,
                config.display_keyword_cost_column,
            ],
        )
        self.assertEqual(result.iloc[0][config.display_keyword_category_column], "类目词")
        self.assertEqual(
            result.iloc[1][config.display_keyword_category_column],
            config.blank_category,
        )
        self.assertEqual(result[config.display_keyword_cost_column].tolist(), [100, 20])

    def test_build_audience_dataset_uses_audience_tag_table(self) -> None:
        config = AppConfig()
        tables = {
            "audience_fact": pd.DataFrame(
                {
                    config.audience_name_column: ["A1-竞品兴趣", "未打标人群"],
                    config.audience_cost_column: [80, 30],
                }
            ),
            "audience_tag": pd.DataFrame(
                {
                    config.audience_name_column: ["A1-竞品兴趣"],
                    config.audience_category_column: ["A1-行业兴趣"],
                }
            ),
        }

        result = build_audience_dataset(tables, config)

        self.assertEqual(
            list(result.columns),
            [
                config.display_audience_category_column,
                config.audience_name_column,
                config.display_audience_cost_column,
            ],
        )
        self.assertEqual(result.iloc[0][config.display_audience_category_column], "A1-行业兴趣")
        self.assertEqual(
            result.iloc[1][config.display_audience_category_column],
            config.blank_category,
        )
        self.assertEqual(result[config.display_audience_cost_column].tolist(), [80, 30])

    def test_build_sku_dataset_uses_product_tag_table(self) -> None:
        config = AppConfig()
        tables = {
            "sku_fact": pd.DataFrame(
                {
                    config.sku_fact_id_column: ["1001", "1001", "9999"],
                    config.sku_cost_column: [100, 60, 20],
                }
            ),
            "sku_tag": pd.DataFrame(
                {
                    config.sku_match_id_column: ["1001", "1002"],
                    config.sku_category_column: ["启护箱装", "其他"],
                    config.sku_name_column: ["启赋蕴淳", "小饼干"],
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
                result[config.sku_fact_id_column] == "9999",
                config.display_sku_category_column,
            ].tolist(),
            [config.blank_category],
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
                config.display_sku_category_column: ["启护箱装", "启护箱装", config.blank_category],
                config.sku_fact_id_column: ["1001", "1001", "9999"],
                config.display_sku_cost_column: [100, 60, 20],
                config.sku_name_column: ["启赋蕴淳", "启赋蕴淳", ""],
            }
        )

        tree_df = build_sku_tree_payload(sku_df, [], config).tree_df

        parent_row = tree_df.loc[tree_df["path"] == "启护箱装"].iloc[0]
        child_row = tree_df.loc[tree_df["path"] == "启护箱装||1001"].iloc[0]

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
                },
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
