import unittest

import pandas as pd

from app.core.filters import (
    FilterField,
    _build_filter_state_keys,
    _clear_filter_state_keys,
    _resolve_reset_widget_value,
    _normalize_filter_selection,
    _normalize_selected_values,
    _resolve_single_default,
    apply_filters,
)


class TestFilters(unittest.TestCase):
    def test_resolve_single_default_uses_previous_when_still_valid(self) -> None:
        """验证单选控件在旧值仍然有效时继续沿用旧值。"""
        result = _resolve_single_default([2024, 2025, 2026], 2025, default_latest=True)

        self.assertEqual(result, 2025)

    def test_resolve_single_default_falls_back_to_latest(self) -> None:
        """验证声明为 default_latest 的单选控件会回退到最新值。"""
        result = _resolve_single_default([2024, 2025, 2026], 2023, default_latest=True)

        self.assertEqual(result, 2026)

    def test_normalize_selected_values_supports_single_value_and_list(self) -> None:
        """验证筛选值归一化同时支持单值、列表和值缺失场景。"""
        self.assertEqual(_normalize_selected_values(2025), [2025])
        self.assertEqual(_normalize_selected_values([2025, 2026]), [2025, 2026])
        self.assertEqual(_normalize_selected_values(None), [])

    def test_apply_filters_supports_single_select_value(self) -> None:
        """验证 apply_filters 能正确处理单选控件返回的标量值。"""
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
        """验证多选控件全选时会被视为未激活筛选条件。"""
        field = FilterField("渠道类型", default_all=True)

        result = _normalize_filter_selection(["RTB", "CPS"], ["RTB", "CPS"], field)

        self.assertEqual(result, [])

    def test_normalize_filter_selection_keeps_partial_selection_active(self) -> None:
        """验证多选控件只选中部分值时会保留真实筛选条件。"""
        field = FilterField("渠道类型", default_all=True)

        result = _normalize_filter_selection(["RTB"], ["RTB", "CPS"], field)

        self.assertEqual(result, ["RTB"])

    def test_build_filter_state_keys_uses_key_prefix_and_field_columns(self) -> None:
        """验证筛选器 state key 会按页面前缀和字段名稳定生成。"""
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
        """验证清理函数只会删除当前页面对应的筛选状态。"""
        mock_state = {
            "广告数据汇总_年": 2026,
            "广告数据汇总_季度": ["Q1"],
            "渠道分析_年": 2025,
            "other_key": "keep",
        }

        _clear_filter_state_keys(
            ["广告数据汇总_年", "广告数据汇总_季度"],
            mock_state,
        )

        self.assertNotIn("广告数据汇总_年", mock_state)
        self.assertNotIn("广告数据汇总_季度", mock_state)
        self.assertEqual(mock_state["渠道分析_年"], 2025)
        self.assertEqual(mock_state["other_key"], "keep")

    def test_resolve_reset_widget_value_returns_all_options_for_default_all_multiselect(self) -> None:
        """验证默认全选的多选控件在重置后仍会恢复为全选。"""
        field = FilterField("季度", default_all=True)

        result = _resolve_reset_widget_value(["Q1", "Q2"], field, previous_selection=[])

        self.assertEqual(result, ["Q1", "Q2"])

    def test_resolve_reset_widget_value_returns_empty_for_non_default_multiselect(self) -> None:
        """验证非默认全选的多选控件在重置后会恢复为空。"""
        field = FilterField("季度", default_all=False)

        result = _resolve_reset_widget_value(["Q1", "Q2"], field, previous_selection=[])

        self.assertEqual(result, [])

    def test_resolve_reset_widget_value_resets_single_select_to_latest_default(self) -> None:
        """验证单选控件重置后会回到声明的最新默认值，而不是保留旧值。"""
        field = FilterField("年", control="single_select", default_latest=True)

        result = _resolve_reset_widget_value([2024, 2025, 2026], field, previous_selection=2025)

        self.assertEqual(result, 2026)

    def test_resolve_reset_widget_value_resets_single_select_to_first_option(self) -> None:
        """验证普通单选控件重置后会回到首个候选项。"""
        field = FilterField("季度", control="single_select", default_latest=False)

        result = _resolve_reset_widget_value(["Q1", "Q2"], field, previous_selection="Q2")

        self.assertEqual(result, "Q1")


if __name__ == "__main__":
    unittest.main()
