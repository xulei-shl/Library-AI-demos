#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Excel增强器单元测试

测试Excel增强器的核心功能，包括Excel文件读取、数据增强、结果保存等。
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from src.core.book_vectorization.excel_enhancer import ExcelEnhancer


class TestExcelEnhancer:
    """Excel增强器测试类"""
    
    @pytest.fixture
    def sample_excel_file(self, tmp_path):
        """创建示例Excel文件"""
        excel_path = tmp_path / "sample_books.xlsx"
        
        # 创建示例数据
        data = [
            {
                "书目条码": "123456789",
                "豆瓣书名": "数字时代的自我",
                "豆瓣副标题": "社交媒体与身份认同",
                "豆瓣作者": "张三",
                "豆瓣丛书": "数字文化研究丛书",
                "豆瓣内容简介": "本书深入探讨了数字时代社交媒体对个体身份认同的影响。",
                "豆瓣作者简介": "张三，数字社会学专家。",
                "豆瓣目录": "第一章 数字身份的兴起"
            },
            {
                "书目条码": "987654321",
                "豆瓣书名": "虚拟空间的哲学",
                "豆瓣副标题": "数字存在论研究",
                "豆瓣作者": "李四",
                "豆瓣丛书": "哲学前沿丛书",
                "豆瓣内容简介": "从哲学角度探讨虚拟空间中的存在本质。",
                "豆瓣作者简介": "李四，哲学研究者。",
                "豆瓣目录": "第一章 虚拟与现实的边界"
            }
        ]
        
        # 创建DataFrame并保存为Excel
        df = pd.DataFrame(data)
        df.to_excel(excel_path, index=False)
        
        return str(excel_path)
    
    @pytest.fixture
    def sample_evaluation_results(self):
        """示例评估结果"""
        return [
            {
                "book_barcode": "123456789",
                "is_selected": True,
                "score": 4.5,
                "evaluation_logic": {
                    "relevance_check": "高相关性",
                    "dimension_match": "契合度高"
                },
                "reason": "这本书深入探讨了数字时代身份认同问题。",
                "llm_status": "success",
                "error_message": ""
            },
            {
                "book_barcode": "987654321",
                "is_selected": False,
                "score": 2.0,
                "evaluation_logic": {
                    "relevance_check": "低相关性",
                    "dimension_match": "契合度低"
                },
                "reason": "这本书与主题关联度不高。",
                "llm_status": "success",
                "error_message": ""
            }
        ]
    
    def test_init_success(self, sample_excel_file):
        """测试初始化成功"""
        enhancer = ExcelEnhancer(sample_excel_file)
        
        assert enhancer.excel_path == Path(sample_excel_file)
        assert enhancer._failed_books == []
    
    def test_init_file_not_exists(self):
        """测试文件不存在的情况"""
        with pytest.raises(FileNotFoundError):
            ExcelEnhancer("不存在的文件.xlsx")
    
    def test_init_invalid_format(self, tmp_path):
        """测试无效文件格式"""
        # 创建非Excel文件
        invalid_file = tmp_path / "invalid.txt"
        invalid_file.write_text("这不是Excel文件")
        
        with pytest.raises(ValueError):
            ExcelEnhancer(str(invalid_file))
    
    def test_load_books_data_success(self, sample_excel_file):
        """测试成功加载Excel数据"""
        enhancer = ExcelEnhancer(sample_excel_file)
        books_data = enhancer.load_books_data()
        
        assert len(books_data) == 2
        assert books_data[0]["书目条码"] == "123456789"
        assert books_data[0]["豆瓣书名"] == "数字时代的自我"
        assert books_data[1]["书目条码"] == "987654321"
        assert books_data[1]["豆瓣书名"] == "虚拟空间的哲学"
    
    def test_load_books_data_missing_columns(self, tmp_path):
        """测试缺少必需列的情况"""
        # 创建缺少必需列的Excel文件
        excel_path = tmp_path / "missing_columns.xlsx"
        data = [{"书名": "测试书籍"}]  # 缺少"书目条码"和"豆瓣书名"
        df = pd.DataFrame(data)
        df.to_excel(excel_path, index=False)
        
        enhancer = ExcelEnhancer(str(excel_path))
        
        with pytest.raises(ValueError):
            enhancer.load_books_data()
    
    def test_add_evaluation_results_success(self, sample_excel_file, sample_evaluation_results, tmp_path):
        """测试成功添加评估结果"""
        enhancer = ExcelEnhancer(sample_excel_file)
        
        # 添加评估结果
        output_path = enhancer.add_evaluation_results(sample_evaluation_results)
        
        # 验证输出文件存在
        assert Path(output_path).exists()
        assert "主题筛选增强" in output_path
        
        # 验证增强后的Excel内容
        enhanced_df = pd.read_excel(output_path)
        
        # 检查新增列是否存在
        assert "主题筛选_是否通过" in enhanced_df.columns
        assert "主题筛选_评分" in enhanced_df.columns
        assert "主题筛选_相关性" in enhanced_df.columns
        assert "主题筛选_契合度" in enhanced_df.columns
        assert "主题筛选_评语" in enhanced_df.columns
        assert "主题筛选_状态" in enhanced_df.columns
        assert "主题筛选_错误信息" in enhanced_df.columns
        
        # 检查评估结果是否正确添加
        assert enhanced_df.loc[0, "主题筛选_是否通过"] is True
        assert enhanced_df.loc[0, "主题筛选_评分"] == 4.5
        assert enhanced_df.loc[0, "主题筛选_状态"] == "success"
        
        assert enhanced_df.loc[1, "主题筛选_是否通过"] is False
        assert enhanced_df.loc[1, "主题筛选_评分"] == 2.0
        assert enhanced_df.loc[1, "主题筛选_状态"] == "success"
    
    def test_add_evaluation_results_data_mismatch(self, sample_excel_file, sample_evaluation_results):
        """测试结果数量与书籍数量不匹配的情况"""
        enhancer = ExcelEnhancer(sample_excel_file)
        
        # 创建不匹配的结果（只有1个结果，但有2本书）
        mismatched_results = sample_evaluation_results[:1]
        
        with pytest.raises(ValueError):
            enhancer.add_evaluation_results(mismatched_results)
    
    def test_add_evaluation_results_with_failures(self, sample_excel_file, tmp_path):
        """测试包含失败记录的评估结果"""
        enhancer = ExcelEnhancer(sample_excel_file)
        
        # 创建包含失败记录的结果
        results_with_failures = [
            {
                "book_barcode": "123456789",
                "is_selected": True,
                "score": 4.5,
                "evaluation_logic": {
                    "relevance_check": "高相关性",
                    "dimension_match": "契合度高"
                },
                "reason": "这本书很相关。",
                "llm_status": "success",
                "error_message": ""
            },
            {
                "book_barcode": "987654321",
                "is_selected": False,
                "score": 0.0,
                "evaluation_logic": {
                    "relevance_check": "评估失败",
                    "dimension_match": "评估失败"
                },
                "reason": "评估过程发生错误: API调用失败",
                "llm_status": "failed",
                "error_message": "API调用失败"
            }
        ]
        
        # 添加评估结果
        output_path = enhancer.add_evaluation_results(results_with_failures)
        
        # 验证失败记录
        failed_books = enhancer.get_failed_books()
        assert len(failed_books) == 1
        assert failed_books[0]["book_barcode"] == "987654321"
        assert failed_books[0]["error_message"] == "API调用失败"
    
    def test_get_failed_books_empty(self, sample_excel_file):
        """测试获取失败书籍列表（空列表）"""
        enhancer = ExcelEnhancer(sample_excel_file)
        failed_books = enhancer.get_failed_books()
        assert failed_books == []
    
    def test_get_failed_books_with_failures(self, sample_excel_file):
        """测试获取失败书籍列表（有失败记录）"""
        enhancer = ExcelEnhancer(sample_excel_file)
        
        # 手动设置失败记录
        enhancer._failed_books = [
            {
                "index": 1,
                "book_barcode": "987654321",
                "error_message": "测试错误"
            }
        ]
        
        failed_books = enhancer.get_failed_books()
        assert len(failed_books) == 1
        assert failed_books[0]["book_barcode"] == "987654321"
        assert failed_books[0]["error_message"] == "测试错误"
    
    def test_create_summary_report(self, sample_excel_file, tmp_path):
        """测试创建摘要报告"""
        enhancer = ExcelEnhancer(sample_excel_file)
        
        # 设置失败记录
        enhancer._failed_books = [
            {
                "index": 0,
                "book_barcode": "123456789",
                "error_message": "测试错误1"
            },
            {
                "index": 1,
                "book_barcode": "987654321",
                "error_message": "测试错误2"
            }
        ]
        
        # 创建摘要报告
        summary_path = enhancer.create_summary_report()
        
        # 验证报告文件存在
        assert Path(summary_path).exists()
        assert "主题筛选摘要报告" in summary_path
        
        # 验证报告内容
        with open(summary_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "主题筛选结果摘要报告" in content
            assert "失败书籍数量: 2" in content
            assert "123456789" in content
            assert "987654321" in content
            assert "测试错误1" in content
            assert "测试错误2" in content
    
    def test_create_summary_report_no_failures(self, sample_excel_file):
        """测试没有失败记录时的摘要报告创建"""
        enhancer = ExcelEnhancer(sample_excel_file)
        
        # 创建摘要报告
        summary_path = enhancer.create_summary_report()
        
        # 验证返回空路径
        assert summary_path == ""
    
    def test_generate_output_path(self, sample_excel_file):
        """测试生成输出路径"""
        enhancer = ExcelEnhancer(sample_excel_file)
        output_path = enhancer._generate_output_path()
        
        # 验证输出路径格式
        assert "主题筛选增强" in output_path
        assert output_path.suffix == ".xlsx"
        assert output_path.parent == Path(sample_excel_file).parent
    
    @patch('src.core.book_vectorization.excel_enhancer.pd.ExcelWriter')
    def test_save_enhanced_excel(self, mock_writer, sample_excel_file, sample_evaluation_results, tmp_path):
        """测试保存增强后的Excel文件"""
        enhancer = ExcelEnhancer(sample_excel_file)
        
        # 创建DataFrame
        df = pd.DataFrame([
            {"书目条码": "123456789", "豆瓣书名": "测试书籍"},
            {"书目条码": "987654321", "豆瓣书名": "测试书籍2"}
        ])
        
        # 添加评估结果列
        df = enhancer._add_evaluation_columns(df, sample_evaluation_results)
        
        # 创建输出路径
        output_path = tmp_path / "test_output.xlsx"
        
        # 保存Excel
        enhancer._save_enhanced_excel(df, output_path)
        
        # 验证ExcelWriter被调用
        mock_writer.assert_called_once()
        
        # 验证输出目录被创建
        assert output_path.parent.exists()
    
    def test_theme_columns_constant(self):
        """测试主题筛选列常量"""
        expected_columns = {
            "is_selected": "主题筛选_是否通过",
            "score": "主题筛选_评分",
            "relevance_check": "主题筛选_相关性",
            "dimension_match": "主题筛选_契合度",
            "reason": "主题筛选_评语",
            "llm_status": "主题筛选_状态",
            "error_message": "主题筛选_错误信息"
        }
        
        assert ExcelEnhancer.THEME_COLUMNS == expected_columns