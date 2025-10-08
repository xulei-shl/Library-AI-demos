# -*- coding: utf-8 -*-
"""
Excel 数据读取工具
- 从项目根目录的 metadata.xlsx 读取“编号”列，返回 row_id 列表
"""
from typing import List
import os

try:
    import pandas as pd
except ImportError:
    pd = None

def load_row_ids(excel_path: str, id_column: str) -> List[str]:
    """
    读取 Excel 并返回编号列表

    Args:
        excel_path: Excel 文件路径
        id_column: 编号列名（如“编号”）

    Returns:
        List[str]: 编号列表，忽略空值

    Raises:
        RuntimeError: 当未安装 pandas 或文件不存在时抛出
    """
    if pd is None:
        raise RuntimeError("未安装 pandas，无法读取 Excel。请安装 pandas。")
    if not os.path.exists(excel_path):
        raise RuntimeError(f"Excel 文件不存在：{excel_path}")
    df = pd.read_excel(excel_path)
    if id_column not in df.columns:
        raise RuntimeError(f"Excel 中缺少列：{id_column}")
    ids = [str(v).strip() for v in df[id_column].tolist() if str(v).strip()]
    return ids