#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Excel数据读取器，专门处理书籍元数据读取

该模块实现了Excel文件的读取和过滤功能，主要用于从Excel文件中
读取书籍数据，并过滤出通过主题筛选的书籍。
"""

from pathlib import Path
from typing import Dict, List

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ExcelReader:
    """Excel数据读取器，专门处理书籍元数据读取"""
    
    def __init__(self):
        """初始化Excel读取器"""
        logger.info("Excel读取器初始化完成")
    
    def load_books_data(self, excel_path: str) -> List[Dict]:
        """
        加载Excel中的书籍数据
        
        Args:
            excel_path: Excel文件路径
            
        Returns:
            书籍数据列表
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误或缺少必需列
        """
        logger.info(f"开始加载Excel数据: {excel_path}")
        
        # 验证文件存在性
        excel_file = Path(excel_path)
        if not excel_file.exists():
            raise FileNotFoundError(f"Excel文件不存在: {excel_path}")
        
        # 验证文件格式
        if excel_file.suffix.lower() not in ['.xlsx', '.xls']:
            raise ValueError(f"不支持的文件格式: {excel_file.suffix}")
        
        try:
            # 读取Excel文件
            df = pd.read_excel(excel_path)
            
            # 检查必需列是否存在
            required_columns = ["书目条码", "豆瓣书名"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Excel文件缺少必需的列: {missing_columns}")
            
            # 转换为字典列表
            books_data = df.to_dict('records')
            
            logger.info(f"成功加载{len(books_data)}本书籍数据")
            
            return books_data
            
        except Exception as e:
            logger.error(f"加载Excel数据时发生错误: {e}")
            raise
    
    def filter_selected_books(self, books_data: List[Dict]) -> List[Dict]:
        """
        过滤通过主题筛选的书籍
        
        Args:
            books_data: 完整的书籍数据列表
            
        Returns:
            通过筛选的书籍数据列表
        """
        logger.info(f"开始过滤通过主题筛选的书籍，总书籍数: {len(books_data)}")
        
        selected_books = []
        
        for book in books_data:
            # 检查是否有"初评结果"列且值为TRUE
            # 注意：Excel中的TRUE值在pandas读取后可能是布尔值True或字符串"TRUE"
            is_selected = False
            
            # 检查中文列名（主题筛选增强后的Excel）
            if "初评结果" in book:
                value = book["初评结果"]
                # 处理可能的TRUE值形式：布尔值True、字符串"TRUE"、字符串"True"
                if value is True or (isinstance(value, str) and value.upper() == "TRUE"):
                    is_selected = True
            
            if is_selected:
                selected_books.append(book)
        
        logger.info(f"筛选完成，通过筛选的书籍数: {len(selected_books)}")
        
        return selected_books