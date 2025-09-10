#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""  
Excel处理工具模块
提供Excel文件解析、验证和预览生成等功能
"""

import os
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from modules.config_manager import MultiModelConfigManager


def get_excel_config():
    """获取Excel相关配置"""
    config_manager = MultiModelConfigManager()
    return config_manager.get_excel_config()


def validate_excel_file(file_path: str) -> Tuple[bool, str]:
    """验证Excel文件
    
    参数:
        file_path: Excel文件路径
        
    返回:
        (是否有效, 错误信息)
    """
    if not file_path or not os.path.exists(file_path):
        return False, "文件不存在"
    
    # 获取配置
    config = get_excel_config()
    
    # 检查文件扩展名
    _, ext = os.path.splitext(file_path)
    if ext.lower() not in config['supported_formats']:
        return False, f"不支持的文件格式，请使用{', '.join(config['supported_formats'])}格式"
    
    # 检查文件大小
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > config['max_file_size_mb']:
        return False, f"文件大小超过限制（{config['max_file_size_mb']}MB）"
    
    return True, ""


def parse_excel_data(file_path: str) -> Dict[str, Any]:
    """解析Excel数据
    
    参数:
        file_path: Excel文件路径
        
    返回:
        {
            'data': DataFrame,  # 完整数据
            'preview': str,     # 前N行Markdown格式
            'total_rows': int,  # 总行数
            'columns': list     # 列名列表
        }
    """
    # 获取配置
    config = get_excel_config()
    max_rows = config['max_rows']
    preview_rows = config['preview_rows']
    
    try:
        # 使用pandas读取Excel文件
        df = pd.read_excel(file_path)
        
        # 检查数据行数，超出限制时截取前max_rows行
        total_rows = len(df)
        if total_rows > max_rows:
            df = df.iloc[:max_rows]
            truncated = True
        else:
            truncated = False
        
        # 生成列名列表（格式：'A列-列名'）
        columns = [f"{chr(65+i)}列-{col}" for i, col in enumerate(df.columns)]
        
        # 生成Markdown预览
        preview = generate_markdown_preview(df, preview_rows)
        
        return {
            'data': df,
            'preview': preview,
            'total_rows': total_rows,
            'truncated': truncated,
            'columns': columns,
            'column_names': list(df.columns)
        }
        
    except Exception as e:
        raise Exception(f"解析Excel文件失败: {str(e)}")


def generate_markdown_preview(df: pd.DataFrame, rows: int = 5) -> str:
    """生成Markdown格式的数据预览
    
    参数:
        df: pandas DataFrame
        rows: 预览行数
        
    返回:
        Markdown格式字符串
    """
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


def get_column_list(df: pd.DataFrame) -> List[str]:
    """获取列名列表，格式：['A列-姓名', 'B列-年龄', ...]
    
    参数:
        df: pandas DataFrame
        
    返回:
        列名列表
    """
    return [f"{chr(65+i)}列-{col}" for i, col in enumerate(df.columns)]


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小
    
    参数:
        size_bytes: 文件大小（字节）
        
    返回:
        格式化后的文件大小字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0 or unit == 'GB':
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0