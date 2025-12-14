#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通用文件操作工具模块

提供文件和目录操作的通用函数，包括目录创建、文件名生成等功能。
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


def ensure_directory_exists(directory_path: str) -> None:
    """
    确保目录存在，不存在则创建
    
    Args:
        directory_path: 目录路径
    """
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise RuntimeError(f"创建目录失败: {directory_path}, 错误: {e}")


def generate_filename(template: str, metadata: Dict, timestamp_format: str, include_timestamp: bool) -> str:
    """
    根据模板生成文件名
    
    Args:
        template: 文件名模板
        metadata: 元数据字典
        timestamp_format: 时间戳格式
        include_timestamp: 是否包含时间戳
        
    Returns:
        生成的文件名
    """
    # 替换模板中的占位符
    filename = template
    
    # 替换基本元数据
    for key, value in metadata.items():
        placeholder = "{" + key + "}"
        if placeholder in filename:
            filename = filename.replace(placeholder, str(value))
    
    # 添加时间戳
    if include_timestamp:
        timestamp = datetime.now().strftime(timestamp_format)
        filename = filename.replace("{timestamp}", timestamp)
    else:
        filename = filename.replace("{timestamp}", "")
    
    # 清理文件名中的非法字符
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    
    # 移除多余的连续下划线
    while "__" in filename:
        filename = filename.replace("__", "_")
    
    return filename


def safe_write_file(file_path: str, content: str) -> None:
    """
    安全写入文件，确保目录存在
    
    Args:
        file_path: 文件路径
        content: 文件内容
    """
    file_path_obj = Path(file_path)
    ensure_directory_exists(str(file_path_obj.parent))
    
    try:
        file_path_obj.write_text(content, encoding='utf-8')
    except Exception as e:
        raise RuntimeError(f"写入文件失败: {file_path}, 错误: {e}")


def get_file_extension(format_name: str) -> str:
    """
    根据格式名称获取文件扩展名
    
    Args:
        format_name: 格式名称（如 'markdown', 'json'）
        
    Returns:
        文件扩展名（如 '.md', '.json'）
    """
    format_extensions = {
        'markdown': '.md',
        'json': '.json',
        'txt': '.txt',
        'csv': '.csv'
    }
    
    return format_extensions.get(format_name.lower(), '.txt')