#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图书过滤器

根据配置规则过滤符合条件的书籍（必填字段 + 评分阈值 + I开头索书号正则过滤）
"""

import re
from typing import Dict, List
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BookFilter:
    """图书过滤器"""
    
    def __init__(self, filter_config: Dict, db_reader=None):
        """
        初始化过滤器
        
        Args:
            filter_config: 过滤配置字典
            db_reader: 数据库读取器实例（用于标记过滤状态）
        """
        self.config = filter_config
        self.db_reader = db_reader
    
    def apply(self, books: List[Dict]) -> List[Dict]:
        """
        应用过滤规则

        Args:
            books: 待过滤的书籍列表

        Returns:
            符合条件的书籍列表
        """
        filtered = []
        filtered_count = 0

        for book in books:
            # 检查必填字段
            if not self._check_required_fields(book):
                self._mark_filtered(book, "缺少必填字段")
                filtered_count += 1
                continue

            # 检查评分阈值（如果启用）
            if self.config.get('enable_rating_filter', True) and not self._check_rating_threshold(book):
                self._mark_filtered(book, "评分未达标")
                filtered_count += 1
                continue

            # 检查I开头索书号正则过滤（如果启用）
            if self.config.get('enable_i_call_no_filter', False) and not self._check_i_call_no_pattern(book):
                self._mark_filtered(book, "I开头索书号不匹配允许的正则模式")
                filtered_count += 1
                continue

            filtered.append(book)

        logger.info(f"过滤完成: 总数={len(books)}, 符合条件={len(filtered)}, 过滤={filtered_count}")

        return filtered
    
    def _check_required_fields(self, book: Dict) -> bool:
        """
        检查必填字段
        
        Args:
            book: 书籍信息字典
            
        Returns:
            是否通过检查
        """
        for field in self.config['required_fields']:
            value = book.get(field)
            if not value or (isinstance(value, str) and value.strip() == ''):
                logger.debug(f"书籍 {book.get('id')} 缺少字段: {field}")
                return False
        return True
    
    def _check_rating_threshold(self, book: Dict) -> bool:
        """
        检查评分阈值
        
        Args:
            book: 书籍信息字典
            
        Returns:
            是否通过检查
        """
        rating = book.get('douban_rating')
        if rating is None:
            logger.debug(f"书籍 {book.get('id')} 缺少评分")
            return False
        
        # 获取索书号首字母
        call_no = book.get('call_no', '')
        prefix = call_no[0].upper() if call_no else ''
        
        # 获取对应阈值
        threshold = self.config['rating_thresholds'].get(
            prefix,
            self.config['rating_thresholds']['default']
        )
        
        passed = float(rating) >= threshold
        
        if not passed:
            logger.debug(f"书籍 {book.get('id')} 评分未达标: {rating} < {threshold}")
        
        return passed

    def _check_i_call_no_pattern(self, book: Dict) -> bool:
        """
        检查I开头索书号是否匹配允许的正则模式

        Args:
            book: 书籍信息字典

        Returns:
            是否通过检查
        """
        call_no = book.get('call_no', '')

        # 只处理I开头的索书号
        if not call_no or not call_no.upper().startswith('I'):
            return True

        # 获取配置的正则模式列表
        patterns = self.config.get('i_call_no_patterns', [])

        # 逐一匹配正则表达式
        for pattern in patterns:
            if re.match(pattern, call_no, re.IGNORECASE):
                logger.debug(f"书籍 {book.get('id')} I开头索书号匹配模式: {pattern}")
                return True

        logger.debug(f"书籍 {book.get('id')} I开头索书号不匹配任何允许的模式: {call_no}")
        return False

    def _mark_filtered(self, book: Dict, reason: str):
        """
        标记为已过滤
        
        Args:
            book: 书籍信息字典
            reason: 过滤原因
        """
        # 如果有数据库读取器，更新状态
        if self.db_reader:
            try:
                self.db_reader.update_embedding_status(
                    book_id=book['id'],
                    status='filtered_out',
                    error=reason
                )
            except Exception as e:
                logger.error(f"标记过滤状态失败: book_id={book.get('id')}, error={str(e)}")
