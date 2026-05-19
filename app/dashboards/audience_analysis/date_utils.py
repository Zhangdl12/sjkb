"""人群分析日期和关联键工具函数。"""

import pandas as pd


def add_time_columns(df: pd.DataFrame, config) -> pd.DataFrame:
    """基于 Date 补充年、季度、月、周、日筛选字段。

    Args:
        df: 已带 Date 列的人群分析明细表。
        config: 人群分析字段配置。

    Returns:
        已补充时间维度字段的 DataFrame。
    """

    result_df = df.copy()
    result_df[config.year_column] = result_df[config.date_column].dt.year.astype("Int64")
    result_df[config.quarter_sort_column] = result_df[config.date_column].dt.quarter.astype("Int64")
    result_df[config.quarter_label_column] = "Q" + result_df[config.quarter_sort_column].astype(str)
    result_df[config.month_sort_column] = result_df[config.date_column].dt.month.astype("Int64")
    result_df[config.month_label_column] = "M" + result_df[config.month_sort_column].astype(str)
    result_df[config.week_sort_column] = result_df[config.date_column].dt.isocalendar().week.astype("Int64")
    result_df[config.week_label_column] = "W" + result_df[config.week_sort_column].astype(str)
    result_df[config.day_label_column] = result_df[config.date_column].apply(format_day_label)
    return result_df


def parse_date(series: pd.Series) -> pd.Series:
    """兼容 YYYYMMDD 数字、字符串和日期对象。

    Args:
        series: 原始日期序列。

    Returns:
        标准化到日期零点的 pandas 时间序列。
    """

    text = series.astype("string").str.strip()
    compact = text.str.fullmatch(r"\d{8}", na=False)
    result = pd.to_datetime(text, errors="coerce")
    result.loc[compact] = pd.to_datetime(text.loc[compact], format="%Y%m%d", errors="coerce")
    return result.dt.normalize()


def normalize_key(series: pd.Series) -> pd.Series:
    """统一 Excel 关联键格式。

    Args:
        series: 需要归一化的关联键序列。

    Returns:
        去除前后空格和数字文本 `.0` 后缀的字符串序列。
    """

    return series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True).fillna("")


def format_day_label(value: pd.Timestamp) -> str:
    """把日期转成页面展示的 YYYY/M/D 文本。

    Args:
        value: pandas 日期值。

    Returns:
        页面展示用日期文本，空日期返回空字符串。
    """

    if pd.isna(value):
        return ""
    return f"{value.year}/{value.month}/{value.day}"
