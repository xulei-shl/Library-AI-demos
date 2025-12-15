#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主题筛选器，负责使用LLM评估书籍与文章主题的匹配度

该模块实现了基于大语言模型的书籍主题筛选功能，通过分析文章主题分析报告
和书籍元数据，评估书籍与文章的互文关系质量，提供结构化的评估结果。
"""

import json
from typing import Dict, List, Optional

from src.utils.logger import get_logger
from src.utils.llm.client import UnifiedLLMClient
from src.utils.llm.exceptions import LLMCallError, JSONParseError

logger = get_logger(__name__)


class ThemeScreener:
    """主题筛选器，负责使用LLM评估书籍与文章主题的匹配度"""
    
    def __init__(self, llm_client: UnifiedLLMClient, config: Dict):
        """
        初始化主题筛选器
        
        Args:
            llm_client: 统一LLM客户端实例
            config: 主题筛选配置字典
        """
        self.llm_client = llm_client
        self.config = config
        self.task_name = "theme_screening"
        
        logger.info("主题筛选器初始化完成")
    
    def evaluate_book(self, article_report: str, book_metadata: Dict) -> Dict:
        """
        评估单本书籍与文章主题的匹配度
        
        Args:
            article_report: 文章主题分析报告内容
            book_metadata: 书籍元数据字典，包含书名、作者、内容简介等
            
        Returns:
            包含评估结果的字典，格式为：
            {
                "is_selected": bool,           # 是否通过筛选
                "score": float,                # 1-5分评分
                "evaluation_logic": {
                    "relevance_check": str,    # 主题相关性描述
                    "dimension_match": str     # 维度契合度描述
                },
                "reason": str                  # New Yorker风格评语
            }
            
        Raises:
            LLMCallError: LLM调用失败
            JSONParseError: 结果解析失败
        """
        logger.debug(f"开始评估书籍: {book_metadata.get('豆瓣书名', '未知')}")
        
        # 构建用户输入
        user_prompt = self._build_user_prompt(article_report, book_metadata)
        
        try:
            # 调用LLM
            response = self.llm_client.call(
                task_name=self.task_name,
                user_prompt=user_prompt
            )
            
            # 解析响应
            result = self._parse_llm_response(response)
            
            # 添加元数据
            result["book_barcode"] = book_metadata.get("书目条码", "")
            result["llm_status"] = "success"
            result["error_message"] = ""
            
            # 确保评分是数字类型
            if isinstance(result["score"], str):
                try:
                    result["score"] = float(result["score"])
                except ValueError:
                    logger.warning(f"评分格式不正确，设置为0: {result['score']}")
                    result["score"] = 0.0
            
            logger.debug(f"书籍评估完成: {book_metadata.get('豆瓣书名', '未知')}, "
                        f"是否通过: {result['is_selected']}, 评分: {result['score']}")
            
            return result
            
        except Exception as e:
            logger.error(f"评估书籍时发生错误: {book_metadata.get('豆瓣书名', '未知')}, 错误: {e}")
            
            # 返回错误结果
            return {
                "book_barcode": book_metadata.get("书目条码", ""),
                "is_selected": False,
                "score": 0.0,
                "evaluation_logic": {
                    "relevance_check": "评估失败",
                    "dimension_match": "评估失败"
                },
                "reason": f"评估过程发生错误: {str(e)}",
                "llm_status": "failed",
                "error_message": str(e)
            }
    
    def evaluate_books_batch(self, article_report: str, books_data: List[Dict]) -> List[Dict]:
        """
        批量评估多本书籍
        
        Args:
            article_report: 文章主题分析报告内容
            books_data: 书籍元数据列表
            
        Returns:
            评估结果列表，与输入书籍列表顺序一致。
            失败的项目包含error字段记录错误信息
        """
        logger.info(f"开始批量评估{len(books_data)}本书籍")
        
        results = []
        
        for i, book_metadata in enumerate(books_data):
            logger.info(f"评估进度: {i+1}/{len(books_data)} - {book_metadata.get('豆瓣书名', '未知')}")
            
            try:
                result = self.evaluate_book(article_report, book_metadata)
                results.append(result)
            except Exception as e:
                logger.error(f"批量评估中处理书籍时发生错误: {book_metadata.get('豆瓣书名', '未知')}, 错误: {e}")
                
                # 添加错误结果
                error_result = {
                    "book_barcode": book_metadata.get("书目条码", ""),
                    "is_selected": False,
                    "score": 0.0,
                    "evaluation_logic": {
                        "relevance_check": "评估失败",
                        "dimension_match": "评估失败"
                    },
                    "reason": f"评估过程发生错误: {str(e)}",
                    "llm_status": "failed",
                    "error_message": str(e)
                }
                results.append(error_result)
        
        # 统计结果
        selected_count = sum(1 for r in results if r.get("is_selected", False))
        success_count = sum(1 for r in results if r.get("llm_status") == "success")
        
        logger.info(f"批量评估完成: 总数{len(books_data)}, 成功{success_count}, "
                   f"通过筛选{selected_count}")
        
        return results
    
    def _build_user_prompt(self, article_report: str, book_metadata: Dict) -> str:
        """
        构建用户输入提示词
        
        Args:
            article_report: 文章主题分析报告
            book_metadata: 书籍元数据
            
        Returns:
            格式化的用户输入字符串
        """
        # 格式化书籍信息
        book_info = f"""
