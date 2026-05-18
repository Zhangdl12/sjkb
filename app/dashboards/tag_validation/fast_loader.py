"""标签检验表专用的 xlsx 流式汇总读取器。"""
from collections import defaultdict
from dataclasses import dataclass
from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import pandas as pd

from app.core.loader import DataLoadError


MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
ROW_TAG = f"{MAIN_NS}row"
CELL_TAG = f"{MAIN_NS}c"
VALUE_TAG = f"{MAIN_NS}v"
INLINE_STRING_TAG = f"{MAIN_NS}is"
TEXT_TAG = f"{MAIN_NS}t"


@dataclass(frozen=True)
class CostSummarySpec:
    """单张事实表配置；sheet_name 是表名，key_column 是汇总键，cost_column 是费用列。"""

    sheet_name: str
    key_column: str
    cost_column: str


def load_cost_summary_sheets(
    file_bytes: bytes,
    specs: dict[str, CostSummarySpec],
) -> dict[str, pd.DataFrame]:
    """流式汇总多张事实表；Args: file_bytes 为 xlsx 字节，specs 为别名配置；Returns: 汇总小表字典。"""
    try:
        with ZipFile(BytesIO(file_bytes)) as workbook_zip:
            shared_strings = _read_shared_strings(workbook_zip)
            sheet_paths = _read_sheet_paths(workbook_zip)
            _validate_required_sheets(sheet_paths, specs)

            return {
                alias: _parse_cost_summary_sheet(
                    workbook_zip,
                    sheet_paths[spec.sheet_name],
                    spec,
                    shared_strings,
                )
                for alias, spec in specs.items()
            }
    except DataLoadError:
        raise
    except Exception as exc:
        raise DataLoadError(f"流式读取标签检验事实表失败: {exc}") from exc


def _validate_required_sheets(
    sheet_paths: dict[str, str],
    specs: dict[str, CostSummarySpec],
) -> None:
    """校验必需工作表；Args: sheet_paths 为表名路径映射，specs 为读取配置；Returns: None。"""
    missing_sheets = [
        spec.sheet_name for spec in specs.values() if spec.sheet_name not in sheet_paths
    ]
    if missing_sheets:
        raise DataLoadError(f"缺少必需的工作表: {', '.join(missing_sheets)}")


def _read_shared_strings(workbook_zip: ZipFile) -> list[str]:
    """读取共享字符串；Args: workbook_zip 为 xlsx zip；Returns: 按索引存储的字符串列表。"""
    if "xl/sharedStrings.xml" not in workbook_zip.namelist():
        return []

    shared_strings: list[str] = []
    with workbook_zip.open("xl/sharedStrings.xml") as shared_file:
        for _, element in ET.iterparse(shared_file, events=("end",)):
            if element.tag != f"{MAIN_NS}si":
                continue

            # 一个共享字符串可能由多个 <t> 片段组成，需拼接完整文本。
            shared_strings.append(
                "".join(text_node.text or "" for text_node in element.iter(TEXT_TAG))
            )
            element.clear()

    return shared_strings


def _read_sheet_paths(workbook_zip: ZipFile) -> dict[str, str]:
    """读取 sheet 路径；Args: workbook_zip 为 xlsx zip；Returns: 工作表名到 XML 路径映射。"""
    workbook_root = ET.fromstring(workbook_zip.read("xl/workbook.xml"))
    rel_root = ET.fromstring(workbook_zip.read("xl/_rels/workbook.xml.rels"))
    rel_targets = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rel_root
    }

    sheet_paths: dict[str, str] = {}
    sheets_element = workbook_root.find(f"{MAIN_NS}sheets")
    if sheets_element is None:
        raise DataLoadError("Excel 文件缺少 sheets 定义。")

    for sheet_element in sheets_element:
        sheet_name = sheet_element.attrib["name"]
        relation_id = sheet_element.attrib[f"{REL_NS}id"]
        target_path = rel_targets[relation_id]
        sheet_paths[sheet_name] = _normalize_zip_path(target_path)

    return sheet_paths


def _normalize_zip_path(target_path: str) -> str:
    """归一化 zip 路径；Args: target_path 为关系文件路径；Returns: xlsx 内部路径。"""
    if target_path.startswith("/"):
        return target_path.lstrip("/")
    if target_path.startswith("xl/"):
        return target_path
    return f"xl/{target_path}"


