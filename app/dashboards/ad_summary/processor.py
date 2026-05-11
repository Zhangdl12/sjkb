"""
广告数据汇总处理器。

负责将多个原始数据表（广告、店铺、SKU、计划类型、目标）整合成一张完整的汇总表，
为后续的指标计算和UI展示提供高质量的数据支撑。

核心流程：
1. 分别预处理5个数据源表
2. 按业务逻辑进行多表关联
3. 填充缺失值和异常值
4. 添加时间维度列（年/季/月/周/日）
"""
import pandas as pd

from app.dashboards.ad_summary.config import AppConfig


class DataProcessingError(Exception):
    """广告数据汇总加工异常。"""


def build_ad_summary_dataset(
    tables: dict[str, pd.DataFrame],
    config: AppConfig,
) -> pd.DataFrame:
    """构建广告数据汇总数据集。
    
    将广告、店铺、SKU、计划类型、目标等多个数据源整合成一张完整的汇总表。
    
    Args:
        tables: 包含5个原始数据表的字典，键为 "ad", "shop", "sku", "plan", "target"
        config: 应用配置对象，包含所有列名和参数配置
    
    Returns:
        整合后的完整数据集 DataFrame
    
    Raises:
        DataProcessingError: 数据处理过程中出现错误时抛出
    """
    try:
        # 第1步：分别预处理5个数据源表
        ad_df = _build_ad_daily(tables["ad"], config)           # 广告日数据
        shop_df = _build_shop_daily(tables["shop"], config)     # 店铺日数据
        sku_df = _build_sku_mapping(tables["sku"], config)      # SKU映射表
        plan_df = _build_plan_mapping(tables["plan"], config)   # 计划类型映射表
        target_df = _build_target_daily(tables["target"], config)  # 目标数据

        # 第2步：多表关联合并
        # 广告数据 + 店铺数据（外连接，保留双方所有记录）
        merged_df = ad_df.merge(
            shop_df,
            on=[config.date_column, config.ad_sku_id_column],  # 按日期+商品ID关联
            how="outer",  # 外连接：即使某一方没有数据也保留
        )
        
        # 关联SKU信息（左连接，补充品类和品牌信息）
        merged_df = merged_df.merge(
            sku_df,
            left_on=config.ad_sku_id_column,
            right_on=config.sku_id_column,
            how="left",
        )
        
        # 关联计划类型信息（左连接，补充渠道信息）
        merged_df = merged_df.merge(
            plan_df,
            left_on=config.ad_plan_type_column,
            right_on=config.plan_type_column,
            how="left",
        )
        
        # 关联目标数据（左连接，补充销售目标）
        merged_df = merged_df.merge(
            target_df,
            left_on=[config.date_column, config.ad_sku_id_column],
            right_on=[config.target_date_column, config.target_sku_id_column],
            how="left",
        )

        # 第3步：填充分类字段的缺失值
        # 商品名称缺失 → 填充"未知"
        merged_df[config.product_name_column] = merged_df[
            config.ad_product_name_column
        ].fillna(config.unknown_text)
        
        # 品牌优先级：SKU品牌 > 店铺品牌 > "未知"
        merged_df[config.brand_column] = (
            merged_df["_sku_brand"]
            .fillna(merged_df[config.shop_brand_column])
            .fillna(config.unknown_text)
        )
        
        # 品类、渠道等分类字段缺失 → 填充"未知"
        for column in [
            config.category_column,
            config.channel_type_column,
            config.new_channel_column,
            config.plan_aggregate_column,
        ]:
            merged_df[column] = merged_df[column].fillna(config.unknown_text)

        # 目标GMV缺失 → 填充0（表示无目标）
        merged_df[config.shop_target_column] = merged_df[
            config.target_gmv_column
        ].fillna(0)
        
        # 第4步：填充数值型指标列的缺失值为0
        merged_df = _fill_metric_columns(merged_df, config)
        
        # 第5步：添加时间维度列（年/季/月/周/日）
        merged_df = _add_time_columns(merged_df, config)
        
        return merged_df
    except KeyError as exc:
        raise DataProcessingError(f"广告汇总缺少必要字段: {exc}") from exc
    except Exception as exc:
        raise DataProcessingError(f"广告汇总加工失败: {exc}") from exc


