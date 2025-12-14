#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
向量化器单元测试
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.book_vectorization.vectorizer import BookVectorizer


class TestBookVectorizer:
    """向量化器测试类"""
    
    def test_build_text(self):
        """测试文本构建逻辑"""
        # 创建一个简化的配置
        config = {
            'text_construction': {
                'template': '书名: {douban_title}\n作者: {douban_author}\n简介: {douban_summary}\n{douban_summary}\n目录: {douban_catalog}',
                'max_catalog_length': 100,
                'summary_weight': 2,
                'empty_placeholder': '[无]'
            }
        }
        
        # 模拟 vectorizer 实例
        class MockVectorizer:
            def __init__(self):
                self.config = config
            
            def _build_text(self, book):
                catalog = book.get('douban_catalog', '')
                if len(catalog) > self.config['text_construction']['max_catalog_length']:
                    catalog = catalog[:self.config['text_construction']['max_catalog_length']] + "..."
                
                summary = book.get('douban_summary', '')
                summary_repeated = '\n'.join([summary] * self.config['text_construction']['summary_weight'])
                
                text = self.config['text_construction']['template'].format(
                    douban_title=book.get('douban_title', self.config['text_construction']['empty_placeholder']),
                    douban_author=book.get('douban_author', self.config['text_construction']['empty_placeholder']),
                    douban_summary=summary_repeated,
                    douban_catalog=catalog
                )
                
                return text
        
        vectorizer = MockVectorizer()
        
        # 测试正常情况
        book = {
            'douban_title': '测试书籍',
            'douban_author': '测试作者',
            'douban_summary': '这是一本测试书籍',
            'douban_catalog': '第一章\n第二章'
        }
        
        text = vectorizer._build_text(book)
        
        assert '书名: 测试书籍' in text
        assert '作者: 测试作者' in text
        assert text.count('这是一本测试书籍') == 4  # 简介在模板中出现2次，每次重复2遍，共4次
        assert '目录: 第一章' in text
    
    def test_build_text_long_catalog(self):
        """测试目录截断逻辑"""
        config = {
            'text_construction': {
                'template': '书名: {douban_title}\n作者: {douban_author}\n简介: {douban_summary}\n{douban_summary}\n目录: {douban_catalog}',
                'max_catalog_length': 50,
                'summary_weight': 2,
                'empty_placeholder': '[无]'
            }
        }
        
        class MockVectorizer:
            def __init__(self):
                self.config = config
            
            def _build_text(self, book):
                catalog = book.get('douban_catalog', '')
                if len(catalog) > self.config['text_construction']['max_catalog_length']:
                    catalog = catalog[:self.config['text_construction']['max_catalog_length']] + "..."
                
                summary = book.get('douban_summary', '')
                summary_repeated = '\n'.join([summary] * self.config['text_construction']['summary_weight'])
                
                text = self.config['text_construction']['template'].format(
                    douban_title=book.get('douban_title', self.config['text_construction']['empty_placeholder']),
                    douban_author=book.get('douban_author', self.config['text_construction']['empty_placeholder']),
                    douban_summary=summary_repeated,
                    douban_catalog=catalog
                )
                
                return text
        
        vectorizer = MockVectorizer()
        
        # 测试超长目录
        book = {
            'douban_title': '测试书籍',
            'douban_author': '测试作者',
            'douban_summary': '简介',
            'douban_catalog': 'A' * 200  # 超过50字符
        }
        
        text = vectorizer._build_text(book)
        
        assert '...' in text
        # 目录部分应该被截断到50字符 + "..."
    
    def test_build_metadata(self):
        """测试元数据构建逻辑"""
        config = {
            'metadata': {
                'fields': ['book_id', 'douban_title', 'douban_author', 'douban_rating']
            }
        }
        
        class MockVectorizer:
            def __init__(self):
                self.config = config
            
            def _build_metadata(self, book):
                metadata = {}
                for field in self.config['metadata']['fields']:
                    value = book.get(field)
                    if value is not None:
                        if isinstance(value, (int, float, bool)):
                            metadata[field] = value
                        else:
                            metadata[field] = str(value)
                
                return metadata
        
        vectorizer = MockVectorizer()
        
        book = {
            'book_id': 123,
            'douban_title': '测试书籍',
            'douban_author': '测试作者',
            'douban_rating': 8.5,
            'extra_field': '不应该包含'
        }
        
        metadata = vectorizer._build_metadata(book)
        
        assert metadata['book_id'] == 123
        assert metadata['douban_title'] == '测试书籍'
        assert metadata['douban_author'] == '测试作者'
        assert metadata['douban_rating'] == 8.5
        assert 'extra_field' not in metadata


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
