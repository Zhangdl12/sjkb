"""CPS 分析数据归一化处理。"""
import pandas as pd

from app.dashboards.cps_analysis.config import AppConfig


class DataProcessingError(Exception):
    """CPS 分析数据加工异常。"""


def build_cps_analysis_dataset(
    tables: dict[str, pd.DataFrame],
    config: AppConfig,
) -> pd.DataFrame:
    """构建 CPS 分析统一明细表。

    Args:
        tables: 已读取的业务数据源和打标表，必须包含 cps 和 sku_tag。
        config: CPS 分析配置，提供工作表、字段和占位文本。

    Returns:
        完成商品打标、金额归一化和时间字段补充的 CPS 明细表。
    """
    try:
        cps_df = tables["cps"].copy()
        sku_map = _build_sku_mapping(tables["sku_tag"], config)

        # 商品编号是 CPS 事实表和商品打标表的关联键，先统一成文本格式再 merge。
        cps_df[config.sku_column] = _normalize_key(cps_df[config.sku_column])
        cps_df[config.leader_column] = cps_df[config.leader_column].map(_normalize_text)
        cps_df[config.leader_column] = cps_df[config.leader_column].replace("", config.unknown_text)
        cps_df[config.date_column] = _parse_date(cps_df[config.date_source_column])
        cps_df[config.display_commission_base_column] = pd.to_numeric(
            cps_df[config.commission_base_column],
            errors="coerce",
        ).fillna(0.0)
        cps_df[config.display_total_commission_column] = pd.to_numeric(
            cps_df[config.total_commission_column],
            errors="coerce",
        ).fillna(0.0)

        merged_df = cps_df.merge(
            sku_map,
            left_on=config.sku_column,
            right_on="_sku_key",
            how="left",
        )
        merged_df = _fill_tag_dimensions(merged_df, config)
        merged_df = _add_time_columns(merged_df, config)
        return merged_df[
            [
                config.sku_column,
                config.date_column,
                config.year_column,
                config.quarter_label_column,
                config.quarter_sort_column,
                config.month_label_column,
                config.month_sort_column,
                config.week_label_column,
                config.week_sort_column,
                config.day_label_column,
                config.leader_column,
                config.product_name_column,
                config.brand_column,
                config.display_commission_base_column,
                config.display_total_commission_column,
            ]
        ]
    except KeyError as exc:
        raise DataProcessingError(f"CPS分析缺少必要字段: {exc}") from exc
    except Exception as exc:
        raise DataProcessingError(f"CPS分析加工失败: {exc}") from exc


def _build_sku_mapping(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """生成 SKU 到商品名称和品牌的去重映射表。

    Args:
        df: 商品打标表。
        config: CPS 分析配置。

    Returns:
        带标准化 SKU 关联键的商品映射表。
    """
    mapping_df = df[
        [
            config.sku_id_column,
            config.product_name_column,
            config.brand_column,
        ]
    ].copy()
    mapping_df["_sku_key"] = _normalize_key(mapping_df[config.sku_id_column])
    mapping_df[config.product_name_column] = mapping_df[config.product_name_column].map(_normalize_text)
    mapping_df[config.brand_column] = mapping_df[config.brand_column].map(_normalize_text)
    return mapping_df.drop_duplicates(subset=["_sku_key"])


def _fill_tag_dimensions(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """填充商品打标维度，未匹配或空值统一显示为“未知”。

    Args:
        df: CPS 明细和商品映射表 merge 后的数据。
        config: CPS 分析配置。

    Returns:
        商品名称、品牌已完成兜底填充的数据。
    """
    result_df = df.copy()
    for column in [config.product_name_column, config.brand_column]:
        result_df[column] = result_df[column].map(_normalize_text).replace("", config.unknown_text)
    return result_df.drop(columns=["_sku_key", config.sku_id_column], errors="ignore")


def _add_time_columns(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """基于下单日期补充年、季度、月、周、日字段。

    Args:
        df: 已解析 Date 字段的 CPS 明细。
        config: CPS 分析配置。

    Returns:
        补齐时间筛选字段后的明细。
    """
    result_df = df.copy()
    result_df[config.year_column] = result_df[config.date_column].dt.year.astype("Int64")
    result_df[config.quarter_sort_column] = result_df[config.date_column].dt.quarter.astype("Int64")
    result_df[config.quarter_label_column] = "Q" + result_df[config.quarter_sort_column].astype(str)
    result_df[config.month_sort_column] = result_df[config.date_column].dt.month.astype("Int64")
    result_df[config.month_label_column] = "M" + result_df[config.month_sort_column].astype(str)
    result_df[config.week_sort_column] = result_df[config.date_column].dt.isocalendar().week.astype("Int64")
    result_df[config.week_label_column] = "W" + result_df[config.week_sort_column].astype(str)
    result_df[config.day_label_column] = result_df[config.date_column].apply(_format_day_label)
    return result_df


def _parse_date(series: pd.Series) -> pd.Series:
    """兼容 YYYYMMDD 数字、字符串和日期对象。

    Args:
        series: CPS 数据源中的下单日期列。

    Returns:
        归一化到自然日的 pandas datetime 序列。
    """
    text = series.astype("string").str.strip()
    compact = text.str.fullmatch(r"\d{8}", na=False)

    # pandas 在同一列混合 20250101 和 2025/1/1 时可能按首个格式推断，
    # 因此这里把紧凑数字日期和普通日期分开解析，避免合法日期被解析成 NaT。
    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    result.loc[compact] = pd.to_datetime(text.loc[compact], format="%Y%m%d", errors="coerce")
    result.loc[~compact] = pd.to_datetime(text.loc[~compact], errors="coerce")
    return result.dt.normalize()


def _normalize_key(series: pd.Series) -> pd.Series:
    """统一 Excel 关联键格式。

    Args:
        series: SKU 或其他 Excel 关联键序列。

    Returns:
        去掉前后空格和数字文本“.0”后缀的字符串序列。
    """
    return series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True).fillna("")


def _normalize_text(value: object) -> str:
    """统一文本字段格式。

    Args:
        value: 任意来源的单元格值。

    Returns:
        去除前后空格后的文本；空值返回空字符串。
    """
    if pd.isna(value):
        return ""
    return str(value).strip()


def _format_day_label(value: pd.Timestamp) -> str:
    """把日期转成页面展示的 YYYY/M/D 文本。

    Args:
        value: pandas 时间戳。

    Returns:
        页面展示用日期文本；无效日期返回空字符串。
    """
    if pd.isna(value):
        return ""
    return f"{value.year}/{value.month}/{value.day}"
