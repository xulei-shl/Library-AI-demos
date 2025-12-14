#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
输出格式化器测试用例
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.book_vectorization.output_formatter import OutputFormatter, extract_md_filename


class TestOutputFormatter:
    """输出格式化器测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'enabled': True,
            'formats': ['markdown', 'json'],
            'base_directory': self.temp_dir,
            'filename_template': 'test_{mode}_{timestamp}',
            'include_timestamp': True,
            'timestamp_format': '%Y%m%d_%H%M%S',
            'auto_create_directory': True
        }
        self.formatter = OutputFormatter(self.config)
        
        # 测试数据
        self.sample_results = [
            {
                'title': '测试书籍1',
                'author': '作者1',
                'rating': 8.5,
                'call_no': 'TP123',
                'summary': '这是一本测试书籍的简介',
                'similarity_score': 0.9234,
                'fused_score': 0.8756
            },
            {
                'title': '测试书籍2',
                'author': '作者2',
                'rating': 7.8,
                'call_no': 'TP456',
                'summary': '这是另一本测试书籍的简介',
                'similarity_score': 0.8567
            }
        ]
        
        self.sample_metadata = {
            'mode': 'single',
            'query': '测试查询',
            'top_k': 5,
            'min_rating': 7.0
        }
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """测试初始化"""
        assert self.formatter.enabled is True
        assert self.formatter.formats == ['markdown', 'json']
        assert self.formatter.base_directory == self.temp_dir
        assert self.formatter.filename_template == 'test_{mode}_{timestamp}'
        assert self.formatter.include_timestamp is True
    
    def test_init_with_default_values(self):
        """测试使用默认值初始化"""
        config = {}
        formatter = OutputFormatter(config)
        
        assert formatter.enabled is False
        assert formatter.formats == ['markdown', 'json']
        assert formatter.base_directory == 'runtime/outputs/retrieval'
        assert formatter.filename_template == 'books_{mode}_{timestamp}'
        assert formatter.include_timestamp is True
    
    def test_format_as_markdown(self):
        """测试Markdown格式化"""
        markdown = self.formatter.format_as_markdown(self.sample_results, self.sample_metadata)
        
        # 检查基本结构
        assert '# 图书检索结果 - SINGLE模式' in markdown
        assert '**检索时间**:' in markdown
        assert '**查询内容**: 测试查询' in markdown
        assert '**结果数量**: 2' in markdown
        
        # 检查检索参数
        assert '## 检索参数' in markdown
        assert '- **top_k**: 5' in markdown
        assert '- **min_rating**: 7.0' in markdown
        
        # 检查结果内容
        assert '## 检索结果' in markdown
        assert '[1] 测试书籍1' in markdown
        assert '**作者**: 作者1' in markdown
        assert '**评分**: 8.5' in markdown
        assert '**相似度**: 0.9234' in markdown
        assert '**融合分数**: 0.8756' in markdown
        assert '这是一本测试书籍的简介' in markdown
    
    def test_format_as_markdown_empty_results(self):
        """测试空结果的Markdown格式化"""
        markdown = self.formatter.format_as_markdown([], self.sample_metadata)
        
        assert '😔 未找到匹配的书籍。' in markdown
    
    def test_format_as_json(self):
        """测试JSON格式化"""
        json_str = self.formatter.format_as_json(self.sample_results, self.sample_metadata)
        data = json.loads(json_str)
        
        # 检查基本结构
        assert 'metadata' in data
        assert 'search_parameters' in data
        assert 'results' in data
        
        # 检查元数据
        assert data['metadata']['mode'] == 'single'
        assert data['metadata']['query'] == '测试查询'
        assert data['metadata']['result_count'] == 2
        
        # 检查检索参数
        assert data['search_parameters']['top_k'] == 5
        assert data['search_parameters']['min_rating'] == 7.0
        
        # 检查结果
        assert len(data['results']) == 2
        assert data['results'][0]['title'] == '测试书籍1'
        assert data['results'][0]['author'] == '作者1'
        assert data['results'][0]['rating'] == 8.5
    
    def test_format_as_json_with_douban_fields(self):
        """测试包含豆瓣字段的JSON格式化"""
        results_with_douban = [
            {
                'douban_title': '豆瓣书籍',
                'douban_author': '豆瓣作者',
                'douban_rating': 8.0
            }
        ]
        
        json_str = self.formatter.format_as_json(results_with_douban, self.sample_metadata)
        data = json.loads(json_str)
        
        # 检查字段名转换
        assert data['results'][0]['title'] == '豆瓣书籍'
        assert data['results'][0]['author'] == '豆瓣作者'
        assert data['results'][0]['rating'] == 8.0
    
    def test_save_results_disabled(self):
        """测试禁用输出时的保存"""
        self.formatter.enabled = False
        saved_files = self.formatter.save_results(self.sample_results, self.sample_metadata)
        
        assert saved_files == {}
    
    def test_save_results_no_formats(self):
        """测试无格式配置时的保存"""
        self.formatter.formats = []
        saved_files = self.formatter.save_results(self.sample_results, self.sample_metadata)
        
        assert saved_files == {}
    
    def test_save_results_success(self):
        """测试成功保存结果"""
        saved_files = self.formatter.save_results(self.sample_results, self.sample_metadata)
        
        assert len(saved_files) == 2
        assert 'markdown' in saved_files
        assert 'json' in saved_files
        
        # 检查文件是否存在
        markdown_path = saved_files['markdown']
        json_path = saved_files['json']
        
        assert os.path.exists(markdown_path)
        assert os.path.exists(json_path)
        
        # 检查文件内容
        with open(markdown_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
            assert '# 图书检索结果' in markdown_content
            assert '测试书籍1' in markdown_content
        
        with open(json_path, 'r', encoding='utf-8') as f:
            json_content = json.load(f)
            assert json_content['metadata']['mode'] == 'single'
            assert len(json_content['results']) == 2
    
    def test_save_results_with_unsupported_format(self):
        """测试包含不支持格式的保存"""
        self.formatter.formats = ['markdown', 'unsupported', 'json']
        
        saved_files = self.formatter.save_results(self.sample_results, self.sample_metadata)
        
        # 应该只保存支持的格式
        assert len(saved_files) == 2
        assert 'markdown' in saved_files
        assert 'json' in saved_files
        assert 'unsupported' not in saved_files
    
    def test_save_results_with_query_in_filename(self):
        """测试文件名包含查询内容"""
        self.formatter.filename_template = 'books_{mode}_{query}_{timestamp}'
        
        saved_files = self.formatter.save_results(self.sample_results, self.sample_metadata)
        
        # 检查文件名是否包含查询内容
        for file_path in saved_files.values():
            filename = os.path.basename(file_path)
            assert '测试查询' in filename
    
    @patch('src.core.book_vectorization.output_formatter.logger')
    def test_save_results_error_handling(self, mock_logger):
        """测试保存过程中的错误处理"""
        # 直接修改formatter实例的safe_write_file引用
        original_safe_write_file = self.formatter.__class__.__module__
        
        # 模拟safe_write_file函数抛出异常
        import src.core.book_vectorization.output_formatter as formatter_module
        original_func = formatter_module.safe_write_file
        
        def mock_safe_write_file(*args, **kwargs):
            raise Exception("写入失败")
        
        formatter_module.safe_write_file = mock_safe_write_file
        
        try:
            saved_files = self.formatter.save_results(self.sample_results, self.sample_metadata)
            
            # 应该返回空字典（因为所有格式都失败了）
            assert saved_files == {}
            
            # 应该记录错误日志（每个格式一次）
            assert mock_logger.error.call_count >= 2  # markdown和json各一次
        finally:
            # 恢复原始函数
            formatter_module.safe_write_file = original_func
    
    def test_save_results_without_auto_create_directory(self):
        """测试不自动创建目录时的保存"""
        self.formatter.auto_create_directory = False
        self.formatter.base_directory = '/nonexistent/directory'
        
        # 由于safe_write_file内部会自动创建目录，所以这里应该成功保存
        # 但在实际环境中，如果目录不存在且没有权限，会抛出异常
        # 这里我们测试的是当auto_create_directory=False时的行为
        saved_files = self.formatter.save_results(self.sample_results, self.sample_metadata)
        
        # 应该仍然保存成功，因为safe_write_file会处理目录创建
        assert len(saved_files) == 2
        assert 'markdown' in saved_files
        assert 'json' in saved_files


class TestMdFilenameExtraction:
    """MD文件名提取功能测试类"""
    
    def test_extract_md_filename_success(self):
        """测试正常MD文件名提取"""
        # 测试标准路径
        result = extract_md_filename("runtime/outputs/cross_analysis/20251211_091218_数字平台的情绪操控与劳动异化_g7.md")
        assert result == "20251211_091218_数字平台的情绪操控与劳动异化_g7"
        
        # 测试相对路径
        result = extract_md_filename("./test_file.md")
        assert result == "test_file"
        
        # 测试绝对路径
        result = extract_md_filename("/path/to/test_document.md")
        assert result == "test_document"
        
        # 测试包含特殊字符的文件名
        result = extract_md_filename("path/test-file_with.special@chars.md")
        assert result == "test-file_with.special@chars"
    
    def test_extract_md_filename_empty_path(self):
        """测试空路径处理"""
        result = extract_md_filename("")
        assert result is None
        
        result = extract_md_filename(None)
        assert result is None
    
    def test_extract_md_filename_invalid_path(self):
        """测试无效路径处理"""
        # 测试只有扩展名的路径
        result = extract_md_filename(".md")
        assert result is None
        
        # 测试没有文件名的路径
        result = extract_md_filename("/path/to/")
        assert result is None
    
    @patch('src.core.book_vectorization.output_formatter.logger')
    def test_extract_md_filename_exception_handling(self, mock_logger):
        """测试异常处理"""
        # 模拟Path.stem抛出异常的情况
        with patch('src.core.book_vectorization.output_formatter.Path') as mock_path:
            mock_path.side_effect = Exception("模拟异常")
            
            result = extract_md_filename("test.md")
            assert result is None
            mock_logger.error.assert_called_once()


class TestMdSmartNaming:
    """MD智能命名功能测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'enabled': True,
            'formats': ['markdown', 'json'],
            'base_directory': self.temp_dir,
            'filename_template': 'books_{mode}_{timestamp}',
            'include_timestamp': True,
            'timestamp_format': '%Y%m%d_%H%M%S',
            'auto_create_directory': True
        }
        self.formatter = OutputFormatter(self.config)
        
        # 测试数据
        self.sample_results = [
            {
                'title': '测试书籍1',
                'author': '作者1',
                'rating': 8.5,
                'call_no': 'TP123',
                'summary': '这是一本测试书籍的简介'
            }
        ]
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_results_with_md_filename(self):
        """测试MD解析检索模式的文件命名"""
        metadata = {
            'mode': 'multi',
            'from_md': 'runtime/outputs/cross_analysis/20251211_091218_数字平台的情绪操控与劳动异化_g7.md'
        }
        
        saved_files = self.formatter.save_results(self.sample_results, metadata)
        
        # 检查文件名是否包含MD文件名
        for file_path in saved_files.values():
            filename = os.path.basename(file_path)
            assert "20251211_091218_数字平台的情绪操控与劳动异化_g7_相关书目_" in filename
            assert filename.endswith('.md') or filename.endswith('.json')
    
    def test_save_results_with_md_filename_extraction_failure(self):
        """测试MD文件名提取失败时的降级处理"""
        metadata = {
            'mode': 'multi',
            'from_md': ''  # 空字符串会导致提取失败
        }
        
        saved_files = self.formatter.save_results(self.sample_results, metadata)
        
        # 应该使用默认命名模板
        for file_path in saved_files.values():
            filename = os.path.basename(file_path)
            assert filename.startswith('books_multi_')
            assert "相关书目" not in filename
    
    def test_save_results_without_md_field(self):
        """测试非MD解析检索模式的文件命名"""
        metadata = {
            'mode': 'single',
            'query': '测试查询'
        }
        
        saved_files = self.formatter.save_results(self.sample_results, metadata)
        
        # 应该使用默认命名模板
        for file_path in saved_files.values():
            filename = os.path.basename(file_path)
            assert filename.startswith('books_single_')
            assert "相关书目" not in filename
    
    def test_save_results_with_md_special_characters(self):
        """测试MD文件名包含特殊字符时的处理"""
        metadata = {
            'mode': 'multi',
            'from_md': 'path/test-file_with:invalid*chars.md'
        }
        
        saved_files = self.formatter.save_results(self.sample_results, metadata)
        
        # 检查文件是否存在且内容正确
        for file_path in saved_files.values():
            assert os.path.exists(file_path)
            
            # 检查文件名中的特殊字符是否被正确处理
            filename = os.path.basename(file_path)
            assert "test-file_with_invalid_chars_相关书目_" in filename
            assert ":" not in filename  # 冒号应该被替换
            assert "*" not in filename  # 星号应该被替换
    
    @patch('src.core.book_vectorization.output_formatter.extract_md_filename')
    def test_save_results_with_mock_extraction(self, mock_extract):
        """测试使用mock的MD文件名提取"""
        mock_extract.return_value = "mocked_filename"
        
        metadata = {
            'mode': 'multi',
            'from_md': 'some/path/file.md'
        }
        
        saved_files = self.formatter.save_results(self.sample_results, metadata)
        
        # 验证extract_md_filename被调用
        mock_extract.assert_called_once_with('some/path/file.md')
        
        # 检查文件名是否使用了mock的结果
        for file_path in saved_files.values():
            filename = os.path.basename(file_path)
            assert "mocked_filename_相关书目_" in filename
    
    @patch('src.core.book_vectorization.output_formatter.logger')
    def test_save_results_md_extraction_logging(self, mock_logger):
        """测试MD文件名提取的日志记录"""
        # 测试成功提取的日志
        metadata = {
            'mode': 'multi',
            'from_md': 'test_file.md'
        }
        
        self.formatter.save_results(self.sample_results, metadata)
        
        # 验证成功日志被记录
        mock_logger.info.assert_any_call("检测到MD解析检索模式，使用MD文件名: test_file")
        
        # 测试提取失败的情况
        metadata['from_md'] = ''
        
        # 重置mock调用记录
        mock_logger.reset_mock()
        
        self.formatter.save_results(self.sample_results, metadata)
        
        # 验证至少有一些日志调用发生（具体消息可能因实现而异）
        assert mock_logger.info.called or mock_logger.warning.called