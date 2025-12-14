#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图书过滤器单元测试
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.book_vectorization.filter import BookFilter


class TestBookFilter:
    """图书过滤器测试类"""
    
    @pytest.fixture
    def filter_config(self):
        """测试配置"""
        return {
            'required_fields': ['douban_title', 'douban_author', 'douban_summary', 'douban_catalog'],
            'rating_thresholds': {
                'B': 8.2,
                'C': 7.5,
                'D': 7.1,
                'default': 7.5
            }
        }
    
    @pytest.fixture
    def book_filter(self, filter_config):
        """创建过滤器实例"""
        return BookFilter(filter_config, db_reader=None)
    
    def test_check_required_fields_pass(self, book_filter):
        """测试必填字段检查 - 通过"""
        book = {
            'id': 1,
            'douban_title': '测试书籍',
            'douban_author': '测试作者',
            'douban_summary': '测试简介',
            'douban_catalog': '测试目录'
        }
        
        assert book_filter._check_required_fields(book) is True
    
    def test_check_required_fields_missing(self, book_filter):
        """测试必填字段检查 - 缺少字段"""
        book = {
            'id': 1,
            'douban_title': '测试书籍',
            'douban_author': '测试作者',
            # 缺少 douban_summary
            'douban_catalog': '测试目录'
        }
        
        assert book_filter._check_required_fields(book) is False
    
    def test_check_required_fields_empty(self, book_filter):
        """测试必填字段检查 - 空字符串"""
        book = {
            'id': 1,
            'douban_title': '测试书籍',
            'douban_author': '',  # 空字符串
            'douban_summary': '测试简介',
            'douban_catalog': '测试目录'
        }
        
        assert book_filter._check_required_fields(book) is False
    
    def test_check_rating_threshold_pass(self, book_filter):
        """测试评分阈值检查 - 通过"""
        book = {
            'id': 1,
            'call_no': 'B123',
            'douban_rating': 8.5  # 大于 B 类阈值 8.2
        }
        
        assert book_filter._check_rating_threshold(book) is True
    
    def test_check_rating_threshold_equal(self, book_filter):
        """测试评分阈值检查 - 等于阈值"""
        book = {
            'id': 1,
            'call_no': 'B123',
            'douban_rating': 8.2  # 等于 B 类阈值 8.2
        }
        
        assert book_filter._check_rating_threshold(book) is True
    
    def test_check_rating_threshold_fail(self, book_filter):
        """测试评分阈值检查 - 未达标"""
        book = {
            'id': 1,
            'call_no': 'B123',
            'douban_rating': 8.0  # 小于 B 类阈值 8.2
        }
        
        assert book_filter._check_rating_threshold(book) is False
    
    def test_check_rating_threshold_default(self, book_filter):
        """测试评分阈值检查 - 使用默认阈值"""
        book = {
            'id': 1,
            'call_no': 'X123',  # X 类未配置，使用默认阈值 7.5
            'douban_rating': 7.8
        }
        
        assert book_filter._check_rating_threshold(book) is True
    
    def test_check_rating_threshold_no_rating(self, book_filter):
        """测试评分阈值检查 - 缺少评分"""
        book = {
            'id': 1,
            'call_no': 'B123'
            # 缺少 douban_rating
        }
        
        assert book_filter._check_rating_threshold(book) is False
    
    def test_apply_filter(self, book_filter):
        """测试完整过滤流程"""
        books = [
            # 符合条件
            {
                'id': 1,
                'douban_title': '书籍1',
                'douban_author': '作者1',
                'douban_summary': '简介1',
                'douban_catalog': '目录1',
                'call_no': 'B123',
                'douban_rating': 8.5
            },
            # 缺少必填字段
            {
                'id': 2,
                'douban_title': '书籍2',
                'douban_author': '作者2',
                # 缺少 douban_summary
                'douban_catalog': '目录2',
                'call_no': 'C123',
                'douban_rating': 8.0
            },
            # 评分未达标
            {
                'id': 3,
                'douban_title': '书籍3',
                'douban_author': '作者3',
                'douban_summary': '简介3',
                'douban_catalog': '目录3',
                'call_no': 'B123',
                'douban_rating': 7.0  # 小于 B 类阈值 8.2
            },
            # 符合条件
            {
                'id': 4,
                'douban_title': '书籍4',
                'douban_author': '作者4',
                'douban_summary': '简介4',
                'douban_catalog': '目录4',
                'call_no': 'D123',
                'douban_rating': 7.5  # 大于 D 类阈值 7.1
            }
        ]
        
        filtered = book_filter.apply(books)
        
        assert len(filtered) == 2
        assert filtered[0]['id'] == 1
        assert filtered[1]['id'] == 4


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
