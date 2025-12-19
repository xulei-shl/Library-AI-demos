#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查重处理器

封装查重逻辑，与异步处理器协作：
1. 调用DatabaseManager进行批量查重
2. 根据刷新策略分类数据
3. 返回分类结果供上层使用

作者：豆瓣评分模块开发组
版本：2.0
创建时间：2025-11-05
"""

import logging
import math
from typing import Dict, List, Any
from .database_manager import DatabaseManager
from .value_normalizers import normalize_call_no, normalize_barcode

logger = logging.getLogger(__name__)


class DataChecker:
    """查重处理器"""

    def __init__(self, db_manager: DatabaseManager, refresh_config: Dict):
        """
        初始化查重处理器

        Args:
            db_manager: 数据库管理器实例
            refresh_config: 刷新策略配置
                {
                    'enabled': True,
                    'stale_days': 30,
                    'force_update': False,
                    'update_mode': 'merge'
                }
        """
        self.db_manager = db_manager
        self.refresh_config = refresh_config or {}
        self.enabled = self.refresh_config.get('enabled', True)
        self.stale_days = self.refresh_config.get('stale_days', 30)
        self.force_update = self.refresh_config.get('force_update', False)
        self.crawl_empty_url = self.refresh_config.get('crawl_empty_url', True)
        self.required_fields = [
            field.strip()
            for field in (self.refresh_config.get('required_fields') or [])
            if isinstance(field, str) and field.strip()
        ] or ['douban_title', 'douban_summary', 'douban_cover_image']

        logger.info(f"查重处理器初始化完成: enabled={self.enabled}, stale_days={self.stale_days}, force_update={self.force_update}, crawl_empty_url={self.crawl_empty_url}")

    def check_and_categorize_books(self, excel_data: List[Dict]) -> Dict:
        """
        检查并分类书籍

        Args:
            excel_data: Excel数据列表，每个元素是一个字典

        Returns:
            Dict: 分类结果
            {
                'existing_valid': [book_data1, book_data2, ...],  # 从DB直接获取
                'existing_stale': [book_data3, book_data4, ...],  # 需要重新爬取
                'new': [book_data5, book_data6, ...]              # 需要完整流程
            }

        Note:
            existing_valid: 从数据库中查询并直接返回，无需爬取
            existing_stale: 数据库中存在但已过期，需要重新爬取
            new: 数据库中不存在，需要完整流程（ISBN爬取+豆瓣爬取）
        """
        if not self.enabled:
            logger.info("查重功能已禁用，直接处理所有数据")
            return {
                'existing_valid': [],
                'existing_valid_incomplete': [],
                'existing_stale': [],
                'new': excel_data
            }

        try:
            # 1. 提取所有barcode并进行归一化
            barcodes = []
            for row in excel_data:
                barcode = str(row.get('barcode') or row.get('书目条码', '')).strip()
                if barcode and barcode != 'nan':
                    # 归一化条码（去除.0后缀等）
                    normalized_barcode = normalize_barcode(barcode)
                    if normalized_barcode:
                        barcodes.append(normalized_barcode)

            if not barcodes:
                logger.warning("没有有效的barcode数据")
                return {
                    'existing_valid': [],
                    'existing_valid_incomplete': [],
                    'existing_stale': [],
                    'new': []
                }

            logger.info(f"开始批量查重，共 {len(barcodes)} 个条码")

            # 2. 调用数据库管理器进行批量查重
            duplicate_result = self.db_manager.batch_check_duplicates(
                barcodes, 
                stale_days=self.stale_days,
                crawl_empty_url=self.crawl_empty_url
            )

            # 3. 转换为统一格式
            result = {
                'existing_valid': [],
                'existing_valid_incomplete': [],
                'existing_stale': [],
                'new': []
            }

            # 处理已有有效数据
            for item in duplicate_result['existing_valid']:
                book_data = item['data']
                barcode = item['barcode']

                # 查找对应的Excel行
                excel_row = self._find_excel_row_by_barcode(excel_data, barcode)
                if excel_row:
                    # 合并数据库数据到Excel行
                    merged_data = self._merge_database_data(excel_row, book_data)
                    bucket = 'existing_valid'
                    if not self._has_required_fields(book_data):
                        bucket = 'existing_valid_incomplete'
                        merged_data['_needs_api_patch'] = True
                    result[bucket].append(merged_data)

            # 处理已有过期数据
            for item in duplicate_result['existing_stale']:
                book_data = item['data']
                barcode = item['barcode']

                # 查找对应的Excel行
                excel_row = self._find_excel_row_by_barcode(excel_data, barcode)
                if excel_row:
                    # 合并数据库数据到Excel行（保留部分基础信息）
                    merged_data = self._merge_database_data(excel_row, book_data, merge_mode='partial')
                    result['existing_stale'].append(merged_data)

            # 处理新数据
            for barcode in duplicate_result['new']:
                excel_row = self._find_excel_row_by_barcode(excel_data, barcode)
                if excel_row:
                    result['new'].append(excel_row)

            # 步骤B：索书号补查重（仅对条码未命中的记录）
            result = self._perform_call_no_deduplication(excel_data, result)

            # 4. 如果启用强制更新，将所有已有数据移动到stale类别
            if self.force_update:
                logger.info("强制更新模式：将所有已有数据标记为需要重新爬取")
                result['existing_stale'].extend(result['existing_valid'])
                result['existing_stale'].extend(result['existing_valid_incomplete'])
                result['existing_valid'] = []
                result['existing_valid_incomplete'] = []

            # 5. 记录统计信息
            total_existing = len(duplicate_result['existing_valid']) + len(duplicate_result['existing_stale'])
            logger.info(
                f"查重分类完成: "
                f"已有有效={len(result['existing_valid'])}, "
                f"已有待补API={len(result['existing_valid_incomplete'])}, "
                f"已有过期={len(result['existing_stale'])}, "
                f"全新数据={len(result['new'])}, "
                f"总计={len(excel_data)}"
            )

            return result

        except Exception as e:
            logger.error(f"查重和分类失败: {e}")
            # 降级处理：返回所有数据为新数据
            logger.warning("查重失败，降级到无数据库模式")
            return {
                'existing_valid': [],
                'existing_valid_incomplete': [],
                'existing_stale': [],
                'new': excel_data
            }

    def check_and_categorize_isbn_books(self, excel_data: List[Dict]) -> Dict:
        """
        检查并分类书籍 (专用于ISBN爬取阶段)

        Args:
            excel_data: Excel数据列表，每个元素是一个字典

        Returns:
            Dict: 分类结果
            {
                'existing_valid': [book_data1, book_data2, ...],  # ISBN已存在,从DB直接获取
                'existing_stale': [],  # ISBN查重不使用此分类
                'new': [book_data3, book_data4, ...]  # ISBN不存在,需要爬取
            }

        Note:
            existing_valid: 数据库中isbn字段有值,直接返回,无需爬取
            existing_stale: 空列表(ISBN查重不使用)
            new: 数据库中不存在或isbn字段为空,需要爬取
        """
        if not self.enabled:
            logger.info("查重功能已禁用，直接处理所有数据")
            return {
                'existing_valid': [],
                'existing_valid_incomplete': [],
                'existing_stale': [],
                'new': excel_data
            }

        try:
            # 1. 提取所有barcode并进行归一化
            barcodes = []
            for row in excel_data:
                barcode = str(row.get('barcode') or row.get('书目条码', '')).strip()
                if barcode and barcode != 'nan':
                    # 归一化条码（去除.0后缀等）
                    normalized_barcode = normalize_barcode(barcode)
                    if normalized_barcode:
                        barcodes.append(normalized_barcode)

            if not barcodes:
                logger.warning("没有有效的barcode数据")
                return {
                    'existing_valid': [],
                    'existing_valid_incomplete': [],
                    'existing_stale': [],
                    'new': []
                }

            logger.info(f"开始ISBN批量查重，共 {len(barcodes)} 个条码")

            # 2. 调用数据库管理器进行ISBN批量查重
            duplicate_result = self.db_manager.batch_check_isbn_duplicates(barcodes)

            # 3. 转换为统一格式
            result = {
                'existing_valid': [],
                'existing_valid_incomplete': [],
                'existing_stale': [],  # ISBN查重不使用
                'new': []
            }

            # 处理已有ISBN数据
            for item in duplicate_result['existing_valid']:
                book_data = item['data']
                barcode = item['barcode']

                # 查找对应的Excel行
                excel_row = self._find_excel_row_by_barcode(excel_data, barcode)
                if excel_row:
                    # 合并数据库的ISBN数据到Excel行
                    merged_data = excel_row.copy()
                    merged_data['isbn'] = book_data.get('isbn')
                    merged_data['_data_source'] = 'database_isbn'
                    result['existing_valid'].append(merged_data)

            # 处理需要爬取ISBN的数据
            for barcode in duplicate_result['new']:
                excel_row = self._find_excel_row_by_barcode(excel_data, barcode)
                if excel_row:
                    result['new'].append(excel_row)

            # 4. 记录统计信息
            logger.info(
                f"ISBN查重分类完成: "
                f"已有ISBN={len(result['existing_valid'])}, "
                f"需爬取ISBN={len(result['new'])}, "
                f"总计={len(excel_data)}"
            )

            return result

        except Exception as e:
            logger.error(f"ISBN查重和分类失败: {e}")
            # 降级处理：返回所有数据为新数据
            logger.warning("ISBN查重失败，降级到无数据库模式")
            return {
                'existing_valid': [],
                'existing_valid_incomplete': [],
                'existing_stale': [],
                'new': excel_data
            }

    def _find_excel_row_by_barcode(self, excel_data: List[Dict], barcode: str) -> Dict:
        """
        根据barcode查找对应的Excel行

        Args:
            excel_data: Excel数据列表
            barcode: 条码

        Returns:
            Dict: 对应的Excel行数据，如果未找到返回None
        """
        for row in excel_data:
            row_barcode = str(row.get('barcode') or row.get('书目条码', '')).strip()
            if row_barcode == barcode:
                return row
        return None

    def _has_required_fields(self, db_book: Dict[str, Any]) -> bool:
        """
        检查数据库书目是否具备配置的必备字段
        """
        for field in self.required_fields:
            value = db_book.get(field)
            if value is None:
                return False
            if isinstance(value, str):
                if not value.strip():
                    return False
            elif isinstance(value, float):
                if math.isnan(value):
                    return False
        return True

    def _merge_database_data(self, excel_row: Dict, db_book: Dict, merge_mode: str = 'full') -> Dict:
        """
        将数据库数据合并到Excel行

        Args:
            excel_row: Excel行数据
            db_book: 数据库书籍数据
            merge_mode: 合并模式
                - 'full': 完全合并（覆盖所有字段）
                - 'partial': 部分合并（只保留基础信息，豆瓣信息会被重新爬取）

        Returns:
            Dict: 合并后的数据
        """
        merged = excel_row.copy()

        if merge_mode == 'full':
            # 完全合并模式：将数据库中的所有字段合并到Excel行
            # 包括基础信息和豆瓣信息
            for key, value in db_book.items():
                if value is not None:
                    merged[key] = value

            # 添加标记，标识数据来源
            merged['_data_source'] = 'database'

        elif merge_mode == 'partial':
            # 部分合并模式：只保留基础信息，豆瓣信息将被重新爬取
            # 基础信息（不变）
            basic_fields = [
                'barcode', 'call_no', 'book_title', 'additional_info', 'isbn',
                'data_version', 'created_at', 'updated_at'
            ]

            for field in basic_fields:
                if field in db_book and db_book[field] is not None:
                    merged[field] = db_book[field]

            # 标记为过期数据，需要重新爬取豆瓣信息
            merged['_data_source'] = 'database_stale'
            merged['_needs_update'] = True

        return merged

    def get_refresh_strategy(self) -> Dict:
        """
        获取当前刷新策略

        Returns:
            Dict: 刷新策略配置
        """
        return {
            'enabled': self.enabled,
            'stale_days': self.stale_days,
            'force_update': self.force_update,
            'update_mode': self.refresh_config.get('update_mode', 'merge')
        }

    def update_refresh_strategy(self, **kwargs):
        """
        更新刷新策略

        Args:
            **kwargs: 要更新的配置项
                - stale_days: 过期天数
                - force_update: 强制更新模式
                - update_mode: 更新模式
        """
        for key, value in kwargs.items():
            if key in self.refresh_config:
                self.refresh_config[key] = value
                logger.info(f"更新刷新策略: {key} = {value}")

        # 同步更新实例变量
        if 'stale_days' in kwargs:
            self.stale_days = kwargs['stale_days']
        if 'force_update' in kwargs:
            self.force_update = kwargs['force_update']

        logger.info(f"刷新策略更新完成: {self.refresh_config}")

    def _perform_call_no_deduplication(self, excel_data: List[Dict], result: Dict) -> Dict:
        """
        执行索书号补查重逻辑（步骤B）

        Args:
            excel_data: 原始Excel数据
            result: 条码查重后的分类结果

        Returns:
            Dict: 更新后的分类结果
        """
        if not result['new']:
            logger.debug("没有新数据，跳过索书号补查重")
            return result

        logger.info(f"开始索书号补查重，共 {len(result['new'])} 条待查记录")

        # 构建归一化条码到Excel行的映射，以便后续正确移除
        barcode_to_excel_row = {}
        for row in result['new']:
            # 获取并归一化条码
            raw_barcode = row.get('barcode') or row.get('书目条码', '')
            normalized_barcode = normalize_barcode(raw_barcode)
            if normalized_barcode:
                barcode_to_excel_row[normalized_barcode] = row

        # 构建索书号到归一化条码的映射
        call_no_to_normalized_barcodes = {}
        for row in result['new']:
            # 获取索书号列的值（假设列名为'索书号'或'call_no'）
            call_no = row.get('索书号') or row.get('call_no', '')
            normalized_call_no = normalize_call_no(call_no)

            # 获取并归一化条码
            raw_barcode = row.get('barcode') or row.get('书目条码', '')
            normalized_barcode = normalize_barcode(raw_barcode)

            if normalized_call_no and normalized_barcode:
                if normalized_call_no not in call_no_to_normalized_barcodes:
                    call_no_to_normalized_barcodes[normalized_call_no] = []
                call_no_to_normalized_barcodes[normalized_call_no].append(normalized_barcode)

        if not call_no_to_normalized_barcodes:
            logger.debug("没有有效的索书号，结束补查重")
            return result

        # 批量查询数据库
        call_numbers = list(call_no_to_normalized_barcodes.keys())
        logger.debug(f"查询 {len(call_numbers)} 个不重复的索书号")

        db_books_by_call_no = self.db_manager.batch_get_books_by_call_numbers(call_numbers)

        # 统计信息
        call_no_match_count = 0
        updated_new_count = 0

        # 处理索书号命中的记录
        for normalized_call_no, normalized_barcodes in call_no_to_normalized_barcodes.items():
            if normalized_call_no in db_books_by_call_no:
                call_no_match_count += 1
                book_data = db_books_by_call_no[normalized_call_no]

                # 使用分类逻辑判断是valid还是stale
                category, reason = self.db_manager._categorize_book_record(
                    book_data, self.stale_days, self.crawl_empty_url
                )

                logger.debug(f"索书号 {normalized_call_no} 匹配: 分类={category}, 原因={reason}")

                # 处理所有使用该索书号的Excel行
                for normalized_barcode in normalized_barcodes:
                    if normalized_barcode in barcode_to_excel_row:
                        excel_row = barcode_to_excel_row[normalized_barcode]

                        # 从result['new']中移除
                        result['new'] = [r for r in result['new'] if r != excel_row]
                        updated_new_count += 1

                        # 合并数据库数据
                        merge_mode = 'full' if category == 'existing_valid' else 'partial'
                        merged_data = self._merge_database_data(excel_row, book_data, merge_mode)

                        # 重要：保留Excel的原始条码，因为这是通过索书号匹配的
                        original_barcode = excel_row.get('barcode') or excel_row.get('书目条码', '')
                        if original_barcode:
                            merged_data['barcode'] = original_barcode

                        # 标记数据来源
                        merged_data['_data_source'] = 'database_call_no'
                        merged_data['_match_source'] = 'call_no'
                        merged_data['_match_reason'] = reason
                        merged_data['_original_db_barcode'] = book_data.get('barcode')  # 记录原始数据库条码

                        # 检查必填字段
                        if category == 'existing_valid' and not self._has_required_fields(book_data):
                            category = 'existing_valid_incomplete'
                            merged_data['_needs_api_patch'] = True

                        result[category].append(merged_data)

        logger.info(
            f"索书号补查重完成: "
            f"匹配 {call_no_match_count} 个索书号, "
            f"从 new 中移除 {updated_new_count} 条记录, "
            f"剩余 {len(result['new'])} 条新数据"
        )

        return result
