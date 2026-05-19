import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TestPageRadioKeys(unittest.TestCase):
    def test_main_view_radios_use_stable_keys(self) -> None:
        """验证各页面主视图 radio 都配置了稳定且互不冲突的 key。"""
        expected_keys = {
            ROOT / "pages" / "01_标签检验表.py": 'key="tag_validation_type_radio"',
            ROOT / "pages" / "02_广告数据汇总.py": 'key="ad_summary_period_radio"',
            ROOT / "pages" / "03_渠道分析.py": 'key="channel_analysis_view_radio"',
            ROOT / "pages" / "04_关键词分析.py": 'key="keyword_analysis_view_radio"',
            ROOT / "pages" / "05_人群分析.py": 'key="audience_analysis_view_radio"',
        }

        for path, expected_key in expected_keys.items():
            source = path.read_text(encoding="utf-8", errors="replace")
            self.assertIn(expected_key, source, msg=f"{path.name} 缺少稳定 radio key")


if __name__ == "__main__":
    unittest.main()
