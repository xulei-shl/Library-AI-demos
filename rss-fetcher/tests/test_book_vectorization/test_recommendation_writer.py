#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RecommendationWriter单元测试

测试推荐导语生成器的各项功能，包括正常路径、边界条件和异常路径。
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from src.core.book_vectorization.excel_reader import ExcelReader
from src.core.book_vectorization.recommendation_writer import RecommendationWriter
from src.utils.llm.exceptions import ProviderError


class TestRecommendationWriter:
    """RecommendationWriter测试类"""
    
    def setup_method(self):
        """测试前准备"""
        # 创建模拟的LLM客户端
        self.mock_llm_client = MagicMock()
        
        # 创建推荐导语生成器
        self.recommendation_writer = RecommendationWriter(
            llm_client=self.mock_llm_client,
            config={}
        )
        
        # 创建测试数据
        self.test_article_report = """
# 文章主题分析报告

## 核心主题
数字时代的身份认同与技术异化

## 关键词
数字身份、技术异化、自我认知、社交媒体

## 文章摘要
本文探讨了在数字时代，人们如何在社交媒体和网络空间中构建和表达自我身份，以及这种数字化存在形式如何影响个体的自我认知和社会关系。
"""
        
        self.test_books_data = [
            {
                "书目条码": "B001",
                "豆瓣书名": "数字时代的自我",
                "豆瓣副标题": "社交媒体时代的身份认同",
                "豆瓣作者": "张三",
                "豆瓣丛书": "数字文化研究丛书",
                "豆瓣内容简介": "本书探讨了数字时代个体身份的构建与表达",
                "豆瓣作者简介": "张三，数字文化研究专家",
                "豆瓣目录": "第一章：数字身份的概念\n第二章：社交媒体与自我表达",
                "初评结果": True,
                "初评理由": "与主题高度相关"
            },
            {
                "书目条码": "B002",
                "豆瓣书名": "技术异化论",
                "豆瓣副标题": "现代技术对人的异化",
                "豆瓣作者": "李四",
                "豆瓣丛书": "技术哲学丛书",
                "豆瓣内容简介": "从哲学角度分析技术对人的异化现象",
                "豆瓣作者简介": "李四，技术哲学研究者",
                "豆瓣目录": "第一章：异化的概念\n第二章：技术异化的表现形式",
                "初评结果": "TRUE",  # 字符串形式的TRUE
                "初评理由": "提供了理论深度"
            }
        ]
        
        self.test_recommendation_content = """
# 数字牢笼里的金丝雀：关于算法控制与自由意志的阅读自救

## 策展人手记

在数字时代的洪流中，我们每个人都在无形中被算法塑造，被数据定义。社交媒体上的每一次点赞、每一条评论，都在构建着一个被量化的自我。这种数字化存在形式让我们获得了前所未有的连接，却也让我们陷入了更深层的孤独。

碎片化的阅读只能让我们看到问题的表象，而深度阅读则能帮助我们理解背后的逻辑。本次精选的书单，从数字身份的构建到技术异化的哲学思考，为我们提供了一幅完整的认知地图。

## 阅读谱系

### 理论的基石
1. **《技术异化论》- 李四**
   如果说之前的文章让你看到了现象的残酷，这本书则带你回溯了残酷诞生的源头。

### 现象的观察
2. **《数字时代的自我》- 张三**
   从社交媒体时代的身份认同出发，深入分析数字化存在对个体的影响。

## 结语：金句

"在算法的牢笼中，我们依然可以保持人性的自由。"
"""
    
    def test_init(self):
        """测试初始化"""
        assert self.recommendation_writer is not None
        assert self.recommendation_writer.llm_client == self.mock_llm_client
        assert isinstance(self.recommendation_writer.excel_reader, ExcelReader)
    
    def test_generate_recommendation_normal(self):
        """测试正常生成推荐导语"""
        # 模拟LLM调用
        self.mock_llm_client.call.return_value = self.test_recommendation_content
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as article_file:
            article_file.write(self.test_article_report)
            article_path = article_file.name
            
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as excel_file:
            excel_path = excel_file.name
            
        try:
            # 模拟ExcelReader的返回值
            with patch.object(self.recommendation_writer.excel_reader, 'load_books_data', return_value=self.test_books_data):
                with patch.object(self.recommendation_writer.excel_reader, 'filter_selected_books', return_value=self.test_books_data):
                    # 生成推荐导语
                    result_path = self.recommendation_writer.generate_recommendation(article_path, excel_path)
                    
                    # 验证结果
                    assert result_path is not None
                    assert result_path.endswith('.md')
                    assert Path(result_path).exists()
                    
                    # 验证文件内容
                    with open(result_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        assert content == self.test_recommendation_content
                    
                    # 验证LLM调用
                    self.mock_llm_client.call.assert_called_once()
                    
        finally:
            # 清理临时文件
            for path in [article_path, excel_path, result_path]:
                if os.path.exists(path):
                    os.unlink(path)
    
    def test_generate_recommendation_article_not_exist(self):
        """测试文章报告文件不存在"""
        with pytest.raises(FileNotFoundError, match="文章分析报告文件不存在"):
            self.recommendation_writer.generate_recommendation("nonexistent.md", "test.xlsx")
    
    def test_generate_recommendation_excel_not_exist(self):
        """测试Excel文件不存在"""
        # 创建临时文章文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as article_file:
            article_file.write(self.test_article_report)
            article_path = article_file.name
            
        try:
            with pytest.raises(Exception):
                self.recommendation_writer.generate_recommendation(article_path, "nonexistent.xlsx")
                
        finally:
            # 清理临时文件
            if os.path.exists(article_path):
                os.unlink(article_path)
    
    def test_generate_recommendation_no_selected_books(self):
        """测试没有通过筛选的书籍"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as article_file:
            article_file.write(self.test_article_report)
            article_path = article_file.name
            
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as excel_file:
            excel_path = excel_file.name
            
        try:
            # 模拟ExcelReader返回空列表
            with patch.object(self.recommendation_writer.excel_reader, 'load_books_data', return_value=self.test_books_data):
                with patch.object(self.recommendation_writer.excel_reader, 'filter_selected_books', return_value=[]):
                    with pytest.raises(ValueError, match="没有通过主题筛选的书籍"):
                        self.recommendation_writer.generate_recommendation(article_path, excel_path)
                        
        finally:
            # 清理临时文件
            for path in [article_path, excel_path]:
                if os.path.exists(path):
                    os.unlink(path)
    
    def test_generate_recommendation_llm_error(self):
        """测试LLM调用失败"""
        # 模拟LLM调用失败
        self.mock_llm_client.call.side_effect = ProviderError("test_provider", "LLM调用失败")
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as article_file:
            article_file.write(self.test_article_report)
            article_path = article_file.name
            
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as excel_file:
            excel_path = excel_file.name
            
        try:
            # 模拟ExcelReader的返回值
            with patch.object(self.recommendation_writer.excel_reader, 'load_books_data', return_value=self.test_books_data):
                with patch.object(self.recommendation_writer.excel_reader, 'filter_selected_books', return_value=self.test_books_data):
                    with pytest.raises(ProviderError):
                        self.recommendation_writer.generate_recommendation(article_path, excel_path)
                        
        finally:
            # 清理临时文件
            for path in [article_path, excel_path]:
                if os.path.exists(path):
                    os.unlink(path)
    
    def test_load_article_report_normal(self):
        """测试正常加载文章报告"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp_file:
            tmp_file.write(self.test_article_report)
            temp_path = tmp_file.name
            
        try:
            # 加载文章报告
            result = self.recommendation_writer._load_article_report(temp_path)
            
            # 验证结果
            assert result == self.test_article_report
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_load_article_report_not_exist(self):
        """测试文件不存在"""
        with pytest.raises(FileNotFoundError, match="文章分析报告文件不存在"):
            self.recommendation_writer._load_article_report("nonexistent.md")
    
    def test_load_article_report_empty(self):
        """测试空文件"""
        # 创建临时空文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp_file:
            temp_path = tmp_file.name
            
        try:
            with pytest.raises(ValueError, match="文章分析报告文件为空"):
                self.recommendation_writer._load_article_report(temp_path)
                
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_build_user_prompt(self):
        """测试构建用户提示词"""
        # 构建用户提示词
        result = self.recommendation_writer._build_user_prompt(self.test_article_report, self.test_books_data)
        
        # 验证结果
        assert "文章主题分析报告" in result
        assert self.test_article_report in result
        assert "待选书目列表" in result
        assert "B001" in result
        assert "数字时代的自我" in result
        assert "B002" in result
        assert "技术异化论" in result
    
    def test_save_recommendation(self):
        """测试保存推荐导语"""
        # 创建临时Excel文件路径
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as excel_file:
            excel_path = excel_file.name
            
        try:
            # 保存推荐导语
            result_path = self.recommendation_writer._save_recommendation(self.test_recommendation_content, excel_path)
            
            # 验证结果
            assert result_path is not None
            assert result_path.endswith('.md')
            assert Path(result_path).exists()
            
            # 验证文件内容
            with open(result_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert content == self.test_recommendation_content
                
        finally:
            # 清理临时文件
            for path in [excel_path, result_path]:
                if os.path.exists(path):
                    os.unlink(path)