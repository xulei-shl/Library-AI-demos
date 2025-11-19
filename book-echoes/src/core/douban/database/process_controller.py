#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
流程控制器

协调数据库功能与现有流程：
1. 初始化数据库连接
2. 执行完整流程：ISBN获取+豆瓣爬取+数据库保存
3. 处理查重逻辑
4. 协调Excel更新

作者：豆瓣评分模块开发组
版本：2.0
创建时间：2025-11-05
"""

import os
import logging
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .database_manager import DatabaseManager
from .data_checker import DataChecker
from .excel_updater import ExcelUpdater

logger = logging.getLogger(__name__)


class DoubanRatingProcessController:
    """豆瓣评分流程控制器"""

    def __init__(self, excel_path: str, enable_db: bool = True, db_config: Dict = None):
        """
        初始化流程控制器

        Args:
            excel_path: Excel文件路径
            enable_db: 是否启用数据库功能
            db_config: 数据库配置字典
                {
                    'db_path': '数据库文件路径',
                    'refresh_strategy': {
                        'enabled': True,
                        'stale_days': 30,
                        'force_update': False,
                        'update_mode': 'merge'
                    },
                    'write_strategy': {
                        'batch_size': 100,
                        'use_transaction': True,
                        'create_backup': True
                    }
                }
        """
        self.excel_path = excel_path
        self.db_enabled = enable_db
        self.db_config = db_config or {}

        # 初始化组件
        self.db_manager = None
        self.data_checker = None
        self.excel_updater = None

        # 统计数据
        self.stats = {
            'total_records': 0,
            'existing_valid_count': 0,
            'existing_stale_count': 0,
            'new_count': 0,
            'processed_count': 0,
            'successful_count': 0,
            'failed_count': 0
        }

        # 初始化数据库组件
        if self.db_enabled:
            self._init_database_components()

        logger.info(f"流程控制器初始化完成: db_enabled={self.db_enabled}")

    def _init_database_components(self):
        """初始化数据库组件"""
        try:
            # 获取数据库配置
            db_path = self.db_config.get('db_path', 'books_history.db')
            refresh_config = self.db_config.get('refresh_strategy', {})
            write_config = self.db_config.get('write_strategy', {})

            # 确保数据库目录存在
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

            # 初始化数据库管理器
            self.db_manager = DatabaseManager(db_path)
            self.db_manager.init_database()

            # 初始化查重处理器
            self.data_checker = DataChecker(self.db_manager, refresh_config)

            # 初始化Excel更新器
            self.excel_updater = ExcelUpdater(self.excel_path)

            logger.info("数据库组件初始化成功")

        except Exception as e:
            logger.error(f"初始化数据库组件失败: {e}")
            raise

    async def run_full_process(self) -> Tuple[str, Dict]:
        """
        执行完整流程：ISBN获取+豆瓣爬取+数据库保存

        Returns:
            Tuple[str, Dict]: (输出文件路径, 统计信息)
        """
        logger.info("开始执行完整流程")

        try:
            # 1. 加载Excel数据
            excel_data = self._load_excel_data()
            self.stats['total_records'] = len(excel_data)

            # 2. 查重分类
            if self.db_enabled:
                categories = self.data_checker.check_and_categorize_books(excel_data)

                # 更新统计
                self.stats['existing_valid_count'] = len(categories['existing_valid'])
                self.stats['existing_stale_count'] = len(categories['existing_stale'])
                self.stats['new_count'] = len(categories['new'])

                logger.info(
                    f"查重完成: "
                    f"有效={self.stats['existing_valid_count']}, "
                    f"过期={self.stats['existing_stale_count']}, "
                    f"新数据={self.stats['new_count']}"
                )
            else:
                # 不使用数据库，所有数据都是新的
                categories = {
                    'existing_valid': [],
                    'existing_stale': [],
                    'new': excel_data
                }
                self.stats['new_count'] = len(excel_data)

            # 3. 处理数据
            processed_data = await self._process_categories(categories)

            # 4. 更新Excel
            await self._update_excel(processed_data)

            # 5. 保存到数据库
            if self.db_enabled:
                await self._save_to_database(processed_data)

            # 6. 生成最终统计
            final_stats = self._generate_final_stats()

            # 7. 保存Excel文件
            output_file = self.excel_updater.save()

            logger.info(f"完整流程执行完成: {output_file}")

            return output_file, final_stats

        except Exception as e:
            logger.error(f"完整流程执行失败: {e}")
            raise

    def _load_excel_data(self) -> List[Dict]:
        """加载Excel数据"""
        try:
            df = pd.read_excel(self.excel_path)

            # 转换为字典列表
            excel_data = df.to_dict('records')

            logger.info(f"成功加载Excel数据: {len(excel_data)} 条记录")

            return excel_data

        except Exception as e:
            logger.error(f"加载Excel数据失败: {e}")
            raise

    async def _process_categories(self, categories: Dict) -> List[Dict]:
        """
        处理不同类别的数据

        Args:
            categories: 查重分类结果

        Returns:
            List[Dict]: 处理后的数据列表
        """
        all_processed_data = []

        # 1. 处理已有有效数据（从数据库获取，不爬取）
        if categories['existing_valid']:
            logger.info(f"处理已有有效数据: {len(categories['existing_valid'])} 条")
            valid_data = self._process_existing_valid_data(categories['existing_valid'])
            all_processed_data.extend(valid_data)

        # 2. 处理过期数据和新数据（完整流程）
        stale_and_new = categories['existing_stale'] + categories['new']
        if stale_and_new:
            logger.info(f"处理过期/新数据: {len(stale_and_new)} 条")
            processed_data = await self._process_stale_and_new_books(stale_and_new)
            all_processed_data.extend(processed_data)

        return all_processed_data

    def _process_existing_valid_data(self, valid_data: List[Dict]) -> List[Dict]:
        """
        处理已有有效数据（从数据库获取，不爬取）

        Args:
            valid_data: 有效的数据库数据列表

        Returns:
            List[Dict]: 处理后的数据
        """
        logger.info(f"从数据库加载已有有效数据: {len(valid_data)} 条")

        processed = []
        for item in valid_data:
            # 这些数据已经有完整的豆瓣信息，直接使用
            book_data = item['data']

            # 标记数据来源
            book_data['_data_source'] = 'database_valid'
            book_data['_needs_crawl'] = False

            processed.append(book_data)

        self.stats['successful_count'] += len(processed)

        return processed

    async def _process_stale_and_new_books(self, books: List[Dict]) -> List[Dict]:
        """
        处理过期数据和新数据（完整爬取流程）

        Args:
            books: 过期/新数据列表

        Returns:
            List[Dict]: 处理后的数据
        """
        logger.info(f"开始处理需要爬取的数据: {len(books)} 条")

        processed = []

        # 这里需要调用ISBN异步处理器和豆瓣爬虫
        # 由于这个控制器是协调层，实际的爬取逻辑在isbn_async_processor中处理

        # 暂时标记所有数据为需要爬取
        for book_data in books:
            # 标记数据来源
            book_data['_data_source'] = 'crawler_required'
            book_data['_needs_crawl'] = True

            processed.append(book_data)

        return processed

    async def _update_excel(self, processed_data: List[Dict]):
        """
        更新Excel文件

        Args:
            processed_data: 处理后的数据列表
        """
        try:
            logger.info(f"开始更新Excel: {len(processed_data)} 条数据")

            # 加载Excel文件
            self.excel_updater.load()

            # 分类更新
            database_valid = [d for d in processed_data if d.get('_data_source') == 'database_valid']
            crawler_required = [d for d in processed_data if d.get('_data_source') == 'crawler_required']

            # 更新已有有效数据（从数据库获取）
            if database_valid:
                self.excel_updater.update_from_database(database_valid)
                logger.info(f"从数据库更新了 {len(database_valid)} 条记录")

            # 更新需要爬取的数据（保持原有逻辑，isbn_async_processor会处理）
            if crawler_required:
                logger.info(f"标记了 {len(crawler_required)} 条记录需要爬取")

        except Exception as e:
            logger.error(f"更新Excel失败: {e}")
            raise

    async def _save_to_database(self, processed_data: List[Dict]):
        """
        保存数据到数据库

        Args:
            processed_data: 处理后的数据列表
        """
        try:
            if not self.db_manager:
                logger.warning("数据库管理器未初始化，跳过保存")
                return

            logger.info(f"开始保存数据到数据库: {len(processed_data)} 条")

            # 准备三类数据
            books_data = []
            borrow_records_list = []
            statistics_list = []

            for item in processed_data:
                # 提取books表数据
                book_data = self._extract_book_data(item)
                if book_data:
                    books_data.append(book_data)

                # 提取borrow_records数据（如果存在）
                borrow_record = self._extract_borrow_record(item)
                if borrow_record:
                    borrow_records_list.append(borrow_record)

                # 提取borrow_statistics数据（如果存在）
                statistics = self._extract_borrow_statistics(item)
                if statistics:
                    statistics_list.append(statistics)

            # 批量保存
            if books_data or borrow_records_list or statistics_list:
                batch_size = self.db_config.get('write_strategy', {}).get('batch_size', 100)
                self.db_manager.batch_save_data(books_data, borrow_records_list, statistics_list, batch_size)

                logger.info("数据保存到数据库成功")

        except Exception as e:
            logger.error(f"保存到数据库失败: {e}")
            raise

    def _extract_book_data(self, item: Dict) -> Dict:
        """
        提取books表数据

        Args:
            item: 原始数据项

        Returns:
            Dict: books表数据
        """
        try:
            book_data = {
                'barcode': item.get('barcode') or item.get('书目条码'),
                'call_no': item.get('call_no') or item.get('索书号'),
                'book_title': item.get('book_title') or item.get('书名'),
                'additional_info': item.get('additional_info') or item.get('附加信息'),
                'isbn': item.get('isbn') or item.get('ISBN号'),
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # 添加豆瓣字段（如果存在）
            for db_field, excel_column in {
                'douban_url': '豆瓣链接',
                'douban_rating': '豆瓣评分',
                'douban_title': '豆瓣书名',
                'douban_subtitle': '豆瓣副标题',
                'douban_original_title': '豆瓣原作名',
                'douban_author': '豆瓣作者',
                'douban_translator': '豆瓣译者',
                'douban_publisher': '豆瓣出版社',
                'douban_producer': '豆瓣出品方',
                'douban_series': '豆瓣丛书',
                'douban_series_link': '豆瓣丛书链接',
                'douban_price': '豆瓣定价',
                'douban_isbn': '豆瓣ISBN',
                'douban_pages': '豆瓣页数',
                'douban_binding': '豆瓣装帧',
                'douban_pub_year': '豆瓣出版年',
                'douban_rating_count': '豆瓣评价人数',
                'douban_summary': '豆瓣内容简介',
                'douban_author_intro': '豆瓣作者简介',
                'douban_catalog': '豆瓣目录',
                'douban_cover_image': '豆瓣封面图片链接'
            }.items():
                if excel_column in item:
                    book_data[db_field] = item[excel_column]

            return book_data

        except Exception as e:
            logger.error(f"提取books数据失败: {e}")
            return {}

    def _extract_borrow_record(self, item: Dict) -> Optional[Dict]:
        """
        提取borrow_records表数据

        Args:
            item: 原始数据项

        Returns:
            Optional[Dict]: borrow_records表数据
        """
        # 借阅记录需要从Excel的借阅相关列提取
        # 这里根据实际的Excel结构来实现

        return None

    def _extract_borrow_statistics(self, item: Dict) -> Optional[Dict]:
        """
        提取borrow_statistics表数据

        Args:
            item: 原始数据项

        Returns:
            Optional[Dict]: borrow_statistics表数据
        """
        # 统计数据需要从Excel的统计相关列提取
        # 这里根据实际的Excel结构来实现

        return None

    def _generate_final_stats(self) -> Dict:
        """
        生成最终统计信息

        Returns:
            Dict: 统计信息
        """
        # 获取数据库统计
        db_stats = {}
        if self.db_manager:
            db_stats = self.db_manager.get_database_stats()

        # 合并统计信息
        final_stats = {
            **self.stats,
            'database': db_stats,
            'excel_file': self.excel_path
        }

        return final_stats

    def get_database_stats(self) -> Dict:
        """
        获取数据库统计信息

        Returns:
            Dict: 数据库统计信息
        """
        if not self.db_manager:
            return {}

        return self.db_manager.get_database_stats()

    def close(self):
        """关闭资源"""
        if self.db_manager:
            self.db_manager.close()

        if self.excel_updater:
            self.excel_updater.close()

        logger.info("流程控制器资源已关闭")
