"""CPS 分析页面的工作表、字段和展示配置。"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppConfig:
    """集中维护 CPS 分析使用的 Excel 表名、字段名和展示列。

    Args:
        无。当前配置全部使用 dataclass 默认值初始化。

    Returns:
        配置对象本身，供数据处理、服务层和 UI 层复用。
    """

    # ===== 业务数据源工作表 =====
    cps_sheet: str = "CPS数据源"

    required_sheets: dict[str, str] = field(
        default_factory=lambda: {
            "cps": "CPS数据源",
        }
    )

    # ===== 打标工作表 =====
    sku_tag_sheet: str = "商品打标"

    required_tag_sheets: dict[str, str] = field(
        default_factory=lambda: {
            "sku_tag": "商品打标",
        }
    )

    # ===== CPS 原始字段 =====
    sku_column: str = "商品编号"
    date_source_column: str = "下单日期"
    leader_column: str = "所属计划/活动"
    commission_base_column: str = "计佣金额"
    total_commission_column: str = "总佣金"

    # ===== 商品打标字段 =====
    sku_id_column: str = "京东skuID"
    product_name_column: str = "商品名称"
    brand_column: str = "品牌"

    # ===== 归一化时间字段 =====
    date_column: str = "Date"
    year_column: str = "年"
    quarter_label_column: str = "季度"
    quarter_sort_column: str = "季度排序"
    month_label_column: str = "月"
    month_sort_column: str = "月排序值"
    week_label_column: str = "周"
    week_sort_column: str = "周排序值"
    day_label_column: str = "日"

    # ===== 展示指标字段 =====
    display_commission_base_column: str = "tk计佣金额"
    display_total_commission_column: str = "tk总佣金"
    commission_rate_column: str = "佣金比例"

    # ===== 通用占位 =====
    unknown_text: str = "未知"

    tree_columns: list[str] = field(
        default_factory=lambda: [
            "所属计划/活动",
            "日",
            "商品名称",
            "tk计佣金额",
            "tk总佣金",
            "佣金比例",
        ]
    )

    @property
    def source_usecols(self) -> dict[str, list[str]]:
        """返回 CPS 分析事实表的最小读取列。

        Returns:
            业务数据源别名到字段列表的映射。
        """
        return {
            "cps": [
                self.sku_column,
                self.date_source_column,
                self.leader_column,
                self.commission_base_column,
                self.total_commission_column,
            ],
        }

    @property
    def tag_usecols(self) -> dict[str, list[str]]:
        """返回商品打标表的最小读取列。

        Returns:
            打标表别名到字段列表的映射。
        """
        return {
            "sku_tag": [
                self.sku_id_column,
                self.product_name_column,
                self.brand_column,
            ],
        }


DEFAULT_CONFIG = AppConfig()
