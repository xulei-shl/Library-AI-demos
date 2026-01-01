#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库管理器

封装所有数据库操作，包括：
1. 初始化数据库（创建表、索引）
2. 批量查重（根据barcode列表+刷新策略）
3. 批量写入三类数据
4. 查询完整的书籍信息

作者：豆瓣评分模块开发组
版本：2.0
创建时间：2025-11-05
"""

import sqlite3
import os
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: str = "books_history.db"):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.conn = None
        self._ensure_db_directory()

    def _ensure_db_directory(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"创建数据库目录: {db_dir}")

    def init_database(self, db_path: str = None):
        """
        初始化数据库（创建表、索引）

        Args:
            db_path: 数据库文件路径（可选）

        Returns:
            bool: 初始化是否成功
        """
        if db_path:
            self.db_path = db_path
            self._ensure_db_directory()

        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束

            # 创建所有表
            self._create_tables()

            # 创建所有索引
            self._create_indexes()

            self.conn.commit()
            logger.info(f"数据库初始化成功: {self.db_path}")
            return True

        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            if self.conn:
                self.conn.rollback()
            raise

    def _create_tables(self):
        """创建所有表"""
        # books表（书籍基础信息和豆瓣信息）
        self._create_books_table()

        # borrow_records表（借阅记录）
        self._create_borrow_records_table()

        # borrow_statistics表（统计信息）
        self._create_borrow_statistics_table()

    def _create_books_table(self):
        """创建books表"""
        sql = """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE NOT NULL,

            -- ============ 书籍基础信息（不变）===========
            call_no TEXT NOT NULL,
            book_title TEXT NOT NULL,
            additional_info TEXT,
            isbn TEXT,

            -- ============ 豆瓣信息（1对1，不变）===========
            douban_url TEXT,
            douban_rating REAL,
            douban_title TEXT,
            douban_subtitle TEXT,
            douban_original_title TEXT,
            douban_author TEXT,
            douban_translator TEXT,
            douban_publisher TEXT,
            douban_producer TEXT,
            douban_series TEXT,
            douban_series_link TEXT,
            douban_price TEXT,
            douban_isbn TEXT,
            douban_pages INTEGER,
            douban_binding TEXT,
            douban_pub_year INTEGER,
            douban_rating_count INTEGER,
            douban_summary TEXT,
            douban_author_intro TEXT,
            douban_catalog TEXT,
            douban_cover_image TEXT,

            -- ============ 元数据 ============
            data_version TEXT DEFAULT '1.0',
            created_at TEXT NOT NULL,
            updated_at TEXT
        );
        """
        self.conn.execute(sql)
        logger.debug("books表创建成功")

    def _create_borrow_records_table(self):
        """创建borrow_records表"""
        sql = """
        CREATE TABLE IF NOT EXISTS borrow_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL,

            -- ============ 借阅记录信息 ============
            reader_card_no TEXT NOT NULL,
            submit_time TEXT,
            return_time TEXT,
            storage_time TEXT,

            -- ============ 元数据 ============
            created_at TEXT NOT NULL,

            FOREIGN KEY (barcode) REFERENCES books(barcode) ON DELETE CASCADE
        );
        """
        self.conn.execute(sql)
        logger.debug("borrow_records表创建成功")

    def _create_borrow_statistics_table(self):
        """创建borrow_statistics表"""
        sql = """
        CREATE TABLE IF NOT EXISTS borrow_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL,

            -- ============ 统计周期信息 ============
            stat_period TEXT NOT NULL,
            stat_year INTEGER NOT NULL,
            stat_month INTEGER NOT NULL,
            period_start TEXT,
            period_end TEXT,

            -- ============ 借阅次数统计 ============
            borrow_count_3m INTEGER,
            borrow_count_m1 INTEGER,
            borrow_count_m2 INTEGER,
            borrow_count_m3 INTEGER,

            -- ============ 元数据 ============
            created_at TEXT NOT NULL,
            updated_at TEXT,

            FOREIGN KEY (barcode) REFERENCES books(barcode) ON DELETE CASCADE,
            UNIQUE(barcode, stat_year, stat_month)
        );
        """
        self.conn.execute(sql)
        logger.debug("borrow_statistics表创建成功")

    def _create_indexes(self):
        """创建所有索引并校验绑定表"""
        index_configs = [
            # books表索引
            ("idx_books_barcode", "books", "CREATE UNIQUE INDEX IF NOT EXISTS idx_books_barcode ON books(barcode)"),
            ("idx_books_isbn", "books", "CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn)"),
            ("idx_books_douban_isbn", "books", "CREATE INDEX IF NOT EXISTS idx_books_douban_isbn ON books(douban_isbn)"),
            ("idx_books_title", "books", "CREATE INDEX IF NOT EXISTS idx_books_title ON books(book_title)"),
            ("idx_books_created_at", "books", "CREATE INDEX IF NOT EXISTS idx_books_created_at ON books(created_at)"),
            # 索书号索引 - 支持大小写不敏感查询
            ("idx_books_call_no_upper", "books", "CREATE INDEX IF NOT EXISTS idx_books_call_no_upper ON books(UPPER(TRIM(call_no))) WHERE call_no IS NOT NULL AND call_no != ''"),

            # borrow_records表索引
            ("idx_borrow_records_barcode", "borrow_records", "CREATE INDEX IF NOT EXISTS idx_borrow_records_barcode ON borrow_records(barcode)"),
            ("idx_borrow_records_reader", "borrow_records", "CREATE INDEX IF NOT EXISTS idx_borrow_records_reader ON borrow_records(reader_card_no)"),
            ("idx_borrow_records_return_time", "borrow_records", "CREATE INDEX IF NOT EXISTS idx_borrow_records_return_time ON borrow_records(return_time)"),

            # borrow_statistics表索引
            ("idx_borrow_statistics_barcode", "borrow_statistics", "CREATE INDEX IF NOT EXISTS idx_borrow_statistics_barcode ON borrow_statistics(barcode)"),
            ("idx_borrow_statistics_period", "borrow_statistics", "CREATE INDEX IF NOT EXISTS idx_borrow_statistics_period ON borrow_statistics(stat_year, stat_month)"),
            ("idx_borrow_statistics_barcode_period", "borrow_statistics", "CREATE INDEX IF NOT EXISTS idx_borrow_statistics_barcode_period ON borrow_statistics(barcode, stat_year, stat_month)")
        ]

        ensured = 0
        for index_name, table_name, index_sql in index_configs:
            if self._ensure_index(index_name, table_name, index_sql):
                ensured += 1

        logger.debug(f"索引检查完成: {ensured}/{len(index_configs)}")

    def _ensure_index(self, index_name: str, target_table: str, create_sql: str) -> bool:
        """
        确保指定索引存在且绑定正确

        Args:
            index_name: 索引名
            target_table: 目标表
            create_sql: 创建SQL
        """
        desired_unique = create_sql.strip().upper().startswith("CREATE UNIQUE INDEX")
        row = self.conn.execute(
            "SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name = ?",
            (index_name,)
        ).fetchone()

        needs_create = False
        if row:
            existing_table = row['tbl_name']
            if existing_table != target_table:
                logger.warning(
                    f"检测到索引 {index_name} 绑定到 {existing_table}, 期望表为 {target_table}, 即将重建"
                )
                self._drop_index(index_name)
                needs_create = True
            elif desired_unique and not self._is_index_unique(target_table, index_name):
                logger.warning(f"索引 {index_name} 非唯一, 需要重建以支持UPSERT")
                self._drop_index(index_name)
                needs_create = True
            else:
                return True
        else:
            needs_create = True

        if needs_create:
            try:
                self.conn.execute(create_sql)
                logger.info(f"索引 {index_name} 已创建/修复")
            except sqlite3.IntegrityError as exc:
                if desired_unique:
                    duplicates = self.conn.execute(
                        """
                        SELECT barcode, COUNT(*) as cnt
                        FROM books
                        GROUP BY barcode
                        HAVING cnt > 1
                        LIMIT 5
                        """
                    ).fetchall()
                    if duplicates:
                        duplicate_samples = ', '.join(
                            f"{row['barcode']}({row['cnt']})" for row in duplicates if row['barcode']
                        )
                        logger.error(
                            f"创建唯一索引 {index_name} 失败, 存在重复条码: {duplicate_samples}"
                        )
                        raise ValueError(
                            f"创建唯一索引 {index_name} 失败, 请先清理重复条码: {duplicate_samples}"
                        ) from exc
                raise

        return True

    def _drop_index(self, index_name: str):
        """删除索引"""
        self.conn.execute(f'DROP INDEX IF EXISTS "{index_name}"')

    def _is_index_unique(self, table: str, index_name: str) -> bool:
        """检查指定索引是否唯一"""
        cursor = self.conn.execute(f"PRAGMA index_list('{table}')")
        for row in cursor.fetchall():
            # row格式: (seq, name, unique, origin, partial)
            if row[1] == index_name:
                return bool(row[2])
        return False

    def batch_check_duplicates(self, barcodes: List[str], stale_days: int = 30, crawl_empty_url: bool = True) -> Dict:
        """
        批量查重，返回分类结果 (优化版 - 支持大批量)

        Args:
            barcodes: 条码列表
            stale_days: 过期天数（超过该天数的数据需要重新爬取）
            crawl_empty_url: 当douban_url为空时是否需要重新爬取（默认True）

        Returns:
            Dict: 分类结果
            {
                'existing_valid': [{'barcode': 'B001', 'data': book_data}, ...],
                'existing_stale': [{'barcode': 'B002', 'data': book_data}, ...],
                'new': ['B003', 'B004', ...]
            }

        Note:
            分类逻辑：
            - existing_valid: 数据库中存在，豆瓣URL有值，且未过期
            - existing_stale: 数据库中存在但豆瓣URL无值(根据crawl_empty_url配置)，或已过期需要重新爬取
            - new: 数据库中不存在
        """
        try:
            # 优化: 处理SQLite参数限制,分批查询
            BATCH_SIZE = 999
            all_existing_books = []

            for i in range(0, len(barcodes), BATCH_SIZE):
                batch = barcodes[i:i+BATCH_SIZE]
                placeholders = ','.join(['?' for _ in batch])
                sql = f"""
                    SELECT * FROM books
                    WHERE barcode IN ({placeholders})
                    ORDER BY created_at DESC
                """

                cursor = self.conn.execute(sql, batch)
                batch_books = cursor.fetchall()
                all_existing_books.extend(batch_books)

                logger.debug(f"查重批次 {i//BATCH_SIZE + 1}: 查询 {len(batch)} 条,找到 {len(batch_books)} 条")

            # 转换为字典以便快速查找
            existing_dict = {book['barcode']: dict(book) for book in all_existing_books}

            # 分类结果
            result = {
                'existing_valid': [],
                'existing_stale': [],
                'new': []
            }

            # 计算过期时间
            stale_threshold = (datetime.now() - timedelta(days=stale_days)).strftime('%Y-%m-%d %H:%M:%S')

            # 统计计数器
            stats = {
                'url_empty': 0,      # douban_url为空
                'time_stale': 0,     # 时间过期
            }

            for barcode in barcodes:
                if barcode in existing_dict:
                    book_data = existing_dict[barcode]
                    # 使用 updated_at 判断数据是否过期，如果 updated_at 为空则回退使用 created_at
                    updated_at = book_data.get('updated_at', '')
                    created_at = book_data.get('created_at', '')
                    check_time = updated_at if updated_at else created_at
                    douban_url = book_data.get('douban_url')

                    needs_update = False
                    stale_reason = None  # 记录过期原因

                    # 检查豆瓣URL是否存在
                    if not douban_url or douban_url.strip() == '':
                        if crawl_empty_url:
                            # 配置为需要爬取URL为空的记录
                            logger.debug(f"条码 {barcode}: douban_url为空,需要重新爬取")
                            needs_update = True
                            stale_reason = 'url_empty'
                            stats['url_empty'] += 1
                        else:
                            # 配置为跳过URL为空的记录
                            logger.debug(f"条码 {barcode}: douban_url为空,但配置为跳过(crawl_empty_url=False)")
                            needs_update = False
                    # 检查是否过期
                    elif check_time > stale_threshold:
                        needs_update = False
                        logger.debug(f"条码 {barcode}: 数据未过期 - updated_at={updated_at}, created_at={created_at}, stale_threshold={stale_threshold}")
                    else:
                        logger.info(f"条码 {barcode}: 数据已过期({stale_days}天) - updated_at={updated_at}, created_at={created_at}, stale_threshold={stale_threshold}")
                        needs_update = True
                        stale_reason = 'time_stale'
                        stats['time_stale'] += 1

                    if needs_update:
                        result['existing_stale'].append({
                            'barcode': barcode,
                            'data': book_data
                        })
                    else:
                        result['existing_valid'].append({
                            'barcode': barcode,
                            'data': book_data
                        })
                else:
                    result['new'].append(barcode)

            # 输出详细的统计信息
            logger.info(
                f"查重完成: {len(result['existing_valid'])}条有效, "
                f"{len(result['existing_stale'])}条需爬取 "
                f"(URL为空:{stats['url_empty']}条, 时间过期:{stats['time_stale']}条), "
                f"{len(result['new'])}条新数据"
            )

            return result

        except Exception as e:
            logger.error(f"批量查重失败: {e}")
            raise

    def batch_check_isbn_duplicates(self, barcodes: List[str]) -> Dict:
        """
        批量查重ISBN数据 (专用于ISBN爬取阶段)

        Args:
            barcodes: 条码列表

        Returns:
            Dict: 分类结果
            {
                'existing_valid': [{'barcode': 'B001', 'data': book_data}, ...],
                'existing_stale': [],  # ISBN查重不使用此分类
                'new': ['B003', 'B004', ...]
            }

        Note:
            分类逻辑：
            - existing_valid: 数据库中存在且isbn字段有值
            - existing_stale: 空列表(ISBN查重不需要此分类)
            - new: 数据库中不存在或isbn字段为空
        """
        try:
            # 优化: 处理SQLite参数限制,分批查询
            BATCH_SIZE = 999
            all_existing_books = []

            for i in range(0, len(barcodes), BATCH_SIZE):
                batch = barcodes[i:i+BATCH_SIZE]
                placeholders = ','.join(['?' for _ in batch])
                sql = f"""
                    SELECT * FROM books
                    WHERE barcode IN ({placeholders})
                    ORDER BY created_at DESC
                """

                cursor = self.conn.execute(sql, batch)
                batch_books = cursor.fetchall()
                all_existing_books.extend(batch_books)

                logger.debug(f"ISBN查重批次 {i//BATCH_SIZE + 1}: 查询 {len(batch)} 条,找到 {len(batch_books)} 条")

            # 转换为字典以便快速查找
            existing_dict = {book['barcode']: dict(book) for book in all_existing_books}

            # 分类结果
            result = {
                'existing_valid': [],
                'existing_stale': [],  # ISBN查重不使用
                'new': []
            }

            for barcode in barcodes:
                if barcode in existing_dict:
                    book_data = existing_dict[barcode]
                    isbn = book_data.get('isbn', '')

                    # 只检查isbn字段是否有值
                    if isbn and str(isbn).strip() not in ['', 'nan', 'None']:
                        result['existing_valid'].append({
                            'barcode': barcode,
                            'data': book_data
                        })
                        logger.debug(f"条码 {barcode}: ISBN已存在 - {isbn}")
                    else:
                        result['new'].append(barcode)
                        logger.debug(f"条码 {barcode}: ISBN为空,需要爬取")
                else:
                    result['new'].append(barcode)
                    logger.debug(f"条码 {barcode}: 数据库中不存在")

            logger.info(
                f"ISBN查重完成: {len(result['existing_valid'])}条有效, "
                f"{len(result['new'])}条需爬取"
            )

            return result

        except Exception as e:
            logger.error(f"ISBN批量查重失败: {e}")
            raise

    def batch_save_data(self, books_data: List[Dict], borrow_records_list: List[Dict],
                       statistics_list: List[Dict], batch_size: int = 100, update_mode: str = "merge"):
        """
        批量保存三类数据

        Args:
            books_data: books表数据列表
            borrow_records_list: borrow_records表数据列表
            statistics_list: borrow_statistics表数据列表
            batch_size: 批量写入大小
            update_mode: 更新模式（merge保留原字段，overwrite完全覆盖）
        """
        try:
            # 开始事务
            self.conn.execute("BEGIN TRANSACTION")

            # 分批保存books数据
            if books_data:
                self._batch_save_books(books_data, batch_size, update_mode)

            # 分批保存borrow_records数据
            if borrow_records_list:
                self._batch_save_borrow_records(borrow_records_list, batch_size)

            # 分批保存borrow_statistics数据
            if statistics_list:
                self._batch_save_borrow_statistics(statistics_list, batch_size)

            # 提交事务
            self.conn.commit()
            logger.info(
                f"批量保存成功 ({update_mode}模式): "
                f"{len(books_data)}条books, "
                f"{len(borrow_records_list)}条borrow_records, "
                f"{len(statistics_list)}条borrow_statistics"
            )

        except Exception as e:
            logger.error(f"批量保存失败: {e}")
            self.conn.rollback()
            raise

    def batch_get_books_by_barcodes(self, barcodes: List[str]) -> Dict[str, Dict]:
        """
        批量查询书籍信息

        Args:
            barcodes: 条码列表

        Returns:
            Dict[str, Dict]: barcode → 书籍信息的映射
        """
        if not barcodes:
            return {}

        try:
            # 处理SQLite参数限制
            BATCH_SIZE = 999
            all_books = {}

            for i in range(0, len(barcodes), BATCH_SIZE):
                batch = barcodes[i:i+BATCH_SIZE]
                placeholders = ','.join(['?' for _ in batch])
                sql = f"SELECT * FROM books WHERE barcode IN ({placeholders})"

                cursor = self.conn.execute(sql, batch)
                rows = cursor.fetchall()

                for row in rows:
                    book_dict = dict(row)
                    all_books[book_dict['barcode']] = book_dict

            logger.debug(f"批量查询完成: {len(all_books)}/{len(barcodes)} 条记录")
            return all_books

        except Exception as e:
            logger.error(f"批量查询书籍信息失败: {e}")
            return {}

    def _increment_version_in_memory(self, current_version: str) -> str:
        """
        在内存中递增版本号 (无需数据库查询)

        Args:
            current_version: 当前版本号

        Returns:
            str: 递增后的版本号
        """
        try:
            version_num = float(current_version)
            new_version_num = round(version_num + 0.1, 1)
            return f"{new_version_num:.1f}"
        except (ValueError, TypeError):
            logger.warning(f"无法解析版本号 {current_version},使用默认版本")
            return '1.0'

    def _increment_data_version(self, barcode: str) -> str:
        """
        递增data_version字段 (已废弃,保留用于向后兼容)

        Args:
            barcode: 条码

        Returns:
            str: 递增后的版本号

        Note:
            此方法已废弃,建议使用_increment_version_in_memory()避免数据库查询
        """
        try:
            # 查询现有记录
            existing_book = self.get_book_by_barcode(barcode)
            if existing_book:
                # 获取当前版本号
                current_version = existing_book.get('data_version', '1.0')
                try:
                    # 将字符串转换为浮点数，递增0.1，然后格式化回字符串
                    version_num = float(current_version)
                    new_version_num = round(version_num + 0.1, 1)
                    return f"{new_version_num:.1f}"
                except (ValueError, TypeError):
                    # 如果转换失败，返回默认版本号
                    logger.warning(f"无法解析版本号 {current_version}，使用默认版本")
                    return '1.0'
            else:
                # 新记录，返回初始版本号
                return '1.0'
        except Exception as e:
            logger.error(f"递增版本号失败: {e}")
            return '1.0'

    def _batch_save_books(self, books_data: List[Dict], batch_size: int, update_mode: str = "merge"):
        """
        批量保存books数据 (优化版)

        Args:
            books_data: books表数据列表
            batch_size: 批量写入大小
            update_mode: 更新模式（merge保留原字段，overwrite完全覆盖）
        """
        if not books_data:
            return

        # 优化: 批量预查询所有barcode
        all_barcodes = [b['barcode'] for b in books_data if 'barcode' in b]
        existing_books_map = self.batch_get_books_by_barcodes(all_barcodes)

        logger.debug(f"预查询完成: {len(existing_books_map)} 条已存在记录")

        for i in range(0, len(books_data), batch_size):
            batch = books_data[i:i + batch_size]

            for book_data in batch:
                # 确保必要字段存在
                book_data.setdefault('updated_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                # 优化: 从内存映射中获取现有记录 (无需查询)
                existing_book = None
                if 'barcode' in book_data:
                    barcode = book_data['barcode']
                    existing_book = existing_books_map.get(barcode)

                    # 优化: 在内存中处理版本号 (无需查询)
                    if existing_book:
                        current_version = existing_book.get('data_version', '1.0')
                        book_data['data_version'] = self._increment_version_in_memory(current_version)
                    else:
                        book_data['data_version'] = '1.0'
                else:
                    book_data.setdefault('data_version', '1.0')

                # 保留原有created_at
                if existing_book and existing_book.get('created_at'):
                    book_data['created_at'] = existing_book['created_at']
                else:
                    book_data.setdefault('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                # 根据更新模式构建UPSERT语句 (逻辑不变)
                if update_mode == "overwrite" or not existing_book:
                    # 完全覆盖模式
                    placeholders = ','.join(['?' for _ in book_data.keys()])
                    columns = ','.join(book_data.keys())

                    set_clauses = []
                    for key in book_data.keys():
                        if key != 'barcode':
                            set_clauses.append(f"{key} = excluded.{key}")

                    sql = f"""
                        INSERT INTO books ({columns})
                        VALUES ({placeholders})
                        ON CONFLICT(barcode) DO UPDATE SET
                            {', '.join(set_clauses)}
                        WHERE books.barcode = excluded.barcode
                    """
                    self.conn.execute(sql, list(book_data.values()))
                else:
                    # 合并模式
                    insert_columns = ['barcode']
                    insert_values = [book_data['barcode']]
                    set_clauses = []

                    for key, value in book_data.items():
                        if key == 'barcode':
                            continue

                        if value is not None and str(value).strip() != "":
                            insert_columns.append(key)
                            insert_values.append(value)
                            set_clauses.append(f"{key} = excluded.{key}")

                    set_clauses.append("updated_at = excluded.updated_at")
                    set_clauses.append("data_version = excluded.data_version")

                    placeholders = ','.join(['?' for _ in insert_columns])
                    columns = ','.join(insert_columns)

                    sql = f"""
                        INSERT INTO books ({columns})
                        VALUES ({placeholders})
                        ON CONFLICT(barcode) DO UPDATE SET
                            {', '.join(set_clauses)}
                        WHERE books.barcode = excluded.barcode
                    """
                    self.conn.execute(sql, insert_values)

            logger.debug(f"已保存books批次 {i // batch_size + 1}/{(len(books_data) - 1) // batch_size + 1} ({update_mode}模式)")

    def _batch_save_borrow_records(self, records: List[Dict], batch_size: int):
        """批量保存borrow_records数据"""
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            for record in batch:
                # 确保必要字段存在（日期格式参考excel_import.py：%Y-%m-%d %H:%M:%S）
                record.setdefault('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                # 构建INSERT OR REPLACE语句
                placeholders = ','.join(['?' for _ in record.keys()])
                columns = ','.join(record.keys())

                sql = f"""
                    INSERT INTO borrow_records ({columns})
                    VALUES ({placeholders})
                """

                self.conn.execute(sql, list(record.values()))

            logger.debug(f"已保存borrow_records批次 {i // batch_size + 1}/{(len(records) - 1) // batch_size + 1}")

    def _batch_save_borrow_statistics(self, statistics: List[Dict], batch_size: int):
        """批量保存borrow_statistics数据"""
        for i in range(0, len(statistics), batch_size):
            batch = statistics[i:i + batch_size]

            for stat in batch:
                # 确保必要字段存在（日期格式参考excel_import.py：%Y-%m-%d %H:%M:%S）
                stat.setdefault('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                stat.setdefault('updated_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                # 构建INSERT OR REPLACE语句
                placeholders = ','.join(['?' for _ in stat.keys()])
                columns = ','.join(stat.keys())

                sql = f"""
                    INSERT OR REPLACE INTO borrow_statistics ({columns})
                    VALUES ({placeholders})
                """

                self.conn.execute(sql, list(stat.values()))

            logger.debug(f"已保存borrow_statistics批次 {i // batch_size + 1}/{(len(statistics) - 1) // batch_size + 1}")

    def get_book_by_barcode(self, barcode: str) -> Optional[Dict]:
        """
        根据barcode查询书籍信息

        Args:
            barcode: 条码

        Returns:
            Optional[Dict]: 书籍信息字典，如果不存在返回None
        """
        try:
            sql = "SELECT * FROM books WHERE barcode = ?"
            cursor = self.conn.execute(sql, (barcode,))
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"查询书籍信息失败: {e}")
            return None

    def update_book_douban_info(self, barcode: str, douban_data: Dict, update_mode: str = "merge"):
        """
        更新书籍的豆瓣信息

        Args:
            barcode: 条码
            douban_data: 豆瓣数据
            update_mode: 更新模式（merge保留原字段，overwrite完全覆盖）

        Returns:
            bool: 更新是否成功
        """
        try:
            # 递增版本号
            new_data_version = self._increment_data_version(barcode)

            if update_mode == "overwrite":
                # 完全覆盖模式（保留基础信息）
                sql = """
                    UPDATE books
                    SET douban_url = ?,
                        douban_rating = ?,
                        douban_title = ?,
                        douban_subtitle = ?,
                        douban_original_title = ?,
                        douban_author = ?,
                        douban_translator = ?,
                        douban_publisher = ?,
                        douban_producer = ?,
                        douban_series = ?,
                        douban_series_link = ?,
                        douban_price = ?,
                        douban_isbn = ?,
                        douban_pages = ?,
                        douban_binding = ?,
                        douban_pub_year = ?,
                        douban_rating_count = ?,
                        douban_summary = ?,
                        douban_author_intro = ?,
                        douban_catalog = ?,
                        douban_cover_image = ?,
                        data_version = ?,
                        updated_at = ?
                    WHERE barcode = ?
                """
                self.conn.execute(sql, (
                    douban_data.get('douban_url'),
                    douban_data.get('douban_rating'),
                    douban_data.get('douban_title'),
                    douban_data.get('douban_subtitle'),
                    douban_data.get('douban_original_title'),
                    douban_data.get('douban_author'),
                    douban_data.get('douban_translator'),
                    douban_data.get('douban_publisher'),
                    douban_data.get('douban_producer'),
                    douban_data.get('douban_series'),
                    douban_data.get('douban_series_link'),
                    douban_data.get('douban_price'),
                    douban_data.get('douban_isbn'),
                    douban_data.get('douban_pages'),
                    douban_data.get('douban_binding'),
                    douban_data.get('douban_pub_year'),
                    douban_data.get('douban_rating_count'),
                    douban_data.get('douban_summary'),
                    douban_data.get('douban_author_intro'),
                    douban_data.get('douban_catalog'),
                    douban_data.get('douban_cover_image'),
                    new_data_version,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    barcode
                ))
            else:
                # 合并模式（仅更新非空字段）
                set_clauses = []
                values = []

                for key, value in douban_data.items():
                    if value is not None and value != "":
                        set_clauses.append(f"{key} = ?")
                        values.append(value)

                if set_clauses:
                    # 递增版本号
                    set_clauses.append("data_version = ?")
                    values.append(new_data_version)

                    set_clauses.append("updated_at = ?")
                    values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    values.append(barcode)

                    sql = f"""
                        UPDATE books
                        SET {', '.join(set_clauses)}
                        WHERE barcode = ?
                    """
                    self.conn.execute(sql, values)

            self.conn.commit()
            logger.debug(f"更新书籍豆瓣信息成功: {barcode}")
            return True

        except Exception as e:
            logger.error(f"更新书籍豆瓣信息失败: {e}")
            self.conn.rollback()
            return False

    def get_database_stats(self) -> Dict:
        """
        获取数据库统计信息

        Returns:
            Dict: 统计信息
        """
        try:
            stats = {}

            # 统计books表
            cursor = self.conn.execute("SELECT COUNT(*) as count FROM books")
            stats['total_books'] = cursor.fetchone()['count']

            # 统计borrow_records表
            cursor = self.conn.execute("SELECT COUNT(*) as count FROM borrow_records")
            stats['total_borrow_records'] = cursor.fetchone()['count']

            # 统计borrow_statistics表
            cursor = self.conn.execute("SELECT COUNT(*) as count FROM borrow_statistics")
            stats['total_statistics'] = cursor.fetchone()['count']

            # 统计有豆瓣信息的书籍数量
            cursor = self.conn.execute("SELECT COUNT(*) as count FROM books WHERE douban_url IS NOT NULL")
            stats['books_with_douban'] = cursor.fetchone()['count']

            # 数据库大小
            if os.path.exists(self.db_path):
                stats['db_size_mb'] = round(os.path.getsize(self.db_path) / 1024 / 1024, 2)

            return stats

        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}")
            return {}

    def create_backup(self, backup_path: str = None) -> str:
        """
        创建数据库备份

        Args:
            backup_path: 备份路径（可选）

        Returns:
            str: 备份文件路径
        """
        try:
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_dir = os.path.dirname(self.db_path)
                backup_path = os.path.join(backup_dir, f"books_history_backup_{timestamp}.db")

            # 使用SQLite的备份API
            backup_conn = sqlite3.connect(backup_path)
            self.conn.backup(backup_conn)
            backup_conn.close()

            logger.info(f"数据库备份成功: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"创建数据库备份失败: {e}")
            raise

    def batch_get_books_by_call_numbers(self, call_numbers: List[str]) -> Dict[str, Dict]:
        """
        按归一化后的索书号批量查询书籍

        Args:
            call_numbers: 索书号列表

        Returns:
            Dict[str, Dict]: normalized_call_no → 书籍信息的映射
        """
        if not call_numbers:
            return {}

        # 导入归一化函数
        from .value_normalizers import normalize_call_no

        # 归一化并过滤无效索书号
        normalized_call_numbers = []
        for cn in call_numbers:
            normalized = normalize_call_no(cn)
            if normalized:  # 过滤空值
                normalized_call_numbers.append(normalized)

        if not normalized_call_numbers:
            return {}

        try:
            # 去重，避免重复查询
            unique_call_numbers = list(set(normalized_call_numbers))

            # 处理SQLite参数限制，分批查询
            BATCH_SIZE = 999
            result = {}

            for i in range(0, len(unique_call_numbers), BATCH_SIZE):
                batch = unique_call_numbers[i:i+BATCH_SIZE]
                placeholders = ','.join(['?' for _ in batch])

                # 使用UPPER(TRIM())进行大小写不敏感的查询
                sql = f"""
                    SELECT * FROM books
                    WHERE UPPER(TRIM(call_no)) IN ({placeholders})
                    AND call_no IS NOT NULL AND call_no != ''
                """

                cursor = self.conn.execute(sql, batch)
                rows = cursor.fetchall()

                for row in rows:
                    book_dict = dict(row)
                    # 对数据库中的call_no也进行归一化作为key
                    db_call_no = book_dict.get('call_no', '')
                    normalized_key = normalize_call_no(db_call_no)
                    if normalized_key:
                        result[normalized_key] = book_dict

            logger.debug(f"索书号批量查询完成: {len(result)}/{len(call_numbers)} 条记录")
            return result

        except Exception as e:
            logger.error(f"索书号批量查询失败: {e}")
            return {}

    def _categorize_book_record(self, book_data: Dict, stale_days: int, crawl_empty_url: bool) -> Tuple[str, Optional[str]]:
        """
        分类书籍记录为有效或过期

        Args:
            book_data: 书籍数据
            stale_days: 过期天数
            crawl_empty_url: 空URL是否需要重新爬取

        Returns:
            Tuple[str, Optional[str]]: (分类, 过期原因)
            - 分类: 'existing_valid' 或 'existing_stale'
            - 过期原因: 'url_empty', 'time_stale' 或 None
        """
        # 计算过期时间
        stale_threshold = (datetime.now() - timedelta(days=stale_days)).strftime('%Y-%m-%d %H:%M:%S')

        # 获取时间字段，优先使用updated_at
        updated_at = book_data.get('updated_at', '')
        created_at = book_data.get('created_at', '')
        check_time = updated_at if updated_at else created_at

        douban_url = book_data.get('douban_url')

        # 检查豆瓣URL是否存在
        if not douban_url or douban_url.strip() == '':
            if crawl_empty_url:
                logger.debug(f"索书号匹配: douban_url为空,需要重新爬取")
                return 'existing_stale', 'url_empty'
            else:
                logger.debug(f"索书号匹配: douban_url为空,但配置为跳过(crawl_empty_url=False)")
                return 'existing_valid', None

        # 检查是否过期
        if check_time and check_time > stale_threshold:
            logger.debug(f"索书号匹配: 数据未过期 - {check_time}")
            return 'existing_valid', None
        else:
            logger.info(f"索书号匹配: 数据已过期({stale_days}天) - {check_time}")
            return 'existing_stale', 'time_stale'

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
