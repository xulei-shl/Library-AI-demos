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
                'douban_title': '测试书籍1',
                'douban_author': '测试作者1',
                'douban_rating': 8.5,
                'douban_pub_year': '2023',
                'douban_publisher': '测试出版社',
                'douban_summary': '这是一本测试书籍',
                'douban_catalog': '第一章\n第二章\n第三章',
                'call_no': 'TP123/456',
                'isbn': '9781234567890',
                'pages': 200,
                'price': '59.00',
                'douban_tags': '技术,编程',
                'embedding_status': 'completed',
                'embedding_date': '2023-01-01'
            },
            {
                'id': 2,
                'douban_title': '测试书籍2',
                'douban_author': '测试作者2',
                'douban_rating': 9.0,
                'douban_pub_year': '2022',
                'douban_publisher': '测试出版社2',
                'douban_summary': '这是另一本测试书籍',
                'douban_catalog': '第一章\n第二章',
                'call_no': 'TP124/789',
                'isbn': '9780987654321',
                'pages': 150,
                'price': '49.00',
                'douban_tags': '技术,设计',
                'embedding_status': 'completed',
                'embedding_date': '2022-01-01'
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
            'douban_title': '测试书籍',
            'douban_author': '测试作者',
            'douban_rating': 8.5,
            'douban_pub_year': '2023',
            'douban_publisher': '测试出版社',
            'douban_summary': '测试简介',
            'douban_catalog': '测试目录',
            'call_no': 'TP123/456',
            'isbn': '9781234567890',
            'pages': 200,
            'price': '59.00',
            'douban_tags': '技术,编程',
            'embedding_status': 'completed',
            'embedding_date': '2023-01-01',
            'extra_field': '不需要的字段',
            'another_extra': '也不需要'
        }
        
        result = excel_exporter._filter_book_fields(book_info)
        
        # 检查只包含需要的字段
        expected_fields = [
            'id', 'douban_title', 'douban_author', 'douban_rating', 
            'douban_pub_year', 'douban_publisher', 'douban_summary', 
            'douban_catalog', 'call_no', 'isbn', 'pages', 'price', 
            'douban_tags', 'embedding_status', 'embedding_date'
        ]
        
        for field in expected_fields:
            assert field in result
        
        # 检查不包含不需要的字段
        assert 'extra_field' not in result
        assert 'another_extra' not in result
    
    def test_export_to_excel(self, excel_exporter, sample_books_data):
        """测试导出到Excel文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'test_output.xlsx'
            
            result_path = excel_exporter._export_to_excel(sample_books_data, str(output_path))
            
            assert Path(result_path).exists()
            assert result_path == str(output_path)
            
            # 验证文件内容
            import pandas as pd
            df = pd.read_excel(result_path)
            
            assert len(df) == 2
            assert 'ID' in df.columns
            assert '书名' in df.columns
            assert '作者' in df.columns
            assert df.iloc[0]['ID'] == 1
            assert df.iloc[0]['书名'] == '测试书籍1'
            assert df.iloc[1]['ID'] == 2
            assert df.iloc[1]['书名'] == '测试书籍2'
    
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