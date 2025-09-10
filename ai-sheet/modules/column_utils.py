#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
列选择相关工具函数
支持Excel列选择和过滤功能
"""

import pandas as pd
from typing import Dict, List, Any, Tuple


def generate_filtered_preview(sheet_data: Dict[str, Any], selected_columns: List[str], preview_rows: int = 5) -> str:
    """生成按选中列过滤的预览数据"""
    if not selected_columns:
        return sheet_data['preview']
    
    try:
        df = sheet_data['data']
        if df.empty:
            return "*数据为空*"
        
        # 解析选中的列索引和保持原始字母标识
        column_indices = []
        original_column_letters = []  # 保存原始列字母标识
        
        for col_name in selected_columns:
            # 从 "A列-索书号" 格式中提取列索引
            if '列-' in col_name:
                # 提取列字母（支持A-Z）
                col_letter = col_name.split('列-')[0]
                if len(col_letter) == 1 and col_letter.isalpha():
                    col_index = ord(col_letter.upper()) - ord('A')
                    if 0 <= col_index < len(df.columns):
                        column_indices.append(col_index)
                        original_column_letters.append(col_letter.upper())  # 保存原始字母
        
        if not column_indices:
            return "*未找到有效的选中列*"
        
        # 过滤DataFrame
        filtered_df = df.iloc[:, column_indices]
        
        # 生成预览，保持原始列字母标识
        return generate_markdown_preview_with_original_letters(filtered_df, original_column_letters, preview_rows)
        
    except Exception as e:
        return f"*生成过滤预览失败: {str(e)}*"


def generate_markdown_preview(df: pd.DataFrame, rows: int = 5) -> str:
    """生成Markdown格式的数据预览（按顺序生成字母标识）"""
    if df.empty:
        return "*数据为空*"
    
    # 取前N行数据
    preview_df = df.head(rows)
    
    # 构建Markdown表格
    header = "| " + " | ".join(f"{chr(65+i)}-{col}" for i, col in enumerate(preview_df.columns)) + " |"
    separator = "| " + " | ".join(["-" * max(len(str(col)), 3) for col in preview_df.columns]) + " |"
    
    rows_md = []
    for _, row in preview_df.iterrows():
        # 处理特殊字符和空值
        row_values = [str(val).replace("|", "\\|").replace("\n", " ") if pd.notna(val) else "" for val in row]
        rows_md.append("| " + " | ".join(row_values) + " |")
    
    return "\n".join([header, separator] + rows_md)


def generate_markdown_preview_with_original_letters(df: pd.DataFrame, column_letters: List[str], rows: int = 5) -> str:
    """生成Markdown格式的数据预览（保持原始列字母标识）"""
    if df.empty:
        return "*数据为空*"
    
    # 取前N行数据
    preview_df = df.head(rows)
    
    # 确保列字母数量与DataFrame列数匹配
    if len(column_letters) != len(preview_df.columns):
        # 如果不匹配，回退到顺序生成
        return generate_markdown_preview(df, rows)
    
    # 构建Markdown表格，使用原始列字母标识
    header = "| " + " | ".join(f"{letter}-{col}" for letter, col in zip(column_letters, preview_df.columns)) + " |"
    separator = "| " + " | ".join(["-" * max(len(str(col)), 3) for col in preview_df.columns]) + " |"
    
    rows_md = []
    for _, row in preview_df.iterrows():
        # 处理特殊字符和空值
        row_values = [str(val).replace("|", "\\|").replace("\n", " ") if pd.notna(val) else "" for val in row]
        rows_md.append("| " + " | ".join(row_values) + " |")
    
    return "\n".join([header, separator] + rows_md)


def update_selections_with_columns(selections: List[Tuple], selected_columns_dict: Dict[str, List[str]]) -> List[Tuple[str, str, List[str]]]:
    """更新选择列表，添加列选择信息
    
    参数:
        selections: 原始选择列表 [(file_path, sheet_name), ...]
        selected_columns_dict: 列选择字典 {f"{file_path}#{sheet_name}": [columns]}
    
    返回:
        更新后的选择列表 [(file_path, sheet_name, selected_columns), ...]
    """
    updated_selections = []
    
    for selection in selections:
        if len(selection) == 2:
            file_path, sheet_name = selection
            key = f"{file_path}#{sheet_name}"
            selected_columns = selected_columns_dict.get(key, [])
            updated_selections.append((file_path, sheet_name, selected_columns))
        elif len(selection) == 3:
            updated_selections.append(selection)
        else:
            # 处理异常情况
            continue
    
    return updated_selections