def _parse_cost_summary_sheet(
    workbook_zip: ZipFile,
    sheet_path: str,
    spec: CostSummarySpec,
    shared_strings: list[str],
) -> pd.DataFrame:
    """解析并汇总单表；Args: workbook_zip/sheet_path/spec/shared_strings 为解析上下文；Returns: 两列汇总表。"""
    key_col_index: int | None = None
    cost_col_index: int | None = None
    cost_by_key: dict[str, float] = defaultdict(float)

    with workbook_zip.open(sheet_path) as sheet_file:
        for _, row_element in ET.iterparse(sheet_file, events=("end",)):
            if row_element.tag != ROW_TAG:
                continue

            if key_col_index is None or cost_col_index is None:
                header_map = _read_header_map(row_element, shared_strings)
                if spec.key_column in header_map and spec.cost_column in header_map:
                    key_col_index = header_map[spec.key_column]
                    cost_col_index = header_map[spec.cost_column]
                row_element.clear()
                continue

            key_value, cost_value, has_selected_value = _read_fact_row(
                row_element,
                key_col_index,
                cost_col_index,
                shared_strings,
            )
            if has_selected_value:
                cost_by_key[key_value] += cost_value
            row_element.clear()

    if key_col_index is None or cost_col_index is None:
        raise DataLoadError(
            f"工作表 `{spec.sheet_name}` 缺少必要字段: "
            f"{spec.key_column}, {spec.cost_column}"
        )

    return pd.DataFrame(
        [
            {spec.key_column: key, spec.cost_column: cost}
            for key, cost in cost_by_key.items()
        ],
        columns=[spec.key_column, spec.cost_column],
    )


def _read_header_map(
    row_element: ET.Element,
    shared_strings: list[str],
) -> dict[str, int]:
    """读取表头映射；Args: row_element 为表头行，shared_strings 为共享字符串；Returns: 列名到列序号。"""
    header_map: dict[str, int] = {}
    for cell_element in row_element.iter(CELL_TAG):
        header_name = _normalize_text(_read_cell_value(cell_element, shared_strings))
        if header_name:
            header_map[header_name] = _column_index(cell_element.attrib.get("r", ""))
    return header_map


def _read_fact_row(
    row_element: ET.Element,
    key_col_index: int,
    cost_col_index: int,
    shared_strings: list[str],
) -> tuple[str, float, bool]:
    """读取一行目标值；Args: row_element 和目标列序号；Returns: 关联键、花费、是否读到目标格。"""
    key_value = ""
    cost_value = 0.0
    has_selected_value = False

    for cell_element in row_element.iter(CELL_TAG):
        column_index = _column_index(cell_element.attrib.get("r", ""))
        if column_index != key_col_index and column_index != cost_col_index:
            continue

        has_selected_value = True
        cell_value = _read_cell_value(cell_element, shared_strings)
        if column_index == key_col_index:
            key_value = _normalize_text(cell_value)
        else:
            cost_value = _to_float(cell_value)

    return key_value, cost_value, has_selected_value


def _read_cell_value(cell_element: ET.Element, shared_strings: list[str]) -> object:
    """读取单元格值；Args: cell_element 为单元格，shared_strings 为共享字符串；Returns: 原始值。"""
    cell_type = cell_element.attrib.get("t")
    if cell_type == "inlineStr":
        inline_element = cell_element.find(INLINE_STRING_TAG)
        if inline_element is None:
            return ""
        return "".join(text_node.text or "" for text_node in inline_element.iter(TEXT_TAG))

    value_element = cell_element.find(VALUE_TAG)
    if value_element is None or value_element.text is None:
        return ""

    raw_value = value_element.text
    if cell_type == "s":
        try:
            return shared_strings[int(raw_value)]
        except (IndexError, TypeError, ValueError):
            return ""
    return raw_value


def _column_index(cell_reference: str) -> int:
    """转换列序号；Args: cell_reference 如 A1/AA1；Returns: 1 基列序号。"""
    index = 0
    for char in cell_reference:
        if not char.isalpha():
            break
        index = index * 26 + ord(char.upper()) - 64
    return index


def _normalize_text(value: object) -> str:
    """统一文本；Args: value 为单元格值；Returns: 去空格且去掉 .0 后缀的字符串。"""
    text = "" if value is None else str(value).strip()
    if text.endswith(".0"):
        return text[:-2]
    return text


def _to_float(value: object) -> float:
    """转换费用；Args: value 为单元格值；Returns: float，无法转换时返回 0。"""
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