书目条码id: {book_metadata.get('书目条码', '')}
书名: {book_metadata.get('豆瓣书名', '')}
副标题: {book_metadata.get('豆瓣副标题', '')}
作者: {book_metadata.get('豆瓣作者', '')}
丛书: {book_metadata.get('豆瓣丛书', '')}
内容简介: {book_metadata.get('豆瓣内容简介', '')}
作者简介: {book_metadata.get('豆瓣作者简介', '')}
目录: {book_metadata.get('豆瓣目录', '')}
        """.strip()
        
        # 构建完整提示词
        user_prompt = f"""
请根据以下文章主题分析报告和候选图书信息，评估这本书是否能与文章构成完美的"互文"关系。

## 文章主题分析报告
{article_report}

## 候选图书信息
{book_info}

请按照要求输出JSON格式的评估结果。
        """.strip()
        
        return user_prompt
    
    def _parse_llm_response(self, response: str) -> Dict:
        """
        解析LLM响应
        
        Args:
            response: LLM原始响应
            
        Returns:
            解析后的评估结果字典
            
        Raises:
            JSONParseError: JSON解析失败
        """
        try:
            # 尝试直接解析JSON
            result = json.loads(response)
            
            # 验证必需字段
            required_fields = ["is_selected", "score", "evaluation_logic", "reason"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"响应缺少必需字段: {field}")
            
            # 验证数据类型
            if not isinstance(result["is_selected"], bool):
                raise ValueError("is_selected 必须是布尔值")
            
            # 尝试转换评分为数字
            if isinstance(result["score"], str):
                try:
                    result["score"] = float(result["score"])
                except ValueError:
                    raise ValueError("score 必须是数字，无法转换字符串")
            
            if not isinstance(result["score"], (int, float)):
                raise ValueError("score 必须是数字")
            
            if not isinstance(result["evaluation_logic"], dict):
                raise ValueError("evaluation_logic 必须是字典")
            
            if not isinstance(result["reason"], str):
                raise ValueError("reason 必须是字符串")
            
            # 验证评分范围
            score = float(result["score"])
            if score < 1 or score > 5:
                raise ValueError("score 必须在1-5之间")
            
            # 确保evaluation_logic包含必需字段
            logic = result["evaluation_logic"]
            if "relevance_check" not in logic or "dimension_match" not in logic:
                raise ValueError("evaluation_logic 必须包含 relevance_check 和 dimension_match 字段")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {response[:200]}..., 错误: {e}")
            raise JSONParseError(f"无法解析LLM响应为JSON: {e}")
        except ValueError as e:
            logger.error(f"响应格式验证失败: {e}")
            raise JSONParseError(f"响应格式不符合要求: {e}")
        except Exception as e:
            logger.error(f"解析LLM响应时发生未知错误: {e}")
            raise JSONParseError(f"解析响应时发生错误: {e}")