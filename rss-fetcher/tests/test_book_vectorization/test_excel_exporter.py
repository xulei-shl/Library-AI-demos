#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Excel导出器单元测试
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.core.book_vectorization.excel_exporter import ExcelExporter


class TestExcelExporter:
    """Excel导出器测试类"""
    
    @pytest.fixture
    def db_config(self):
        """数据库配置"""
        return {
            'path': ':memory:',
            'table': 'books'
        }
    
    @pytest.fixture
    def excel_config(self):
        """Excel导出配置"""
        return {
            'enabled': True,
            'default_directory': 'runtime/outputs/excel',
            'filename_template': 'books_full_info_{timestamp}',
            'timestamp_format': '%Y%m%d_%H%M%S',
            'auto_create_directory': True
        }
    
    @pytest.fixture
    def sample_books_data(self):
        """示例书籍数据"""
        return [
            {
                'id': 1,
                'barcode': '54121111261793',
                'call_no': 'TP391/4831-1',
                'cleaned_call_no': 'TP391/4831-1',
                'book_title': '自然语言理解',
                'additional_info': '200454818',
                'isbn': '9787302627784',
                'douban_url': 'https://book.douban.com/subject/36481873/',
                'douban_rating': 8.5,
                'douban_title': '自然语言理解',
                'douban_subtitle': '自然语言处理',
                'douban_original_title': 'Natural Language Understanding',
                'douban_author': '赵海',
                'douban_translator': '张三',
                'douban_publisher': '清华大学出版社',
                'douban_producer': '清华出版社',
                'douban_series': '计算机科学丛书',
                'douban_series_link': 'https://book.douban.com/series/123/',
                'douban_price': '89.00',
                'douban_isbn': '9787302627784',
                'douban_pages': 388,
                'douban_binding': '平装',
                'douban_pub_year': 2023,
                'douban_rating_count': 1250,
                'douban_summary': '本书系统介绍自然语言处理的经典和前沿技术',
                'douban_author_intro': '赵海，教授，博士生导师',
                'douban_catalog': '目录\n第1章 绪论\n第2章 基础知识',
                'douban_cover_image': 'https://img2.doubanio.com/view/subject/s/public/s34590761.jpg',
                'data_version': '1.0',
                'created_at': '2025-11-05 16:43:01',
                'updated_at': '2025-11-05 16:43:01',
                'embedding_id': 'abc123',
                'embedding_status': 'completed',
                'embedding_date': '2025-11-05 16:43:01',
                'embedding_error': None,
                'retry_count': 0
            },
            {
                'id': 2,
                'barcode': '54121111261794',
                'call_no': 'TP392/4832-2',
                'cleaned_call_no': 'TP392/4832-2',
                'book_title': '机器学习',
                'additional_info': '200454819',
                'isbn': '9787302627791',
                'douban_url': 'https://book.douban.com/subject/36481874/',
                'douban_rating': 9.0,
                'douban_title': '机器学习',
                'douban_subtitle': '机器学习基础',
                'douban_original_title': 'Machine Learning',
                'douban_author': '李四',
                'douban_translator': '王五',
                'douban_publisher': '北京大学出版社',
                'douban_producer': '北大出版社',
                'douban_series': '人工智能丛书',
                'douban_series_link': 'https://book.douban.com/series/124/',
                'douban_price': '99.00',
                'douban_isbn': '9787302627791',
                'douban_pages': 450,
                'douban_binding': '精装',
                'douban_pub_year': 2022,
                'douban_rating_count': 2100,
                'douban_summary': '本书全面介绍机器学习的理论和方法',
                'douban_author_intro': '李四，教授，人工智能专家',
                'douban_catalog': '目录\n第1章 机器学习概述\n第2章 监督学习',
                'douban_cover_image': 'https://img2.doubanio.com/view/subject/s/public/s34590762.jpg',
                'data_version': '1.0',
                'created_at': '2025-11-05 16:43:02',
                'updated_at': '2025-11-05 16:43:02',
                'embedding_id': 'def456',
                'embedding_status': 'completed',
                'embedding_date': '2025-11-05 16:43:02',
                'embedding_error': None,
                'retry_count': 0
            }
        ]
    
    @pytest.fixture
    def excel_exporter(self, db_config, excel_config):
        """创建Excel导出器实例"""
        return ExcelExporter(db_config, excel_config)
    
    def test_init(self, db_config, excel_config):
        """测试初始化"""
        exporter = ExcelExporter(db_config, excel_config)
        
        assert exporter.db_reader is not None
        assert exporter.excel_config == excel_config
    
    def test_export_books_to_excel_success(self, excel_exporter, sample_books_data):
        """测试成功导出Excel"""
        book_ids = [1, 2]
        
        # 模拟数据库查询
        with patch.object(excel_exporter, '_query_books_from_database', return_value=sample_books_data) as mock_query:
            with patch.object(excel_exporter, '_export_to_excel', return_value='test_output.xlsx') as mock_export:
                
                result = excel_exporter.export_books_to_excel(book_ids, 'test_output.xlsx')
                
                assert result == 'test_output.xlsx'
                mock_query.assert_called_once_with(book_ids)
                mock_export.assert_called_once_with(sample_books_data, 'test_output.xlsx')
    
    def test_export_books_to_excel_empty_ids(self, excel_exporter):
        """测试空的书籍ID列表"""
        with pytest.raises(ValueError, match="书籍ID列表为空"):
            excel_exporter.export_books_to_excel([], 'test_output.xlsx')
    
    def test_export_books_to_excel_no_data(self, excel_exporter):
        """测试没有查询到书籍数据"""
        book_ids = [1, 2]
        
        with patch.object(excel_exporter, '_query_books_from_database', return_value=[]):
            with pytest.raises(ValueError, match="未查询到任何书籍数据"):
                excel_exporter.export_books_to_excel(book_ids, 'test_output.xlsx')
    
    def test_query_books_from_database(self, excel_exporter, sample_books_data):
        """测试从数据库查询书籍信息"""
        book_ids = [1, 2]
        
        # 模拟数据库读取器
        mock_reader = Mock()
        mock_reader.get_book_by_id.side_effect = [
            sample_books_data[0],
            sample_books_data[1]
        ]
        excel_exporter.db_reader = mock_reader
        
        result = excel_exporter._query_books_from_database(book_ids)
        
        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[1]['id'] == 2
        assert mock_reader.get_book_by_id.call_count == 2
    
    def test_query_books_from_database_missing_book(self, excel_exporter, sample_books_data):
        """测试查询不存在的书籍"""
        book_ids = [1, 2, 3]
        
        # 模拟数据库读取器，第三本书不存在
        mock_reader = Mock()
        mock_reader.get_book_by_id.side_effect = [
            sample_books_data[0],
            None,
            sample_books_data[1]
        ]
        excel_exporter.db_reader = mock_reader
        
        result = excel_exporter._query_books_from_database(book_ids)
        
        assert len(result) == 2  # 只返回两本存在的书
        assert result[0]['id'] == 1
        assert result[1]['id'] == 2
    
    def test_filter_book_fields(self, excel_exporter):
        """测试过滤书籍字段"""
        book_info = {
            'id': 1,
            'barcode': '54121111261793',
            'call_no': 'TP391/4831-1',
            'cleaned_call_no': 'TP391/4831-1',
            'book_title': '自然语言理解',
            'additional_info': '200454818',
            'isbn': '9787302627784',
            'douban_url': 'https://book.douban.com/subject/36481873/',
            'douban_rating': 8.5,
            'douban_title': '自然语言理解',
            'douban_subtitle': '自然语言处理',
            'douban_original_title': 'Natural Language Understanding',
            'douban_author': '赵海',
            'douban_translator': '张三',
            'douban_publisher': '清华大学出版社',
            'douban_producer': '清华出版社',
            'douban_series': '计算机科学丛书',
            'douban_series_link': 'https://book.douban.com/series/123/',
            'douban_price': '89.00',
            'douban_isbn': '9787302627784',
            'douban_pages': 388,
            'douban_binding': '平装',
            'douban_pub_year': 2023,
            'douban_rating_count': 1250,
            'douban_summary': '本书系统介绍自然语言处理的经典和前沿技术',
            'douban_author_intro': '赵海，教授，博士生导师',
            'douban_catalog': '目录\n第1章 绪论\n第2章 基础知识',
            'douban_cover_image': 'https://img2.doubanio.com/view/subject/s/public/s34590761.jpg',
            'data_version': '1.0',
            'created_at': '2025-11-05 16:43:01',
            'updated_at': '2025-11-05 16:43:01',
            'embedding_id': 'abc123',
            'embedding_status': 'completed',
            'embedding_date': '2025-11-05 16:43:01',
            'embedding_error': None,
            'retry_count': 0
        }
        
        result = excel_exporter._filter_book_fields(book_info)
        
        # 检查排除的字段不存在
        exclude_fields = [
            'data_version', 'created_at', 'updated_at', 'embedding_id',
            'embedding_status', 'embedding_date', 'embedding_error', 'retry_count'
        ]
        
        for field in exclude_fields:
            assert field not in result, f"字段 {field} 应该被排除"
        
        # 检查其他字段都存在
        for field in book_info:
            if field not in exclude_fields:
                assert field in result, f"字段 {field} 应该被保留"
        
        # 验证一些关键字段
        assert result['id'] == 1
        assert result['douban_title'] == '自然语言理解'
        assert result['douban_author'] == '赵海'
        assert result['isbn'] == '9787302627784'
        # 验证新增的候选状态字段
        assert result['candidate_status'] == '候选'
    
    def test_export_to_excel(self, excel_exporter, sample_books_data):
        """测试导出到Excel文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'test_output.xlsx'
            
            # 过滤书籍数据（模拟实际使用场景）
            filtered_books_data = [excel_exporter._filter_book_fields(book) for book in sample_books_data]
            
            result_path = excel_exporter._export_to_excel(filtered_books_data, str(output_path))
            
            assert Path(result_path).exists()
            assert result_path == str(output_path)
            
            # 验证文件内容
            import pandas as pd
            df = pd.read_excel(result_path)
            
            assert len(df) == 2
            assert 'ID' in df.columns
            assert '豆瓣书名' in df.columns
            assert '豆瓣作者' in df.columns
            assert '书目条码' in df.columns
            assert '索书号' in df.columns
            assert '候选状态' in df.columns
            assert df.iloc[0]['ID'] == 1
            assert df.iloc[0]['豆瓣书名'] == '自然语言理解'
            assert df.iloc[0]['豆瓣作者'] == '赵海'
            assert df.iloc[0]['候选状态'] == '候选'
            assert df.iloc[1]['ID'] == 2
            assert df.iloc[1]['豆瓣书名'] == '机器学习'
            assert df.iloc[1]['豆瓣作者'] == '李四'
            assert df.iloc[1]['候选状态'] == '候选'
    
    def test_export_to_excel_auto_extension(self, excel_exporter, sample_books_data):
        """测试自动添加文件扩展名"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'test_output'  # 没有扩展名
            
            result_path = excel_exporter._export_to_excel(sample_books_data, str(output_path))
            
            assert Path(result_path).suffix == '.xlsx'
    
    def test_export_to_excel_relative_path(self, excel_exporter, sample_books_data):
        """测试相对路径处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 修改配置的默认目录
            excel_exporter.excel_config['default_directory'] = temp_dir
            
            result_path = excel_exporter._export_to_excel(sample_books_data, 'test_output.xlsx')
            
            assert Path(result_path).parent == Path(temp_dir)
            assert Path(result_path).name == 'test_output.xlsx'
    
    def test_close(self, excel_exporter):
        """测试关闭数据库连接"""
        mock_reader = Mock()
        excel_exporter.db_reader = mock_reader
        
        excel_exporter.close()
        
        mock_reader.close.assert_called_once()