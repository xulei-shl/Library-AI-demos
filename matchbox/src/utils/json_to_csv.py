# -*- coding: utf-8 -*-
"""
JSON 结果导出到 CSV 工具模块。

功能：
- 扫描指定目录下的所有 JSON 文件
- 区分系列 JSON（S_ 开头）和对象 JSON
- 过滤掉所有 meta 字段（*_meta, consensus_meta 等）
- 对象 JSON 的 series 节点只提取 name 和 id
- 分别导出到不同的 CSV 文件
"""
import os
import json
import csv
from typing import Any, Dict, List, Optional
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)


def is_meta_field(field_name: str) -> bool:
    """
    判断是否为 meta 字段。

    Args:
        field_name: 字段名称

    Returns:
        是否为 meta 字段
    """
    return field_name.endswith('_meta') or field_name == 'consensus_meta' or field_name == 'reasoning'


def filter_meta_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    过滤掉所有 meta 字段。

    Args:
        data: 原始数据字典

    Returns:
        过滤后的数据字典
    """
    return {k: v for k, v in data.items() if not is_meta_field(k)}


def extract_series_info(series_data: Any) -> Optional[Dict[str, str]]:
    """
    从 series 节点提取 name 和 id。

    Args:
        series_data: series 数据（可能是字典或其他类型）

    Returns:
        包含 series_name 和 series_id 的字典，如果无法提取则返回 None
    """
    if not isinstance(series_data, dict):
        return None

    result = {}
    if 'name' in series_data:
        result['series_name'] = series_data['name']
    if 'id' in series_data:
        result['series_id'] = series_data['id']

    return result if result else None


def flatten_value(value: Any) -> str:
    """
    将复杂类型转换为字符串用于 CSV 输出。

    Args:
        value: 任意类型的值

    Returns:
        字符串表示
    """
    if value is None:
        return ''
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def process_series_json(json_data: Dict[str, Any]) -> Dict[str, str]:
    """
    处理系列 JSON 数据，过滤 meta 字段并展平为一行数据。

    Args:
        json_data: 系列 JSON 数据

    Returns:
        展平后的字典，键值对都是字符串
    """
    filtered = filter_meta_fields(json_data)
    return {k: flatten_value(v) for k, v in filtered.items()}


def process_object_json(json_data: Dict[str, Any]) -> Dict[str, str]:
    """
    处理对象 JSON 数据，过滤 meta 字段，提取 series 信息。

    Args:
        json_data: 对象 JSON 数据

    Returns:
        展平后的字典，键值对都是字符串
    """
    # 过滤 meta 字段
    filtered = filter_meta_fields(json_data)

    # 处理 series 节点
    series_info = None
    if 'series' in filtered:
        series_info = extract_series_info(filtered['series'])
        # 移除原 series 节点
        filtered.pop('series')

    # 展平数据
    result = {k: flatten_value(v) for k, v in filtered.items()}

    # 添加 series 信息
    if series_info:
        result.update(series_info)

    return result


def is_series_json(filename: str) -> bool:
    """
    判断文件是否为系列 JSON（S_ 开头）。

    Args:
        filename: 文件名

    Returns:
        是否为系列 JSON
    """
    return os.path.basename(filename).startswith('S_')


def collect_json_files(directory: str) -> tuple[List[str], List[str]]:
    """
    收集目录下的所有 JSON 文件，分为系列和对象两类。

    Args:
        directory: 目标目录路径

    Returns:
        (系列JSON文件列表, 对象JSON文件列表)
    """
    series_files = []
    object_files = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                if is_series_json(file):
                    series_files.append(file_path)
                else:
                    object_files.append(file_path)

    return series_files, object_files


def write_to_csv(data_rows: List[Dict[str, str]], output_path: str) -> None:
    """
    将数据行写入 CSV 文件，并进行额外处理：
    1. 增加固定列 rdf:type = Product, VisualArtwork
    2. 增加固定列 dct:type = MatchBox
    3. 文本替换：删除所有 `[`, `]`, `"`

    Args:
        data_rows: 数据行列表
        output_path: 输出文件路径
    """
    if not data_rows:
        logger.warning(f"没有数据可写入 CSV: {output_path}")
        return

    processed_rows: List[Dict[str, str]] = []
    for row in data_rows:
        # 复制以避免副作用，并增加固定列
        new_row = dict(row)
        new_row["rdf:type"] = "Product, VisualArtwork"
        new_row["dct:type"] = "MatchBox"

        # 文本处理：删除 `[` `]` `"`
        cleaned_row: Dict[str, str] = {}
        for k, v in new_row.items():
            if v is None:
                cleaned_row[k] = ""
            else:
                s = v if isinstance(v, str) else str(v)
                s = s.replace("[", "").replace("]", "").replace("\"", "")
                cleaned_row[k] = s
        processed_rows.append(cleaned_row)

    # 收集所有字段名（保持顺序）
    all_fields = []
    seen_fields = set()
    for row in processed_rows:
        for field in row.keys():
            if field not in seen_fields:
                all_fields.append(field)
                seen_fields.add(field)

    # 写入 CSV
    # 强制使用 UTF-8 编码（无 BOM）
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_fields)
        writer.writeheader()
        writer.writerows(processed_rows)

    logger.info(f"CSV 文件已生成: {output_path}, 共 {len(processed_rows)} 行")


def export_json_to_csv(
    json_directory: str,
    series_csv_path: Optional[str] = None,
    object_csv_path: Optional[str] = None
) -> tuple[int, int]:
    """
    导出 JSON 文件到 CSV。

    Args:
        json_directory: JSON 文件所在目录
        series_csv_path: 系列 CSV 输出路径（默认为 json_directory/series_results.csv）
        object_csv_path: 对象 CSV 输出路径（默认为 json_directory/object_results.csv）

    Returns:
        (系列记录数, 对象记录数)
    """
    # 设置默认输出路径
    if series_csv_path is None:
        series_csv_path = os.path.join(json_directory, 'series_results.csv')
    if object_csv_path is None:
        object_csv_path = os.path.join(json_directory, 'object_results.csv')

    logger.info(f"开始导出 JSON 到 CSV: {json_directory}")

    # 收集 JSON 文件
    series_files, object_files = collect_json_files(json_directory)
    logger.info(f"发现 {len(series_files)} 个系列 JSON, {len(object_files)} 个对象 JSON")

    # 处理系列 JSON
    series_rows = []
    for file_path in series_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                row = process_series_json(json_data)
                # 添加文件名以便追溯
                row['_source_file'] = os.path.basename(file_path)
                series_rows.append(row)
        except Exception as e:
            logger.error(f"处理系列 JSON 失败: {file_path}, 错误: {e}")

    # 处理对象 JSON
    object_rows = []
    for file_path in object_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                row = process_object_json(json_data)
                # 添加文件名以便追溯
                row['_source_file'] = os.path.basename(file_path)
                object_rows.append(row)
        except Exception as e:
            logger.error(f"处理对象 JSON 失败: {file_path}, 错误: {e}")

    # 写入 CSV
    write_to_csv(series_rows, series_csv_path)
    write_to_csv(object_rows, object_csv_path)

    logger.info(f"导出完成: 系列 {len(series_rows)} 条, 对象 {len(object_rows)} 条")
    return len(series_rows), len(object_rows)


if __name__ == "__main__":
    # 命令行直接运行示例
    import sys

    if len(sys.argv) < 2:
        print("用法: python json_to_csv.py <json_directory> [series_csv_path] [object_csv_path]")
        sys.exit(1)

    json_dir = sys.argv[1]
    series_csv = sys.argv[2] if len(sys.argv) > 2 else None
    object_csv = sys.argv[3] if len(sys.argv) > 3 else None

    export_json_to_csv(json_dir, series_csv, object_csv)