def _build_ad_daily(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """构建广告日数据表。
    
    将原始广告数据按日期、计划类型、商品ID进行分组聚合，生成每日的广告指标汇总。
    
    Args:
        df: 原始广告数据表
        config: 应用配置对象
    
    Returns:
        聚合后的广告日数据表，包含：日期、计划类型、商品ID、商品名称、广告费用、广告GMV、广告点击
    """
    ad_df = df.copy()
    
    # 转换日期格式：将字符串格式的日期（如 "20240101"）转换为 datetime 对象
    ad_df[config.date_column] = pd.to_datetime(
        ad_df[config.ad_date_column].astype(str), format="%Y%m%d", errors="coerce"
    )
    
    # 转换商品ID为数值类型，无效值转为 NaN
    ad_df[config.ad_sku_id_column] = pd.to_numeric(
        ad_df[config.ad_sku_id_column], errors="coerce"
    )
    
    # 按日期+计划类型+商品ID分组聚合
    return (
        ad_df.groupby(
            [config.date_column, config.ad_plan_type_column, config.ad_sku_id_column],
            dropna=False,  # 保留分组键中的 NaN 值
            as_index=False,  # 分组键作为普通列而非索引
        )
        .agg(
            {
                config.ad_product_name_column: "first",  # 取第一个商品名称
                config.ad_cost_column: "sum",            # 广告费用求和
                config.ad_gmv_column: "sum",             # 广告GMV求和
                config.ad_click_column: "sum",           # 广告点击量求和
            }
        )
    )


def _build_shop_daily(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """构建店铺日数据表。
    
    将原始店铺数据按日期、商品ID进行分组聚合，生成每日的店铺运营指标汇总。
    
    Args:
        df: 原始店铺数据表
        config: 应用配置对象
    
    Returns:
        聚合后的店铺日数据表，包含：日期、商品ID、PV、访客数、购买人数、订单数、商品数、店铺GMV、品牌
    """
    shop_df = df.copy()
    
    # 转换日期格式并标准化（去除时间部分，只保留日期）
    shop_df[config.date_column] = pd.to_datetime(
        shop_df[config.shop_date_column], errors="coerce"
    ).dt.normalize()
    
    # 转换商品ID为数值类型
    shop_df[config.ad_sku_id_column] = pd.to_numeric(
        shop_df[config.shop_sku_id_column], errors="coerce"
    )
    
    # 按日期+商品ID分组聚合
    return (
        shop_df.groupby([config.date_column, config.ad_sku_id_column], dropna=False, as_index=False)
        .agg(
            {
                config.shop_pv_column: "sum",              # PV（页面浏览量）求和
                config.shop_visitor_column: "sum",         # 访客数求和
                config.shop_buyer_column: "sum",           # 购买人数求和
                config.shop_order_count_column: "sum",     # 订单数求和
                config.shop_item_count_column: "sum",      # 商品数求和
                config.shop_gmv_column: "sum",             # 店铺GMV求和
                config.shop_brand_column: "first",         # 取第一个品牌名称
            }
        )
    )


def _build_sku_mapping(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """构建SKU映射表。
    
    提取商品ID与品类、品牌的映射关系，用于后续关联查询。
    
    Args:
        df: 原始SKU数据表
        config: 应用配置对象
    
    Returns:
        SKU映射表，包含：商品ID、品类、SKU品牌（去重后）
    """
    sku_df = df.copy()
    
    # 转换商品ID为数值类型
    sku_df[config.sku_id_column] = pd.to_numeric(sku_df[config.sku_id_column], errors="coerce")
    
    # 重命名列，避免与店铺品牌列冲突
    sku_df = sku_df.rename(columns={config.brand_column: "_sku_brand"})
    
    # 提取关键字段并去重（每个商品ID只保留一条记录）
    return sku_df[[config.sku_id_column, config.category_column, "_sku_brand"]].drop_duplicates(
        subset=[config.sku_id_column]
    )


def _build_plan_mapping(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """构建计划类型映射表。
    
    提取计划类型与渠道信息的映射关系，用于后续关联查询。
    
    Args:
        df: 原始计划类型数据表
        config: 应用配置对象
    
    Returns:
        计划类型映射表，包含：计划类型、计划聚合类型、新渠道、渠道类型（去重后）
    """
    return df[
        [
            config.plan_type_column,          # 计划类型
            config.plan_aggregate_column,     # 计划聚合类型
            config.new_channel_column,        # 新渠道
            config.channel_type_column,       # 渠道类型
        ]
    ].drop_duplicates(subset=[config.plan_type_column])  # 按计划类型去重


def _build_target_daily(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """构建目标日数据表。
    
    将原始目标数据按日期、商品ID进行分组聚合，生成每日的销售目标汇总。
    
    Args:
        df: 原始目标数据表
        config: 应用配置对象
    
    Returns:
        聚合后的目标日数据表，包含：日期、商品ID、目标GMV
    """
    target_df = df.copy()
    
    # 转换日期格式并标准化
    target_df[config.target_date_column] = pd.to_datetime(
        target_df[config.target_date_column], errors="coerce"
    ).dt.normalize()
    
    # 转换商品ID为数值类型
    target_df[config.target_sku_id_column] = pd.to_numeric(
        target_df[config.target_sku_id_column], errors="coerce"
    )
    
    # 按日期+商品ID聚合目标GMV
    return (
        target_df.groupby(
            [config.target_date_column, config.target_sku_id_column],
            dropna=False,
            as_index=False,
        )[config.target_gmv_column]
        .sum()
    )


def _fill_metric_columns(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """填充数值型指标列的缺失值为0。
    
    对于广告和店铺的数值型指标，缺失值统一填充为0，便于后续计算。
    
    Args:
        df: 待处理的数据表
        config: 应用配置对象
    
    Returns:
        填充后的数据表
    """
    metric_columns = [
        config.ad_cost_column,           # 广告费用
        config.ad_gmv_column,            # 广告GMV
        config.ad_click_column,          # 广告点击
        config.shop_pv_column,           # PV
        config.shop_visitor_column,      # 访客数
        config.shop_buyer_column,        # 购买人数
        config.shop_order_count_column,  # 订单数
        config.shop_item_count_column,   # 商品数
        config.shop_gmv_column,          # 店铺GMV
    ]
    
    # 将所有数值型指标列的缺失值填充为0
    for column in metric_columns:
        df[column] = df[column].fillna(0)
    
    return df


def _add_time_columns(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """添加时间维度列。
    
    从日期列衍生出年、季度、月份、周、日等多级时间维度，便于后续透视分析。
    
    Args:
        df: 待处理的数据表（必须包含日期列）
        config: 应用配置对象
    
    Returns:
        添加了时间维度列的数据表
    """
    result_df = df.copy()
    
    # 年份
    result_df[config.year_column] = result_df[config.date_column].dt.year
    
    # 季度（排序值 + 标签）
    result_df[config.quarter_sort_column] = result_df[config.date_column].dt.quarter
    result_df[config.quarter_label_column] = "Q" + result_df[config.quarter_sort_column].astype("Int64").astype(str)
    
    # 月份（排序值 + 标签）
    result_df[config.month_sort_column] = result_df[config.date_column].dt.month
    result_df[config.month_label_column] = "M" + result_df[config.month_sort_column].astype("Int64").astype(str)
    
    # 周（排序值 + 标签）
    result_df[config.week_sort_column] = result_df[config.date_column].dt.isocalendar().week.astype("Int64")
    result_df[config.week_label_column] = "W" + result_df[config.week_sort_column].astype(str)
    
    # 日（格式化标签，如 "2024/1/1"）
    result_df[config.day_label_column] = result_df[config.date_column].apply(_format_day_label)
    
    return result_df


def _format_day_label(value: pd.Timestamp) -> str:
    """格式化日期标签。
    
    将 datetime 对象格式化为 "年/月/日" 的字符串形式。
    
    Args:
        value: 日期时间对象
    
    Returns:
        格式化后的日期字符串，如 "2024/1/1"；如果输入为空则返回空字符串
    """
    if pd.isna(value):
        return ""
    return f"{value.year}/{value.month}/{value.day}"
