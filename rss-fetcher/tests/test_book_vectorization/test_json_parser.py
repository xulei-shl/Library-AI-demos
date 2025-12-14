#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JSON解析器单元测试
"""

import json
import pytest
import tempfile
from pathlib import Path
from src.core.book_vectorization.json_parser import JsonParser


class TestJsonParser:
    """JSON解析器测试类"""
    
    def test_extract_book_ids_success(self):
        """测试成功提取book_id"""
        # 创建临时JSON文件
        test_data = {
            "metadata": {
                "mode": "multi",
                "result_count": 2
            },
            "results": [
                {
                    "book_id": 123,
                    "title": "测试书籍1",
                    "embedding_id": "book_123_1234567890"
                },
                {
                    "book_id": 456,
                    "title": "测试书籍2",
                    "embedding_id": "book_456_1234567890"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
            temp_file = f.name
        
        try:
            parser = JsonParser()
            book_ids = parser.extract_book_ids(temp_file)
            
            assert book_ids == [123, 456]
        finally:
            Path(temp_file).unlink()
    
    def test_extract_book_ids_file_not_found(self):
        """测试文件不存在的情况"""
        parser = JsonParser()
        
        with pytest.raises(FileNotFoundError, match="JSON文件不存在"):
            parser.extract_book_ids("nonexistent_file.json")
    
    def test_extract_book_ids_invalid_json(self):
        """测试无效JSON格式"""
        # 创建无效JSON文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            f.write("{ invalid json }")
            temp_file = f.name
        
        try:
            parser = JsonParser()
            
            with pytest.raises(ValueError, match="JSON文件格式错误"):
                parser.extract_book_ids(temp_file)
        finally:
            Path(temp_file).unlink()
    
    def test_extract_book_ids_missing_results(self):
        """测试缺少results字段"""
        test_data = {
            "metadata": {
                "mode": "multi"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
            temp_file = f.name
        
        try:
            parser = JsonParser()
            
            with pytest.raises(ValueError, match="JSON文件缺少'results'字段"):
                parser.extract_book_ids(temp_file)
        finally:
            Path(temp_file).unlink()
    
    def test_extract_book_ids_invalid_results_type(self):
        """测试results字段不是列表"""
        test_data = {
            "results": "not a list"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
            temp_file = f.name
        
        try:
            parser = JsonParser()
            
            with pytest.raises(ValueError, match="'results'字段不是列表类型"):
                parser.extract_book_ids(temp_file)
        finally:
            Path(temp_file).unlink()
    
    def test_extract_book_ids_missing_book_id(self):
        """测试结果项缺少book_id"""
        test_data = {
            "results": [
                {
                    "title": "测试书籍",
                    "embedding_id": "book_123_1234567890"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
            temp_file = f.name
        
        try:
            parser = JsonParser()
            book_ids = parser.extract_book_ids(temp_file)
            
            assert book_ids == []
        finally:
            Path(temp_file).unlink()
    
    def test_extract_book_ids_invalid_book_id(self):
        """测试无效的book_id"""
        test_data = {
            "results": [
                {
                    "book_id": "not_a_number",
                    "title": "测试书籍"
                },
                {
                    "book_id": 123,
                    "title": "测试书籍2"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
            temp_file = f.name
        
        try:
            parser = JsonParser()
            book_ids = parser.extract_book_ids(temp_file)
            
            assert book_ids == [123]
        finally:
            Path(temp_file).unlink()
    
    def test_extract_book_ids_empty_results(self):
        """测试空的results列表"""
        test_data = {
            "results": []
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
            temp_file = f.name
        
        try:
            parser = JsonParser()
            book_ids = parser.extract_book_ids(temp_file)
            
            assert book_ids == []
        finally:
            Path(temp_file).unlink()