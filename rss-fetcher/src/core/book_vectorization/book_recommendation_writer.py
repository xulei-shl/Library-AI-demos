#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
单本书籍推荐语生成器，负责为通过人工评选的书籍生成推荐语

该模块实现了单本书籍推荐语的生成功能，根据书籍的元数据信息
使用大语言模型生成专业的推荐语，并将结果写回Excel文件。
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List

from src.utils.logger import get_logger
from src.utils.llm.client import UnifiedLLMClient
from src.utils.llm.exceptions import ProviderError

logger = get_logger(__name__)


class BookRecommendationWriter:
    """单本书籍推荐语生成器"""

    def __init__(self, llm_client: UnifiedLLMClient, config: Dict = None):
        """
        初始化推荐语生成器

        Args:
            llm_client: 统一LLM客户端实例
            config: 配置字典（可选）
        """
        self.llm_client = llm_client
        self.config = config or {}

        logger.info("单本书籍推荐语生成器初始化完成")

    def generate_recommendations_for_books(self, excel_path: str) -> str:
        """
        为Excel中通过人工评选的书籍批量生成推荐语

        Args:
            excel_path: Excel文件路径

        Returns:
            更新后的Excel文件路径

        Raises:
            FileNotFoundError: Excel文件不存在
            ValueError: 没有需要生成推荐语的书籍
            ProviderError: LLM调用失败
        """
        logger.info(f"开始为书籍生成推荐语，Excel文件: {excel_path}")

        try:
            # 读取Excel文件
            excel_file = Path(excel_path)
            if not excel_file.exists():
                raise FileNotFoundError(f"Excel文件不存在: {excel_path}")

            df = pd.read_excel(excel_path)
            logger.info(f"成功加载Excel文件，共{len(df)}行数据")

            # 检测使用哪种筛选方式
            selected_books = self._get_selected_books(df)

            if not selected_books:
                raise ValueError("没有找到需要生成推荐语的书籍（人工评选为'通过'或初评结果为TRUE的书籍）")

            logger.info(f"找到{len(selected_books)}本需要生成推荐语的书籍")

            # 批量生成推荐语
            results = self._batch_generate_recommendations(selected_books)

            # 更新Excel文件
            output_path = self._update_excel_with_recommendations(excel_path, df, results)

            logger.info(f"推荐语生成完成，更新后的Excel文件: {output_path}")

            return output_path

        except ProviderError as e:
            logger.error(f"LLM调用失败: {e}")
            raise
        except Exception as e:
            logger.error(f"生成推荐语时发生错误: {e}")
            raise

    def _get_selected_books(self, df: pd.DataFrame) -> List[Dict]:
        """
        获取需要生成推荐语的书籍

        优先使用"人工评选"列筛选值为"通过"的书籍，如果该列不存在或所有值都为空，
        则回退使用"初评结果"列筛选值为TRUE的书籍。

        Args:
            df: Excel数据框

        Returns:
            需要生成推荐语的书籍列表，每本书包含索引和书籍信息
        """
        logger.info("开始筛选需要生成推荐语的书籍")

        # 检测使用哪种筛选方式
        use_manual_review = False
        use_initial_review = False

        # 检查"人工评选"列是否存在且有非空值
        if "人工评选" in df.columns:
            manual_review_values = df["人工评选"].dropna()
            if not manual_review_values.empty:
                use_manual_review = True
                logger.info(f"检测到'人工评选'列且包含{len(manual_review_values)}个非空值，使用该列进行筛选")

        if not use_manual_review and "初评结果" in df.columns:
            use_initial_review = True
            logger.info("'人工评选'列不存在或全部为空，回退使用'初评结果'列进行筛选")

        selected_books = []

        for idx, row in df.iterrows():
            is_selected = False

            if use_manual_review:
                # 使用"人工评选"列，筛选值为"通过"的书籍
                value = row.get("人工评选")
                if pd.notna(value) and isinstance(value, str) and value.strip() == "通过":
                    is_selected = True

            elif use_initial_review:
                # 回退使用"初评结果"列，筛选值为TRUE的书籍
                value = row.get("初评结果")
                if value is True or (isinstance(value, str) and value.upper() == "TRUE"):
                    is_selected = True

            if is_selected:
                # 检查是否已有推荐语
                existing_recommendation = row.get("人工推荐语", "")
                if pd.notna(existing_recommendation) and str(existing_recommendation).strip():
                    logger.info(f"书籍'{row.get('豆瓣书名', '')}'已有推荐语，跳过")
                    continue

                selected_books.append({
                    "index": idx,
                    "book_id": row.get("书目条码", ""),
                    "title": row.get("豆瓣书名", ""),
                    "subtitle": row.get("豆瓣副标题", ""),
                    "author": row.get("豆瓣作者", ""),
                    "summary": row.get("豆瓣内容简介", ""),
                    "author_intro": row.get("豆瓣作者简介", ""),
                    "catalog": row.get("豆瓣目录", "")
                })

        logger.info(f"筛选完成，需要生成推荐语的书籍数: {len(selected_books)}")

        return selected_books

    def _batch_generate_recommendations(self, books: List[Dict]) -> List[Dict]:
        """
        批量生成推荐语

        Args:
            books: 书籍列表

        Returns:
            生成结果列表，每项包含书籍索引和推荐语
        """
        logger.info(f"开始批量生成推荐语，共{len(books)}本书")

        results = []

        for i, book in enumerate(books, 1):
            logger.info(f"正在处理第{i}/{len(books)}本书: {book['title']}")

            try:
                # 构建用户提示词
                user_prompt = self._build_book_prompt(book)

                # 调用LLM生成推荐语
                logger.info(f"调用LLM为书籍'{book['title']}'生成推荐语")
                recommendation = self.llm_client.call("book_recommendation_writer", user_prompt)

                # 清理推荐语（移除可能的markdown代码块标记）
                recommendation = self._clean_recommendation(recommendation)

                logger.info(f"成功为书籍'{book['title']}'生成推荐语")

                results.append({
                    "index": book["index"],
                    "book_id": book["book_id"],
                    "title": book["title"],
                    "recommendation": recommendation,
                    "status": "success"
                })

            except Exception as e:
                logger.error(f"为书籍'{book['title']}'生成推荐语失败: {e}")
                results.append({
                    "index": book["index"],
                    "book_id": book["book_id"],
                    "title": book["title"],
                    "recommendation": "",
                    "status": f"failed: {str(e)}"
                })

        # 统计结果
        success_count = sum(1 for r in results if r["status"] == "success")
        logger.info(f"批量生成完成，成功{success_count}/{len(books)}本")

        return results

    def _build_book_prompt(self, book: Dict) -> str:
        """
        构建单本书籍的用户提示词

        Args:
            book: 书籍信息字典

        Returns:
            格式化的用户提示词
        """
        prompt = f"""# 书籍信息

书名: {book['title']}
副标题: {book['subtitle']}
作者: {book['author']}
内容简介: {book['summary']}
作者简介: {book['author_intro']}
目录: {book['catalog']}

请根据以上信息，为这本书撰写一段100-200字的推荐语。
"""
        return prompt

    def _clean_recommendation(self, recommendation: str) -> str:
        """
        清理推荐语文本，移除可能的markdown代码块标记

        Args:
            recommendation: 原始推荐语

        Returns:
            清理后的推荐语
        """
        # 移除可能的markdown代码块标记
        recommendation = recommendation.strip()
        if recommendation.startswith("```"):
            # 找到第一个换行符
            first_newline = recommendation.find("\n")
            if first_newline != -1:
                recommendation = recommendation[first_newline + 1:]
        if recommendation.endswith("```"):
            recommendation = recommendation[:-3]

        # 移除可能的"推荐语:"等前缀
        prefixes_to_remove = ["推荐语:", "推荐语：", "推荐:", "推荐："]
        for prefix in prefixes_to_remove:
            if recommendation.startswith(prefix):
                recommendation = recommendation[len(prefix):].strip()

        return recommendation.strip()

    def _update_excel_with_recommendations(
        self,
        excel_path: str,
        df: pd.DataFrame,
        results: List[Dict]
    ) -> str:
        """
        将推荐语更新到Excel文件

        Args:
            excel_path: 原Excel文件路径
            df: 原始数据框
            results: 生成结果列表

        Returns:
            更新后的Excel文件路径
        """
        logger.info("正在将推荐语更新到Excel文件")

        # 确保"人工推荐语"列存在
        if "人工推荐语" not in df.columns:
            df["人工推荐语"] = ""
            logger.info("添加'人工推荐语'列")

        # 更新推荐语
        for result in results:
            if result["status"] == "success":
                df.at[result["index"], "人工推荐语"] = result["recommendation"]

        try:
            # 直接写回原Excel文件
            df.to_excel(excel_path, index=False)

            logger.info(f"Excel文件已更新: {excel_path}")

            return str(excel_path)

        except Exception as e:
            logger.error(f"保存Excel文件时发生错误: {e}")
            raise
