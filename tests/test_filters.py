import unittest

import pandas as pd

from app.core.filters import (
    FilterField,
    _build_filter_state_keys,
    _clear_filter_state_keys,
    _build_preserved_single_select_state,
    _resolve_reset_widget_value,
    _normalize_filter_selection,
    _normalize_selected_values,
    _resolve_single_default,
    apply_filters,
)


class TestFilters(unittest.TestCase):
    def test_resolve_single_default_uses_previous_when_still_valid(self) -> None:
        result = _resolve_single_default([2024, 2025, 2026], 2025, default_latest=True)

        self.assertEqual(result, 2025)

    def test_resolve_single_default_falls_back_to_latest(self) -> None:
        result = _resolve_single_default([2024, 2025, 2026], 2023, default_latest=True)

        self.assertEqual(result, 2026)

    def test_normalize_selected_values_supports_single_value_and_list(self) -> None:
        self.assertEqual(_normalize_selected_values(2025), [2025])
        self.assertEqual(_normalize_selected_values([2025, 2026]), [2025, 2026])
        self.assertEqual(_normalize_selected_values(None), [])

    def test_apply_filters_supports_single_select_value(self) -> None:
        df = pd.DataFrame(
            {
                "年": [2024, 2025, 2026],
                "季度": ["Q1", "Q1", "Q2"],
            }
        )
        fields = (
            FilterField("年", control="single_select"),
            FilterField("季度"),
        )

        result = apply_filters(df, {"年": 2025, "季度": ["Q1"]}, fields)

        self.assertEqual(result["年"].tolist(), [2025])

    def test_normalize_filter_selection_treats_default_all_as_inactive(self) -> None:
        field = FilterField("渠道类型", default_all=True)

        result = _normalize_filter_selection(["RTB", "CPS"], ["RTB", "CPS"], field)

        self.assertEqual(result, [])

    def test_normalize_filter_selection_keeps_partial_selection_active(self) -> None:
        field = FilterField("渠道类型", default_all=True)

        result = _normalize_filter_selection(["RTB"], ["RTB", "CPS"], field)

        self.assertEqual(result, ["RTB"])

    def test_build_filter_state_keys_uses_key_prefix_and_field_columns(self) -> None:
        fields = (
            FilterField("年"),
            FilterField("季度"),
            FilterField("渠道类型"),
        )

        result = _build_filter_state_keys(fields, "广告数据汇总")

        self.assertEqual(
            result,
            [
                "广告数据汇总_年",
                "广告数据汇总_季度",
                "广告数据汇总_渠道类型",
            ],
        )

    def test_clear_filter_state_keys_only_removes_current_prefix(self) -> None:
        mock_state = {
            "广告数据汇总_年": 2026,
            "广告数据汇总_季度": ["Q1"],
            "素材分析_年": 2025,
            "other_key": "keep",
        }

        _clear_filter_state_keys(
            ["广告数据汇总_年", "广告数据汇总_季度"],
            mock_state,
        )

        self.assertNotIn("广告数据汇总_年", mock_state)
        self.assertNotIn("广告数据汇总_季度", mock_state)
        self.assertEqual(mock_state["素材分析_年"], 2025)
        self.assertEqual(mock_state["other_key"], "keep")

    def test_build_preserved_single_select_state_keeps_current_single_select_values(self) -> None:
        fields = (
            FilterField("年", control="single_select"),
            FilterField("季度"),
            FilterField("渠道类型"),
        )
        mock_state = {
            "广告数据汇总_年": 2025,
            "广告数据汇总_季度": ["Q1"],
            "广告数据汇总_渠道类型": ["RTB"],
        }

        result = _build_preserved_single_select_state(
            fields,
            "广告数据汇总",
            mock_state,
        )

        self.assertEqual(result, {"广告数据汇总_年": 2025})

    def test_resolve_reset_widget_value_returns_all_options_for_default_all_multiselect(self) -> None:
        field = FilterField("季度", default_all=True)

        result = _resolve_reset_widget_value(["Q1", "Q2"], field, previous_selection=[])

        self.assertEqual(result, ["Q1", "Q2"])

    def test_resolve_reset_widget_value_returns_empty_for_non_default_multiselect(self) -> None:
        field = FilterField("季度", default_all=False)

        result = _resolve_reset_widget_value(["Q1", "Q2"], field, previous_selection=[])

        self.assertEqual(result, [])

    def test_resolve_reset_widget_value_keeps_single_select_default(self) -> None:
        field = FilterField("年", control="single_select", default_latest=True)

        result = _resolve_reset_widget_value([2024, 2025, 2026], field, previous_selection=2025)

        self.assertEqual(result, 2025)


if __name__ == "__main__":
    unittest.main()
