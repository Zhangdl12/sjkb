import unittest

from app.core.page_state import ensure_page_radio_state


class TestPageState(unittest.TestCase):
    def test_page_radio_state_uses_default_when_state_missing(self) -> None:
        """验证页面主 radio 首次进入时会写入声明的默认值。"""
        state = {}

        result = ensure_page_radio_state(["季度汇总", "月度汇总"], "period_radio", "季度汇总", state)

        self.assertEqual(result, "季度汇总")
        self.assertEqual(state["period_radio"], "季度汇总")
        self.assertEqual(state["period_radio__persistent_value"], "季度汇总")

    def test_page_radio_state_keeps_current_widget_value(self) -> None:
        """验证页面主 radio 当前值有效时不会被默认值覆盖。"""
        state = {
            "period_radio": "月度汇总",
            "period_radio__persistent_value": "季度汇总",
        }

        result = ensure_page_radio_state(["季度汇总", "月度汇总"], "period_radio", "季度汇总", state)

        self.assertEqual(result, "月度汇总")
        self.assertEqual(state["period_radio__persistent_value"], "月度汇总")

    def test_page_radio_state_restores_persistent_value_when_widget_key_missing(self) -> None:
        """验证 widget 状态被中途 rerun 清理后，可用持久状态恢复当前选择。"""
        state = {"period_radio__persistent_value": "月度汇总"}

        result = ensure_page_radio_state(["季度汇总", "月度汇总"], "period_radio", "季度汇总", state)

        self.assertEqual(result, "月度汇总")
        self.assertEqual(state["period_radio"], "月度汇总")

    def test_page_radio_state_falls_back_when_old_value_invalid(self) -> None:
        """验证旧状态不在候选项内时会回退到声明默认值。"""
        state = {
            "period_radio": "年度汇总",
            "period_radio__persistent_value": "年度汇总",
        }

        result = ensure_page_radio_state(["季度汇总", "月度汇总"], "period_radio", "季度汇总", state)

        self.assertEqual(result, "季度汇总")


if __name__ == "__main__":
    unittest.main()
