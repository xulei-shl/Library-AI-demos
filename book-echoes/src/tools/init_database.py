#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
根据历史数据查重数据库设计文档，初始化 SQLite 数据库表

作者：豆瓣评分模块开发组
版本：1.0
创建时间：2025-11-04
"""

import sqlite3
import os
import yaml
from pathlib import Path


class DatabaseInitializer:
    """数据库初始化器"""

    def __init__(self, db_path: str = None):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径（如果为None，将从配置文件中读取）
        """
        self.db_path = db_path
        self.conn = None

    @staticmethod
    def load_config(config_path: str = "config/setting.yaml"):
        """
        加载配置文件

        Args:
            config_path: 配置文件路径

        Returns:
            dict: 配置信息
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            print(f"[警告] 配置文件不存在: {config_path}")
            return {}
        except yaml.YAMLError as e:
            print(f"[错误] 解析配置文件失败: {e}")
            return {}
        except Exception as e:
            print(f"[错误] 读取配置文件时发生错误: {e}")
            return {}

    def get_db_path_from_config(self, config_path: str = "config/setting.yaml"):
        """
        从配置文件中获取数据库路径

        Args:
            config_path: 配置文件路径

        Returns:
            str: 数据库文件路径
        """
        config = self.load_config(config_path)

        # 从配置文件中读取数据库配置
        db_config = config.get('douban', {}).get('database', {})

        if self.db_path:
            # 如果已经指定了路径，使用指定的路径
            return self.db_path

        # 直接读取 db_path 字段（配置文件中的实际字段）
        db_path = db_config.get('db_path')

        if db_path:
            # 确保目录存在
            db_dir = os.path.dirname(db_path)
            if db_dir:
                Path(db_dir).mkdir(parents=True, exist_ok=True)
            return db_path

        # 如果配置文件没有提供路径，使用默认值
        return "runtime/outputs/books_history.db"

    def connect(self):
        """建立数据库连接"""
        # 如果没有指定数据库路径，从配置文件读取
        if not self.db_path:
            self.db_path = self.get_db_path_from_config()

        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # 允许使用列名访问
            print(f"[成功] 连接到数据库: {self.db_path}")
            return True
        except Exception as e:
            print(f"[错误] 数据库连接失败: {e}")
            return False

    def create_books_table(self):
        """创建books表（书籍基础信息和豆瓣信息）"""
        sql = """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE NOT NULL,  -- 书目条码（唯一键）

            -- ============ 书籍基础信息（不变）===========
            call_no TEXT NOT NULL,         -- 索书号
            cleaned_call_no TEXT,          -- 清理后索书号
            book_title TEXT NOT NULL,      -- 书名
            additional_info TEXT,          -- 附加信息
            isbn TEXT,                     -- ISBN号

            -- ============ 豆瓣信息（1对1，不变）===========
            douban_url TEXT,               -- 豆瓣链接
            douban_rating REAL,            -- 豆瓣评分
            douban_title TEXT,             -- 豆瓣书名
            douban_subtitle TEXT,          -- 豆瓣副标题
            douban_original_title TEXT,    -- 豆瓣原作名
            douban_author TEXT,            -- 豆瓣作者
            douban_translator TEXT,        -- 豆瓣译者
            douban_publisher TEXT,         -- 豆瓣出版社
            douban_producer TEXT,          -- 豆瓣出品方
            douban_series TEXT,            -- 豆瓣丛书
            douban_series_link TEXT,       -- 豆瓣丛书链接
            douban_price TEXT,             -- 豆瓣定价
            douban_isbn TEXT,              -- 豆瓣ISBN
            douban_pages INTEGER,          -- 豆瓣页数
            douban_binding TEXT,           -- 豆瓣装帧
            douban_pub_year INTEGER,       -- 豆瓣出版年
            douban_rating_count INTEGER,   -- 豆瓣评价人数
            douban_summary TEXT,           -- 豆瓣内容简介
            douban_author_intro TEXT,      -- 豆瓣作者简介
            douban_catalog TEXT,           -- 豆瓣目录
            douban_cover_image TEXT,       -- 豆瓣封面图片链接

            -- ============ 元数据 ============
            data_version TEXT DEFAULT '1.0',
            created_at TEXT NOT NULL,
            updated_at TEXT
        );
        """
        cursor = self.conn.cursor()
        cursor.execute(sql)

        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_books_barcode ON books(barcode)",
            "CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn)",
            "CREATE INDEX IF NOT EXISTS idx_books_douban_isbn ON books(douban_isbn)",
            "CREATE INDEX IF NOT EXISTS idx_books_title ON books(book_title)"
        ]
        for index_sql in indexes:
            cursor.execute(index_sql)

        self.conn.commit()
        print("[成功] books表创建成功")

    def create_borrow_records_table(self):
        """创建borrow_records表（借阅记录）"""
        sql = """
        CREATE TABLE IF NOT EXISTS borrow_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL,  -- 外键，关联books表

            -- ============ 借阅记录信息 ============
            reader_card_no TEXT NOT NULL,  -- 读者卡号
            submit_time TEXT,              -- 提交时间
            return_time TEXT,              -- 归还时间
            storage_time TEXT,             -- 入库时间

            -- ============ 元数据 ============
            created_at TEXT NOT NULL,      -- 记录创建时间

            -- 外键和索引
            FOREIGN KEY (barcode) REFERENCES books(barcode) ON DELETE CASCADE
        );
        """
        cursor = self.conn.cursor()
        cursor.execute(sql)

        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_borrow_records_barcode ON borrow_records(barcode)",
            "CREATE INDEX IF NOT EXISTS idx_borrow_records_reader ON borrow_records(reader_card_no)",
            "CREATE INDEX IF NOT EXISTS idx_borrow_records_return_time ON borrow_records(return_time)"
        ]
        for index_sql in indexes:
            cursor.execute(index_sql)

        self.conn.commit()
        print("[成功] borrow_records表创建成功")

    def create_borrow_statistics_table(self):
        """创建borrow_statistics表（统计信息）"""
        sql = """
        CREATE TABLE IF NOT EXISTS borrow_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL,  -- 外键，关联books表

            -- ============ 统计周期信息 ============
            stat_period TEXT NOT NULL,     -- 统计周期标识（如"2024-10"）
            stat_year INTEGER NOT NULL,    -- 统计年份
            stat_month INTEGER NOT NULL,   -- 统计月份（1-12）
            period_start TEXT,             -- 周期开始时间
            period_end TEXT,               -- 周期结束时间

            -- ============ 借阅次数统计 ============
            borrow_count_3m INTEGER,       -- 近三个月总次数
            borrow_count_m1 INTEGER,       -- 第一月借阅次数
            borrow_count_m2 INTEGER,       -- 第二月借阅次数
            borrow_count_m3 INTEGER,       -- 第三月借阅次数
            unique_reader_count_3m INTEGER,        -- 借阅人数（去重后的读者数）

            -- ============ 元数据 ============
            created_at TEXT NOT NULL,      -- 记录创建时间
            updated_at TEXT,               -- 记录更新时间

            -- 外键和索引
            FOREIGN KEY (barcode) REFERENCES books(barcode) ON DELETE CASCADE,

            -- 确保同一本书在同一统计周期只有一条记录
            UNIQUE(barcode, stat_year, stat_month)
        );
        """
        cursor = self.conn.cursor()
        cursor.execute(sql)

        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_borrow_statistics_barcode ON borrow_statistics(barcode)",
            "CREATE INDEX IF NOT EXISTS idx_borrow_statistics_period ON borrow_statistics(stat_year, stat_month)",
            "CREATE INDEX IF NOT EXISTS idx_borrow_statistics_barcode_period ON borrow_statistics(barcode, stat_year, stat_month)"
        ]
        for index_sql in indexes:
            cursor.execute(index_sql)

        self.conn.commit()
        print("[成功] borrow_statistics表创建成功")

    def create_recommendation_results_table(self):
        """创建recommendation_results表(书目推荐评选结果)"""
        sql = """
        CREATE TABLE IF NOT EXISTS recommendation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL,  -- 外键,关联books表

            -- ============ 评选批次信息 ============
            evaluation_batch TEXT,             -- 评选批次标识(如"2025-01"、"2025春季"等)
            evaluation_date TEXT,              -- 评选日期

            -- ============ 初评信息 ============
            preliminary_result TEXT,           -- 初评结果
            preliminary_score REAL,            -- 初评分数
            preliminary_reason TEXT,           -- 初评理由
            preliminary_elimination_reason TEXT,  -- 初评淘汰原因
            preliminary_elimination_note TEXT,    -- 初评淘汰说明

            -- ============ 主题内决选信息 ============
            theme_final_result TEXT,           -- 主题内决选结果
            theme_final_reason TEXT,           -- 主题内决选理由

            -- ============ 终评信息 ============
            final_result TEXT,                 -- 终评结果
            final_score REAL,                  -- 终评分数
            final_reason TEXT,                 -- 终评理由
            final_elimination_reason TEXT,     -- 终评淘汰原因
            final_elimination_note TEXT,       -- 终评淘汰说明

            -- ============ 人工评选信息 ============
            manual_selection TEXT,             -- 人工评选
            manual_recommendation TEXT,        -- 人工推荐语

            -- ============ 元数据 ============
            created_at TEXT NOT NULL,          -- 记录创建时间
            updated_at TEXT,                   -- 记录更新时间

            -- 外键
            FOREIGN KEY (barcode) REFERENCES books(barcode) ON DELETE CASCADE,
            
            -- 确保同一本书在同一评选批次只有一条记录
            UNIQUE(barcode, evaluation_batch)
        );
        """
        cursor = self.conn.cursor()
        cursor.execute(sql)

        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_recommendation_results_barcode ON recommendation_results(barcode)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_results_batch ON recommendation_results(evaluation_batch)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_results_barcode_batch ON recommendation_results(barcode, evaluation_batch)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_results_preliminary ON recommendation_results(preliminary_result)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_results_final ON recommendation_results(final_result)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_results_manual ON recommendation_results(manual_selection)"
        ]
        for index_sql in indexes:
            cursor.execute(index_sql)

        self.conn.commit()
        print("[成功] recommendation_results表创建成功")

    def create_tables(self):
        """创建所有表"""
        try:
            print("\n" + "="*50)
            print("开始创建数据库表...")
            print("="*50)

            # 按依赖顺序创建表（books表无依赖，先创建）
            self.create_books_table()
            self.create_borrow_records_table()
            self.create_borrow_statistics_table()
            self.create_recommendation_results_table()

            print("\n" + "="*50)
            print("[成功] 所有表创建完成！")
            print("="*50)
            return True
        except Exception as e:
            print(f"\n[错误] 创建表时发生错误: {e}")
            self.conn.rollback()
            return False

    def verify_tables(self):
        """验证表是否创建成功"""
        cursor = self.conn.cursor()

        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()

        print("\n数据库表验证:")
        print("-" * 50)
        expected_tables = ['books', 'borrow_records', 'borrow_statistics', 'recommendation_results']
        for table_name in expected_tables:
            if (table_name,) in tables:
                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                print(f"[成功] {table_name} - {len(columns)} 列")

                # 获取索引信息
                cursor.execute(f"PRAGMA index_list({table_name})")
                indexes = cursor.fetchall()
                if indexes:
                    print(f"   └─ 索引数量: {len(indexes)}")
            else:
                print(f"[错误] {table_name} - 表不存在")

        print("-" * 50)

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            print(f"\n[信息] 数据库连接已关闭")


def init_database(db_path: str = None):
    """
    初始化数据库

    Args:
        db_path: 数据库文件路径（如果为None，从配置文件读取）
    """
    # 初始化数据库（不传递路径，让它从配置文件读取）
    initializer = DatabaseInitializer(db_path)

    # 获取实际使用的数据库路径
    if not initializer.db_path:
        initializer.db_path = initializer.get_db_path_from_config()

    # 确保数据库目录存在
    db_dir = os.path.dirname(initializer.db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"[信息] 创建数据库目录: {db_dir}")

    # 获取绝对路径
    abs_db_path = os.path.abspath(initializer.db_path)
    print(f"\n数据库文件路径: {abs_db_path}")

    try:
        if initializer.connect():
            initializer.create_tables()
            initializer.verify_tables()

            print("\n" + "="*50)
            print("[成功] 数据库初始化完成！")
            print("="*50)
            print("\n数据库表说明:")
            print("  - books: 书籍基础信息和豆瓣信息")
            print("  - borrow_records: 借阅记录历史")
            print("  - borrow_statistics: 每月统计汇总")
            print("  - recommendation_results: 书目推荐评选结果")
            print("\n现在可以在主程序中使用此数据库了。")

    except Exception as e:
        print(f"\n[错误] 初始化失败: {e}")
        raise
    finally:
        initializer.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='初始化豆瓣评分模块数据库')
    parser.add_argument(
        '--db-path',
        type=str,
        default=None,
        help='数据库文件路径（默认: 从配置文件读取，使用 config/setting.yaml 中的设置）'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='强制重新创建数据库（如果已存在）'
    )

    args = parser.parse_args()

    # 检查数据库是否已存在
    if args.db_path and os.path.exists(args.db_path) and not args.force:
        print(f"[警告] 数据库文件已存在: {args.db_path}")
        print("使用 --force 参数强制重新创建，或手动删除现有数据库文件。")
        response = input("是否删除现有数据库并重新创建？(y/N): ")
        if response.lower() == 'y':
            os.remove(args.db_path)
            print(f"已删除现有数据库文件")
        else:
            print("取消操作")
            exit(0)

    # 执行初始化
    init_database(args.db_path)
