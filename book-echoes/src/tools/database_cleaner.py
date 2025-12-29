#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库清洗工具
对books表进行数据清洗：
1. 按call_no字段去重合并，保留最新数据的字段值
2. 清洗barcode字段，去除末尾的.0

作者：数据库清洗工具开发组
版本：1.0
创建时间：2025-12-18
"""

import sqlite3
import yaml
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


class DatabaseCleaner:
    """数据库清洗器"""

    def __init__(self, db_path: str = None, config_path: str = "config/setting.yaml"):
        """
        初始化清洗器

        Args:
            db_path: 数据库文件路径（如果为None，从配置文件读取）
            config_path: 配置文件路径
        """
        self.db_path = db_path
        self.config_path = config_path
        self.conn = None
        
        # 设置日志
        self.setup_logging()
        
        # 统计信息
        self.stats = {
            'total_records': 0,
            'duplicate_groups': 0,
            'merged_records': 0,
            'cleaned_barcodes': 0,
            'final_records': 0
        }

    def setup_logging(self):
        """设置日志记录"""
        # 创建日志目录
        log_dir = Path("runtime/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置日志文件名（带时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"database_cleaning_{timestamp}.log"
        
        # 配置日志格式
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("="*60)
        self.logger.info("数据库清洗工具启动")
        self.logger.info("="*60)

    def load_config(self):
        """
        加载配置文件

        Returns:
            dict: 配置信息
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            self.logger.error(f"配置文件不存在: {self.config_path}")
            return {}
        except yaml.YAMLError as e:
            self.logger.error(f"解析配置文件失败: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"读取配置文件时发生错误: {e}")
            return {}

    def get_db_path_from_config(self):
        """从配置文件中获取数据库路径"""
        config = self.load_config()

        # 优先使用命令行参数指定的路径
        if self.db_path:
            return self.db_path

        # 从配置中获取完整路径
        db_config = config.get('douban', {}).get('database', {})
        db_path = db_config.get('db_path', 'runtime/database/books_history.db')

        # 确保目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)

        return db_path

    def connect(self):
        """建立数据库连接"""
        if not self.db_path:
            self.db_path = self.get_db_path_from_config()

        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # 允许使用列名访问
            self.logger.info(f"成功连接到数据库: {self.db_path}")
            return True
        except Exception as e:
            self.logger.error(f"数据库连接失败: {e}")
            return False

    def get_table_schema(self, table_name: str) -> Tuple[Dict[str, str], str]:
        """
        获取表结构

        Args:
            table_name: 表名

        Returns:
            tuple: (字段名到字段类型的映射, 主键列名)
        """
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        schema = {col[1]: col[2] for col in columns}
        # col[5] 是 pk 字段（1 表示是主键）
        primary_key = next((col[1] for col in columns if col[5] == 1), '')
        return schema, primary_key

    def get_all_books(self) -> List[sqlite3.Row]:
        """
        获取所有书籍记录

        Returns:
            list: 书籍记录列表
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM books ORDER BY call_no, updated_at DESC")
        return cursor.fetchall()

    def clean_barcode(self, barcode: str) -> str:
        """
        清洗barcode字段，去除末尾的.0

        Args:
            barcode: 原始barcode

        Returns:
            str: 清洗后的barcode
        """
        if not barcode:
            return barcode
        
        barcode_str = str(barcode).strip()
        
        # 如果以.0结尾，则去除
        if barcode_str.endswith('.0'):
            cleaned = barcode_str[:-2]
            self.logger.debug(f"清洗barcode: {barcode_str} -> {cleaned}")
            self.stats['cleaned_barcodes'] += 1
            return cleaned
        
        return barcode_str

    def merge_records_by_call_no(self, records: List[sqlite3.Row]) -> Dict[str, Any]:
        """
        按call_no合并记录，保留最新数据的字段值

        Args:
            records: 相同call_no的记录列表（按updated_at降序排列）

        Returns:
            dict: 合并后的记录
        """
        if not records:
            return None
        
        if len(records) == 1:
            # 只有一条记录，直接返回字典
            return dict(records[0])
        
        # 多条记录，进行合并
        self.logger.debug(f"合并 {len(records)} 条记录，call_no: {records[0]['call_no']}")
        
        # 第一条记录是最新的（按updated_at降序排列）
        merged = dict(records[0])
        
        # 遍历其他记录，补充空字段
        for record in records[1:]:
            record_dict = dict(record)
            for field_name, field_value in record_dict.items():
                # 如果当前记录的字段为空，且其他记录有值，则使用其他记录的值
                if (merged.get(field_name) is None or merged.get(field_name) == '') and field_value is not None and field_value != '':
                    merged[field_name] = field_value
                    self.logger.debug(f"  字段 {field_name}: 使用值 {field_value}")
        
        # 返回字典
        return merged

    def clean_books_data(self):
        """清洗books表数据"""
        self.logger.info("开始清洗books表数据...")

        # 获取表结构
        schema, primary_key = self.get_table_schema('books')
        self.logger.info(f"books表结构: {len(schema)} 个字段, 主键: {primary_key}")
        
        # 获取所有记录
        all_records = self.get_all_books()
        self.stats['total_records'] = len(all_records)
        self.logger.info(f"读取到 {len(all_records)} 条记录")
        
        # 按call_no分组
        call_no_groups = {}
        for record in all_records:
            call_no = record['call_no']
            if call_no not in call_no_groups:
                call_no_groups[call_no] = []
            call_no_groups[call_no].append(record)
        
        self.stats['duplicate_groups'] = len(call_no_groups)
        self.logger.info(f"按call_no分组后，共 {len(call_no_groups)} 个不同的call_no")
        
        # 合并记录
        merged_records = []
        for call_no, records in call_no_groups.items():
            if len(records) > 1:
                self.logger.debug(f"call_no {call_no} 有 {len(records)} 条重复记录")
            
            # 合并记录（已按updated_at降序排列）
            merged_record = self.merge_records_by_call_no(records)
            merged_records.append(merged_record)
            
            if len(records) > 1:
                self.stats['merged_records'] += len(records) - 1
        
        # 清洗barcode字段
        cleaned_records = []
        for record in merged_records:
            record_dict = dict(record)
            
            # 清洗barcode
            original_barcode = record_dict.get('barcode')
            cleaned_barcode = self.clean_barcode(original_barcode)
            record_dict['barcode'] = cleaned_barcode
            
            cleaned_records.append(record_dict)

        # 创建临时表
        cursor = self.conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS books_temp")

        # 创建临时表结构（正确处理主键和AUTOINCREMENT）
        column_defs = []
        for col_name, col_type in schema.items():
            if col_name == primary_key and col_type.upper() == 'INTEGER':
                # 主键INTEGER列需要添加AUTOINCREMENT
                column_defs.append(f"{col_name} {col_type} PRIMARY KEY AUTOINCREMENT")
            else:
                column_defs.append(f"{col_name} {col_type}")

        columns_sql = ", ".join(column_defs)
        cursor.execute(f"CREATE TABLE books_temp ({columns_sql})")
        
        # 插入清洗后的数据
        for record in cleaned_records:
            # 准备插入数据
            insert_data = {}
            for field_name in schema.keys():
                insert_data[field_name] = record.get(field_name)
            
            # 构建SQL
            columns = ", ".join(insert_data.keys())
            placeholders = ", ".join(["?" for _ in insert_data])
            values = list(insert_data.values())
            
            cursor.execute(f"INSERT INTO books_temp ({columns}) VALUES ({placeholders})", values)
        
        self.stats['final_records'] = len(cleaned_records)
        self.logger.info(f"清洗后记录数: {len(cleaned_records)}")
        
        # 备份原表
        cursor.execute("ALTER TABLE books RENAME TO books_backup")
        
        # 重命名临时表
        cursor.execute("ALTER TABLE books_temp RENAME TO books")
        
        # 重新创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_books_barcode ON books(barcode)",
            "CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn)",
            "CREATE INDEX IF NOT EXISTS idx_books_douban_isbn ON books(douban_isbn)",
            "CREATE INDEX IF NOT EXISTS idx_books_title ON books(book_title)"
        ]
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        # 提交事务
        self.conn.commit()
        
        self.logger.info("books表数据清洗完成")

    def backup_database(self):
        """备份数据库"""
        backup_path = self.db_path.replace('.db', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
        
        try:
            # 创建备份连接
            backup_conn = sqlite3.connect(backup_path)
            
            # 备份数据
            with backup_conn:
                self.conn.backup(backup_conn)
            
            backup_conn.close()
            self.logger.info(f"数据库已备份到: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"备份数据库失败: {e}")
            return None

    def run_cleaning(self, backup: bool = True):
        """
        执行数据清洗

        Args:
            backup: 是否在清洗前备份数据库
        """
        try:
            # 连接数据库
            if not self.connect():
                return False
            
            # 备份数据库
            if backup:
                backup_path = self.backup_database()
                if not backup_path:
                    self.logger.warning("数据库备份失败，但继续执行清洗")
            
            # 执行清洗
            self.clean_books_data()
            
            # 输出统计信息
            self.logger.info("="*60)
            self.logger.info("数据清洗完成统计:")
            self.logger.info(f"  原始记录数: {self.stats['total_records']}")
            self.logger.info(f"  call_no分组数: {self.stats['duplicate_groups']}")
            self.logger.info(f"  合并记录数: {self.stats['merged_records']}")
            self.logger.info(f"  清洗barcode数: {self.stats['cleaned_barcodes']}")
            self.logger.info(f"  最终记录数: {self.stats['final_records']}")
            self.logger.info("="*60)
            
            return True
            
        except Exception as e:
            self.logger.error(f"数据清洗过程中发生错误: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.logger.info("数据库连接已关闭")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='清洗books表数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s                                    # 使用默认配置清洗数据
  %(prog)s --db-path custom.db               # 指定数据库路径
  %(prog)s --no-backup                       # 不备份数据库
        """
    )
    
    parser.add_argument(
        '--db-path',
        type=str,
        default=None,
        help='数据库文件路径（默认: 从配置文件读取）'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/setting.yaml',
        help='配置文件路径（默认: config/setting.yaml）'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='不备份数据库（默认: 备份）'
    )
    
    args = parser.parse_args()
    
    # 创建清洗器
    cleaner = DatabaseCleaner(db_path=args.db_path, config_path=args.config)
    
    try:
        # 执行清洗
        print("\n" + "="*60)
        print("开始数据清洗...")
        print("="*60)
        
        success = cleaner.run_cleaning(backup=not args.no_backup)
        
        if success:
            print("\n" + "="*60)
            print("数据清洗完成!")
            print("="*60)
            print(f"  原始记录数: {cleaner.stats['total_records']}")
            print(f"  最终记录数: {cleaner.stats['final_records']}")
            print(f"  合并记录数: {cleaner.stats['merged_records']}")
            print(f"  清洗barcode数: {cleaner.stats['cleaned_barcodes']}")
            print("="*60)
            return 0
        else:
            print("\n" + "="*60)
            print("数据清洗失败!")
            print("="*60)
            return 1
            
    except Exception as e:
        print(f"\n[错误] 数据清洗过程中发生错误: {e}")
        return 1
    finally:
        cleaner.close()


if __name__ == "__main__":
    exit(main())