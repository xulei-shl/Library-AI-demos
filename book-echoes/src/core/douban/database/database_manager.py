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
        """创建所有索引"""
        indexes = [
            # books表索引
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_books_barcode ON books(barcode)",
            "CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn)",
            "CREATE INDEX IF NOT EXISTS idx_books_douban_isbn ON books(douban_isbn)",
            "CREATE INDEX IF NOT EXISTS idx_books_title ON books(book_title)",
            "CREATE INDEX IF NOT EXISTS idx_books_created_at ON books(created_at)",

            # borrow_records表索引
            "CREATE INDEX IF NOT EXISTS idx_borrow_records_barcode ON borrow_records(barcode)",
            "CREATE INDEX IF NOT EXISTS idx_borrow_records_reader ON borrow_records(reader_card_no)",
            "CREATE INDEX IF NOT EXISTS idx_borrow_records_return_time ON borrow_records(return_time)",

            # borrow_statistics表索引
            "CREATE INDEX IF NOT EXISTS idx_borrow_statistics_barcode ON borrow_statistics(barcode)",
            "CREATE INDEX IF NOT EXISTS idx_borrow_statistics_period ON borrow_statistics(stat_year, stat_month)",
            "CREATE INDEX IF NOT EXISTS idx_borrow_statistics_barcode_period ON borrow_statistics(barcode, stat_year, stat_month)"
        ]

        for index_sql in indexes:
            self.conn.execute(index_sql)

        logger.debug(f"创建了 {len(indexes)} 个索引")

    def batch_check_duplicates(self, barcodes: List[str], stale_days: int = 30) -> Dict:
        """
        批量查重，返回分类结果

        Args:
            barcodes: 条码列表
            stale_days: 过期天数（超过该天数的数据需要重新爬取）

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
            - existing_stale: 数据库中存在但豆瓣URL无值，或已过期需要重新爬取
            - new: 数据库中不存在
        """
        try:
            # 批量查询所有barcode
            placeholders = ','.join(['?' for _ in barcodes])
            sql = f"""
                SELECT * FROM books
                WHERE barcode IN ({placeholders})
                ORDER BY created_at DESC
            """

            cursor = self.conn.execute(sql, barcodes)
            existing_books = cursor.fetchall()

            # 转换为字典以便快速查找
            existing_dict = {book['barcode']: dict(book) for book in existing_books}

            # 分类结果
            result = {
                'existing_valid': [],
                'existing_stale': [],
                'new': []
            }

            # 计算过期时间（日期格式参考excel_import.py：%Y-%m-%d %H:%M:%S）
            stale_threshold = (datetime.now() - timedelta(days=stale_days)).strftime('%Y-%m-%d %H:%M:%S')

            for barcode in barcodes:
                if barcode in existing_dict:
                    book_data = existing_dict[barcode]
                    created_at = book_data.get('created_at', '')
                    douban_url = book_data.get('douban_url')

                    # 检查是否需要重新爬取
                    needs_update = False

                    # 1. 检查豆瓣URL是否存在（新增逻辑）
                    if not douban_url or douban_url.strip() == '':
                        # 豆瓣URL为空，需要重新爬取
                        logger.debug(f"条码 {barcode}: douban_url为空，需要重新爬取")
                        needs_update = True
                    # 2. 检查是否过期
                    elif created_at > stale_threshold:
                        # 未过期且有豆瓣URL
                        needs_update = False
                    else:
                        # 已过期，需要重新爬取
                        logger.debug(f"条码 {barcode}: 数据已过期（{stale_days}天），需要重新爬取")
                        needs_update = True

                    if needs_update:
                        # 需要重新爬取
                        result['existing_stale'].append({
                            'barcode': barcode,
                            'data': book_data
                        })
                    else:
                        # 数据库中存在且有有效豆瓣URL，直接使用
                        result['existing_valid'].append({
                            'barcode': barcode,
                            'data': book_data
                        })
                else:
                    # 不存在，需要完整流程
                    result['new'].append(barcode)

            logger.info(
                f"查重完成: {len(result['existing_valid'])}条有效, "
                f"{len(result['existing_stale'])}条需爬取, "
                f"{len(result['new'])}条新数据"
            )

            return result

        except Exception as e:
            logger.error(f"批量查重失败: {e}")
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

    def _increment_data_version(self, barcode: str) -> str:
        """
        递增data_version字段

        Args:
            barcode: 条码

        Returns:
            str: 递增后的版本号
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
        批量保存books数据

        Args:
            books_data: books表数据列表
            batch_size: 批量写入大小
            update_mode: 更新模式（merge保留原字段，overwrite完全覆盖）
        """
        for i in range(0, len(books_data), batch_size):
            batch = books_data[i:i + batch_size]

            for book_data in batch:
                # 确保必要字段存在（日期格式参考excel_import.py：%Y-%m-%d %H:%M:%S）
                book_data.setdefault('updated_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                # 获取现有的created_at（如果存在）
                existing_book = None
                if 'barcode' in book_data:
                    barcode = book_data['barcode']
                    existing_book = self.get_book_by_barcode(barcode)

                    # 处理data_version字段 - 递增版本号
                    book_data['data_version'] = self._increment_data_version(barcode)
                else:
                    # 没有barcode的新记录
                    book_data.setdefault('data_version', '1.0')

                # 如果已存在，保留原有的created_at；否则使用当前时间
                if existing_book and existing_book.get('created_at'):
                    book_data['created_at'] = existing_book['created_at']
                else:
                    book_data.setdefault('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                # 根据更新模式构建不同的UPSERT语句
                if update_mode == "overwrite" or not existing_book:
                    # 完全覆盖模式或新记录：更新所有字段
                    placeholders = ','.join(['?' for _ in book_data.keys()])
                    columns = ','.join(book_data.keys())

                    set_clauses = []
                    for key in book_data.keys():
                        if key != 'barcode':  # barcode在WHERE子句中使用
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
                    # 合并模式：只更新非空字段（保留数据库中已有但新数据中为空的字段）
                    # 关键修复：确保INSERT的字段与UPDATE的字段匹配
                    insert_columns = ['barcode']  # 总是包含barcode
                    insert_values = [book_data['barcode']]
                    set_clauses = []
                    update_values = []

                    # 只处理非空字段
                    for key, value in book_data.items():
                        if key == 'barcode':
                            continue  # 已处理

                        if value is not None and str(value).strip() != "":
                            # 插入时包含这个字段
                            insert_columns.append(key)
                            insert_values.append(value)

                            # 更新时也包含这个字段
                            set_clauses.append(f"{key} = excluded.{key}")
                            update_values.append(value)

                    # 添加updated_at字段（总是更新）
                    set_clauses.append("updated_at = excluded.updated_at")
                    update_values.append(book_data['updated_at'])

                    # 添加data_version字段（总是更新）
                    set_clauses.append("data_version = excluded.data_version")
                    update_values.append(book_data['data_version'])

                    # 生成SQL，确保INSERT和UPDATE的列数匹配
                    placeholders = ','.join(['?' for _ in insert_columns])
                    columns = ','.join(insert_columns)
                    all_values = insert_values + update_values

                    sql = f"""
                        INSERT INTO books ({columns})
                        VALUES ({placeholders})
                        ON CONFLICT(barcode) DO UPDATE SET
                            {', '.join(set_clauses)}
                        WHERE books.barcode = excluded.barcode
                    """
                    # 修复参数绑定数量问题：merge模式使用excluded引用，不需要绑定update_values
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
