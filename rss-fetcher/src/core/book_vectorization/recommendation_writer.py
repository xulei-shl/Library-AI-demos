#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
推荐导语生成器，负责根据文章分析报告和书籍列表生成推荐导语

该模块实现了推荐导语的生成功能，主要根据文章分析报告和通过主题筛选的书籍列表，
使用大语言模型生成专业的推荐导语，包含标题、策展人手记、阅读谱系和结语四个部分。
"""

import os
from pathlib import Path
from typing import Dict, List

from src.core.book_vectorization.excel_reader import ExcelReader
from src.utils.logger import get_logger
from src.utils.llm.client import UnifiedLLMClient
from src.utils.llm.exceptions import ProviderError

logger = get_logger(__name__)


class RecommendationWriter:
    """推荐导语生成器，负责根据文章分析报告和书籍列表生成推荐导语"""
    
    def __init__(self, llm_client: UnifiedLLMClient, config: Dict):
        """
        初始化推荐导语生成器
        
        Args:
            llm_client: 统一LLM客户端实例
            config: 推荐导语生成配置字典
        """
        self.llm_client = llm_client
        self.config = config
        self.excel_reader = ExcelReader()
        
        logger.info("推荐导语生成器初始化完成")
    
    def generate_recommendation(self, article_report_path: str, excel_path: str) -> str:
        """
        生成推荐导语
        
        Args:
            article_report_path: 文章分析报告MD文件路径
            excel_path: 书籍元数据Excel文件路径
            
        Returns:
            生成的推荐导语MD文件路径
            
        Raises:
            FileNotFoundError: 输入文件不存在
            ValueError: 没有通过筛选的书籍
            LLMCallError: LLM调用失败
        """
        logger.info(f"开始生成推荐导语，文章报告: {article_report_path}, Excel文件: {excel_path}")
        
        try:
            # 加载文章分析报告
            article_report = self._load_article_report(article_report_path)
            
            # 加载并过滤书籍数据
            books_data = self._load_selected_books(excel_path)
            
            # 构建用户提示词
            user_prompt = self._build_user_prompt(article_report, books_data)
            
            # 调用LLM生成推荐导语
            logger.info("开始调用LLM生成推荐导语")
            recommendation_content = self.llm_client.call("recommendation_writer", user_prompt)
            
            # 保存推荐导语
            output_path = self._save_recommendation(recommendation_content, excel_path)
            
            logger.info(f"推荐导语生成完成: {output_path}")
            
            return output_path
            
        except ProviderError as e:
            logger.error(f"LLM调用失败: {e}")
            raise
        except Exception as e:
            logger.error(f"生成推荐导语时发生错误: {e}")
            raise
    
    def _load_article_report(self, file_path: str) -> str:
        """
        加载文章分析报告
        
        Args:
            file_path: 文章分析报告文件路径
            
        Returns:
            文章分析报告内容
            
        Raises:
            FileNotFoundError: 文件不存在
            UnicodeDecodeError: 文件编码错误
        """
        logger.info(f"加载文章分析报告: {file_path}")
        
        # 验证文件存在性
        report_file = Path(file_path)
        if not report_file.exists():
            raise FileNotFoundError(f"文章分析报告文件不存在: {file_path}")
        
        try:
            # 读取文件内容
            with open(report_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                raise ValueError("文章分析报告文件为空")
            
            logger.info(f"成功加载文章分析报告，长度: {len(content)} 字符")
            
            return content
            
        except UnicodeDecodeError as e:
            logger.error(f"文件编码错误: {e}")
            raise
        except Exception as e:
            logger.error(f"读取文章分析报告时发生错误: {e}")
            raise
    
    def _load_selected_books(self, excel_path: str) -> List[Dict]:
        """
        加载通过主题筛选的书籍数据
        
        Args:
            excel_path: Excel文件路径
            
        Returns:
            通过筛选的书籍数据列表
            
        Raises:
            FileNotFoundError: Excel文件不存在
            ValueError: 没有通过筛选的书籍
        """
        logger.info(f"加载并过滤书籍数据: {excel_path}")
        
        try:
            # 加载所有书籍数据
            all_books = self.excel_reader.load_books_data(excel_path)
            
            # 过滤通过筛选的书籍
            selected_books = self.excel_reader.filter_selected_books(all_books)
            
            if not selected_books:
                raise ValueError("没有通过主题筛选的书籍")
            
            logger.info(f"成功加载{len(selected_books)}本通过筛选的书籍")
            
            return selected_books
            
        except Exception as e:
            logger.error(f"加载书籍数据时发生错误: {e}")
            raise
    
    def _build_user_prompt(self, article_report: str, books_data: List[Dict]) -> str:
        """
        构建用户提示词
        
        Args:
            article_report: 文章分析报告内容
            books_data: 书籍数据列表
            
        Returns:
            格式化的用户提示词
        """
        logger.info("构建用户提示词")
        
        # 构建书籍信息文本
        books_text = ""
        for i, book in enumerate(books_data, 1):
            books_text += f"\n书籍 {i}:\n"
            books_text += f"书目条码id: {book.get('书目条码', '')}\n"
            books_text += f"书名: {book.get('豆瓣书名', '')}\n"
            books_text += f"副标题: {book.get('豆瓣副标题', '')}\n"
            books_text += f"作者: {book.get('豆瓣作者', '')}\n"
            books_text += f"丛书: {book.get('豆瓣丛书', '')}\n"
            books_text += f"内容简介: {book.get('豆瓣内容简介', '')}\n"
            books_text += f"作者简介: {book.get('豆瓣作者简介', '')}\n"
            books_text += f"目录: {book.get('豆瓣目录', '')}\n"
            books_text += f"初评理由: {book.get('初评理由', '')}\n"
            books_text += "---\n"
        
        # 构建完整提示词
        user_prompt = f"""
# 文章主题分析报告

{article_report}

# 待选书目列表

{books_text}

请根据以上信息，生成一份专业的推荐导语。
"""
        
        logger.info(f"用户提示词构建完成，长度: {len(user_prompt)} 字符")
        
        return user_prompt
    
    def _save_recommendation(self, content: str, excel_path: str) -> str:
        """
        保存推荐导语到Excel同路径
        
        Args:
            content: 推荐导语内容
            excel_path: Excel文件路径
            
        Returns:
            保存的MD文件路径
        """
        logger.info("保存推荐导语")
        
        # 生成输出文件路径
        excel_file = Path(excel_path)
        stem = excel_file.stem
        
        # 添加时间戳
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 构建输出文件名
        output_filename = f"{stem}_推荐导语_{timestamp}.md"
        output_path = excel_file.parent / output_filename
        
        try:
            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"推荐导语已保存: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"保存推荐导语时发生错误: {e}")
            raise