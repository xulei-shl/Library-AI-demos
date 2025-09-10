#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
count_image_groups.py
计算目录中有多少组图片（基于相同的前缀）
"""

from pathlib import Path
from collections import defaultdict

def count_image_groups(directory: Path) -> int:
    # 收集所有jpg/jpeg文件（不区分大小写）
    jpegs = sorted(directory.glob("*.[jJ][pP][gG]")) + sorted(directory.glob("*.[jJ][pP][eE][gG]"))
    
    if not jpegs:
        print("未找到任何 jpg 图片。")
        return 0
    
    # 创建字典来统计每组图片
    groups = defaultdict(int)
    
    # 提取每个文件的前缀（假设格式为"前缀-数字.jpg"）
    for jpeg in jpegs:
        stem = jpeg.stem
        # 查找最后一个"-"的位置，作为前缀分隔符
        last_dash = stem.rfind('-')
        if last_dash == -1:
            # 如果没有"-"，则整个文件名作为前缀
            prefix = stem
        else:
            prefix = stem[:last_dash]
        
        groups[prefix] += 1
    
    # 输出每组的信息
    print(f"共找到 {len(groups)} 组图片:")
    for i, (prefix, count) in enumerate(groups.items(), 1):
        print(f"第{i}组: 前缀 '{prefix}' - 包含 {count} 张图片")
    
    return len(groups)

if __name__ == "__main__":
    # 直接指定路径
    directory = Path(r"E:\scripts\jiemudan\2")
    
    if not directory.exists():
        print(f"目录不存在: {directory}")
    else:
        count_image_groups(directory)