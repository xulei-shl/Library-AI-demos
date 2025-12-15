#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ExcelReader单元测试

测试Excel数据读取器的各项功能，包括正常路径、边界条件和异常路径。
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pandas as pd

from src.core.book_vectorization.excel_reader import ExcelReader


class TestExcelReader:
    """ExcelReader测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.excel_reader = ExcelReader()
        
        # 创建测试数据
        self.test_books_data = [
            {
                "书目条码": "B001",
                "豆瓣书名": "测试书籍1",
                "豆瓣副标题": "副标题1",
                "豆瓣作者": "作者1",
                "豆瓣丛书": "丛书1",
                "豆瓣内容简介": "内容简介1",
                "豆瓣作者简介": "作者简介1",
                "豆瓣目录": "目录1",
                "初评结果": True,
                "初评理由": "理由1"
            },
            {
                "书目条码": "B002",
                "豆瓣书名": "测试书籍2",
                "豆瓣副标题": "副标题2",
                "豆瓣作者": "作者2",
                "豆瓣丛书": "丛书2",
                "豆瓣内容简介": "内容简介2",
                "豆瓣作者简介": "作者简介2",
                "豆瓣目录": "目录2",
                "初评结果": False,
                "初评理由": "理由2"
            },
            {
                "书目条码": "B003",
                "豆瓣书名": "测试书籍3",
                "豆瓣副标题": "副标题3",
                "豆瓣作者": "作者3",
                "豆瓣丛书": "丛书3",
                "豆瓣内容简介": "内容简介3",
                "豆瓣作者简介": "作者简介3",
                "豆瓣目录": "目录3",
                "初评结果": "TRUE",  # 字符串形式的TRUE
                "初评理由": "理由3"
            }
        ]
    
    def test_init(self):
        """测试初始化"""
        assert self.excel_reader is not None
    
    def test_load_books_data_normal(self):
        """测试正常加载Excel数据"""
        # 创建临时Excel文件
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            temp_path = tmp_file.name
            
        try:
            # 写入测试数据
            df = pd.DataFrame(self.test_books_data)
            df.to_excel(temp_path, index=False)
            
            # 加载数据
            result = self.excel_reader.load_books_data(temp_path)
            
            # 验证结果
            assert len(result) == 3
            assert result[0]["书目条码"] == "B001"
            assert result[0]["豆瓣书名"] == "测试书籍1"
            assert result[0]["初评结果"] is True
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_load_books_data_file_not_exist(self):
        """测试文件不存在的情况"""
        with pytest.raises(FileNotFoundError, match="Excel文件不存在"):
            self.excel_reader.load_books_data("nonexistent_file.xlsx")
    
    def test_load_books_data_wrong_format(self):
        """测试文件格式错误的情况"""
        # 创建临时文本文件
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
            temp_path = tmp_file.name
            
        try:
            with pytest.raises(ValueError, match="不支持的文件格式"):
                self.excel_reader.load_books_data(temp_path)
                
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_load_books_data_missing_columns(self):
        """测试缺少必需列的情况"""
        # 创建缺少必需列的数据
        incomplete_data = [
            {
                "书名": "测试书籍",  # 缺少"书目条码"和"豆瓣书名"
                "作者": "测试作者"
            }
        ]
        
        # 创建临时Excel文件
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            temp_path = tmp_file.name
            
        try:
            # 写入测试数据
            df = pd.DataFrame(incomplete_data)
            df.to_excel(temp_path, index=False)
            
            # 尝试加载数据
            with pytest.raises(ValueError, match="Excel文件缺少必需的列"):
                self.excel_reader.load_books_data(temp_path)
                
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_filter_selected_books_normal(self):
        """测试正常过滤通过筛选的书籍"""
        # 测试中文列名
        result = self.excel_reader.filter_selected_books(self.test_books_data)
        
        # 应该返回2本书（B001和B003）
        assert len(result) == 2
        assert result[0]["书目条码"] == "B001"
        assert result[1]["书目条码"] == "B003"
    
    def test_filter_selected_books_no_selected(self):
        """测试没有通过筛选的书籍"""
        # 创建全部未通过筛选的数据
        no_selected_data = [
            {
                "书目条码": "B001",
                "豆瓣书名": "测试书籍1",
                "初评结果": False
            },
            {
                "书目条码": "B002",
                "豆瓣书名": "测试书籍2",
                "初评结果": "FALSE"  # 字符串形式的FALSE
            }
        ]
        
        result = self.excel_reader.filter_selected_books(no_selected_data)
        
        # 应该返回空列表
        assert len(result) == 0
    
    def test_filter_selected_books_all_selected(self):
        """测试全部通过筛选的书籍"""
        # 创建全部通过筛选的数据
        all_selected_data = [
            {
                "书目条码": "B001",
                "豆瓣书名": "测试书籍1",
                "初评结果": True
            },
            {
                "书目条码": "B002",
                "豆瓣书名": "测试书籍2",
                "初评结果": "TRUE"  # 字符串形式的TRUE
            }
        ]
        
        result = self.excel_reader.filter_selected_books(all_selected_data)
        
        # 应该返回全部书籍
        assert len(result) == 2
    
    def test_filter_selected_books_empty_list(self):
        """测试空书籍列表"""
        result = self.excel_reader.filter_selected_books([])
        
        # 应该返回空列表
        assert len(result) == 0