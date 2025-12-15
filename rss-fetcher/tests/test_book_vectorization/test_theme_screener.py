#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主题筛选器单元测试

测试主题筛选器的核心功能，包括单本书籍评估、批量评估、错误处理等。
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.core.book_vectorization.theme_screener import ThemeScreener
from src.utils.llm.exceptions import LLMCallError, JSONParseError


class TestThemeScreener:
    """主题筛选器测试类"""
    
    @pytest.fixture
    def mock_llm_client(self):
        """模拟LLM客户端"""
        mock_client = Mock()
        return mock_client
    
    @pytest.fixture
    def theme_screener(self, mock_llm_client):
        """创建主题筛选器实例"""
        config = {}
        return ThemeScreener(mock_llm_client, config)
    
    @pytest.fixture
    def sample_article_report(self):
        """示例文章主题分析报告"""
        return """
        # 文章主题分析报告
        
        ## 核心主题
        数字时代的身份认同与社交媒体影响
        
        ## 关键词
        身份认同、社交媒体、数字时代、自我呈现、虚拟空间
        
        ## 摘要
        本文探讨了在数字时代背景下，个体如何通过社交媒体平台进行身份建构和自我呈现。
        分析了虚拟空间中的身份流动性、社交互动对自我认知的影响，以及数字身份与现实身份的冲突与融合。
        """
    
    @pytest.fixture
    def sample_book_metadata(self):
        """示例书籍元数据"""
        return {
            "书目条码": "123456789",
            "豆瓣书名": "数字时代的自我：社交媒体与身份认同",
            "豆瓣副标题": "虚拟空间中的身份建构研究",
            "豆瓣作者": "张三",
            "豆瓣丛书": "数字文化研究丛书",
            "豆瓣内容简介": "本书深入探讨了数字时代社交媒体对个体身份认同的影响，分析了虚拟空间中的自我呈现机制。",
            "豆瓣作者简介": "张三，数字社会学专家，长期关注社交媒体与身份认同研究。",
            "豆瓣目录": "第一章 数字身份的兴起\n第二章 社交媒体与自我呈现\n第三章 虚拟空间的身份流动性"
        }
    
    @pytest.fixture
    def sample_llm_response(self):
        """示例LLM响应"""
        return json.dumps({
            "is_selected": True,
            "score": 4.5,
            "evaluation_logic": {
                "relevance_check": "高相关性",
                "dimension_match": "文章探讨数字身份，书籍深入分析社交媒体身份建构，契合度高"
            },
            "reason": "当文章揭示了数字时代身份认同的复杂性时，这本书为我们提供了理解这一现象的理论框架。"
        })
    
    def test_init(self, mock_llm_client):
        """测试初始化"""
        config = {"test": "value"}
        screener = ThemeScreener(mock_llm_client, config)
        
        assert screener.llm_client == mock_llm_client
        assert screener.config == config
        assert screener.task_name == "theme_screening"
    
    def test_evaluate_book_success(self, theme_screener, mock_llm_client, 
                                 sample_article_report, sample_book_metadata, 
                                 sample_llm_response):
        """测试单本书籍评估成功场景"""
        # 设置模拟响应
        mock_llm_client.call.return_value = sample_llm_response
        
        # 执行评估
        result = theme_screener.evaluate_book(sample_article_report, sample_book_metadata)
        
        # 验证结果
        assert result["is_selected"] is True
        assert result["score"] == 4.5
        assert result["evaluation_logic"]["relevance_check"] == "高相关性"
        assert "理解这一现象的理论框架" in result["reason"]
        assert result["book_barcode"] == "123456789"
        assert result["llm_status"] == "success"
        assert result["error_message"] == ""
        
        # 验证LLM调用
        mock_llm_client.call.assert_called_once()
        call_args = mock_llm_client.call.call_args
        assert call_args[1]["task_name"] == "theme_screening"
        assert sample_article_report in call_args[1]["user_prompt"]
        assert sample_book_metadata["豆瓣书名"] in call_args[1]["user_prompt"]
    
    def test_evaluate_book_llm_failure(self, theme_screener, mock_llm_client,
                                     sample_article_report, sample_book_metadata):
        """测试LLM调用失败的重试机制"""
        # 设置模拟异常
        mock_llm_client.call.side_effect = LLMCallError("API调用失败")
        
        # 执行评估
        result = theme_screener.evaluate_book(sample_article_report, sample_book_metadata)
        
        # 验证错误处理
        assert result["is_selected"] is False
        assert result["score"] == 0.0
        assert result["llm_status"] == "failed"
        assert "API调用失败" in result["error_message"]
        assert result["book_barcode"] == "123456789"
    
    def test_evaluate_book_json_parse_failure(self, theme_screener, mock_llm_client,
                                          sample_article_report, sample_book_metadata):
        """测试JSON解析失败的修复机制"""
        # 设置无效JSON响应
        mock_llm_client.call.return_value = "这不是有效的JSON格式"
        
        # 执行评估
        result = theme_screener.evaluate_book(sample_article_report, sample_book_metadata)
        
        # 验证错误处理
        assert result["is_selected"] is False
        assert result["score"] == 0.0
        assert result["llm_status"] == "failed"
        assert "JSON" in result["error_message"]
    
    def test_evaluate_book_invalid_response_format(self, theme_screener, mock_llm_client,
                                               sample_article_report, sample_book_metadata):
        """测试无效响应格式的处理"""
        # 设置缺少必需字段的响应
        invalid_response = json.dumps({
            "is_selected": True,
            "score": 4.5
            # 缺少 evaluation_logic 和 reason
        })
        mock_llm_client.call.return_value = invalid_response
        
        # 执行评估
        result = theme_screener.evaluate_book(sample_article_report, sample_book_metadata)
        
        # 验证错误处理
        assert result["is_selected"] is False
        assert result["score"] == 0.0
        assert result["llm_status"] == "failed"
        assert "格式不符合要求" in result["error_message"]
    
    def test_evaluate_books_batch_success(self, theme_screener, mock_llm_client,
                                       sample_article_report, sample_llm_response):
        """测试批量评估成功场景"""
        # 设置模拟响应
        mock_llm_client.call.return_value = sample_llm_response
        
        # 创建多本书籍数据
        books_data = [
            {
                "书目条码": "123456789",
                "豆瓣书名": f"书籍{i}",
                "豆瓣内容简介": f"书籍{i}的内容简介"
            }
            for i in range(3)
        ]
        
        # 执行批量评估
        results = theme_screener.evaluate_books_batch(sample_article_report, books_data)
        
        # 验证结果
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result["is_selected"] is True
            assert result["score"] == 4.5
            assert result["book_barcode"] == books_data[i]["书目条码"]
            assert result["llm_status"] == "success"
        
        # 验证LLM调用次数
        assert mock_llm_client.call.call_count == 3
    
    def test_evaluate_books_batch_mixed_results(self, theme_screener, mock_llm_client,
                                            sample_article_report, sample_llm_response):
        """测试批量评估中部分成功部分失败的场景"""
        # 设置模拟响应：第一次成功，第二次失败，第三次成功
        mock_llm_client.call.side_effect = [
            sample_llm_response,
            LLMCallError("API调用失败"),
            sample_llm_response
        ]
        
        # 创建三本书籍数据
        books_data = [
            {
                "书目条码": f"12345678{i}",
                "豆瓣书名": f"书籍{i}",
                "豆瓣内容简介": f"书籍{i}的内容简介"
            }
            for i in range(3)
        ]
        
        # 执行批量评估
        results = theme_screener.evaluate_books_batch(sample_article_report, books_data)
        
        # 验证结果
        assert len(results) == 3
        assert results[0]["llm_status"] == "success"
        assert results[1]["llm_status"] == "failed"
        assert results[2]["llm_status"] == "success"
    
    def test_evaluate_books_batch_empty_input(self, theme_screener, sample_article_report):
        """测试空输入的处理"""
        # 执行批量评估
        results = theme_screener.evaluate_books_batch(sample_article_report, [])
        
        # 验证结果
        assert len(results) == 0
    
    def test_build_user_prompt(self, theme_screener, sample_article_report, sample_book_metadata):
        """测试用户输入构建"""
        # 构建用户提示词
        user_prompt = theme_screener._build_user_prompt(sample_article_report, sample_book_metadata)
        
        # 验证内容
        assert "文章主题分析报告" in user_prompt
        assert "候选图书信息" in user_prompt
        assert sample_article_report in user_prompt
        assert sample_book_metadata["豆瓣书名"] in user_prompt
        assert sample_book_metadata["书目条码"] in user_prompt
        assert sample_book_metadata["豆瓣内容简介"] in user_prompt
    
    def test_parse_llm_response_success(self, theme_screener, sample_llm_response):
        """测试LLM响应解析成功"""
        # 解析响应
        result = theme_screener._parse_llm_response(sample_llm_response)
        
        # 验证解析结果
        assert result["is_selected"] is True
        assert result["score"] == 4.5
        assert result["evaluation_logic"]["relevance_check"] == "高相关性"
        assert "理论框架" in result["reason"]
    
    def test_parse_llm_response_invalid_json(self, theme_screener):
        """测试无效JSON解析"""
        # 测试无效JSON
        with pytest.raises(JSONParseError):
            theme_screener._parse_llm_response("这不是有效的JSON")
    
    def test_parse_llm_response_missing_fields(self, theme_screener):
        """测试缺少必需字段的响应"""
        # 创建缺少字段的响应
        invalid_response = json.dumps({
            "is_selected": True,
            "score": 4.5
            # 缺少其他必需字段
        })
        
        # 测试解析
        with pytest.raises(JSONParseError):
            theme_screener._parse_llm_response(invalid_response)
    
    def test_parse_llm_response_invalid_types(self, theme_screener):
        """测试无效数据类型的响应"""
        # 创建类型错误的响应
        invalid_response = json.dumps({
            "is_selected": "true",  # 应该是布尔值
            "score": 4.5,
            "evaluation_logic": {
                "relevance_check": "高相关性",
                "dimension_match": "契合度高"
            },
            "reason": "测试评语"
        })
        
        # 测试解析
        with pytest.raises(JSONParseError):
            theme_screener._parse_llm_response(invalid_response)
    
    def test_parse_llm_response_invalid_score(self, theme_screener):
        """测试无效评分范围的响应"""
        # 创建超出范围的评分
        invalid_response = json.dumps({
            "is_selected": True,
            "score": 6.0,  # 超出1-5范围
            "evaluation_logic": {
                "relevance_check": "高相关性",
                "dimension_match": "契合度高"
            },
            "reason": "测试评语"
        })
        
        # 测试解析
        with pytest.raises(JSONParseError):
            theme_screener._parse_llm_response(invalid_response)