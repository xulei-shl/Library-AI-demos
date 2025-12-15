#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Excel数据导入脚本（带版本控制）
将Excel文件中的数据导入到SQLite数据库中，支持版本控制和去重逻辑

作者：豆瓣评分模块开发组
版本：2.0
创建时间：2025-12-15
"""

import sqlite3
import pandas as pd
import argparse
import sys
from datetime import datetime
from pathlib import Path
import yaml
import os
import re
import logging


class ExcelImporterWithVersion:
    """Excel数据导入器（带版本控制）"""

    def __init__(self, db_path: str = None, config_path: str = "config/setting.yaml"):
        """
        初始化导入器

        Args:
            db_path: 数据库文件路径（如果为None，从配置文件读取）
            config_path: 配置文件路径
        """
        self.db_path = db_path
        self.config_path = config_path
        self.conn = None
        
        # 设置日志
        self.setup_logging()
        
        # 从配置文件加载字段映射
        self.column_mapping = self._load_field_mapping()
        
        # 统计信息
        self.stats = {
            'total_records': 0,
            'new_records': 0,
            'updated_records': 0,
            'skipped_records': 0,
            'error_records': 0
        }

    def setup_logging(self):
        """设置日志记录"""
        # 创建日志目录
        log_dir = Path("runtime/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置日志文件名（带时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"excel_import_{timestamp}.log"
        
        # 配置日志格式
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("="*60)
        self.logger.info("Excel导入脚本（带版本控制）启动")
        self.logger.info("="*60)

    def _load_field_mapping(self):
        """
        从配置文件加载字段映射

        Returns:
            dict: 字段映射字典（Excel列名 → 数据库字段名）
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.error(f"配置文件不存在: {self.config_path}")
            return {}
        except yaml.YAMLError as e:
            self.logger.error(f"解析配置文件失败: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"读取配置文件时发生错误: {e}")
            return {}

        # 从统一字段映射配置加载
        fields_mapping = config.get('fields_mapping', {})
        excel_to_db_mapping = fields_mapping.get('excel_to_database', {})

        if excel_to_db_mapping:
            self.logger.info("使用统一字段映射配置 (fields_mapping)")
            return excel_to_db_mapping
        else:
            self.logger.error("未找到统一字段映射配置")
            return {}

    def get_db_path_from_config(self):
        """从配置文件中获取数据库路径"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"读取配置文件失败: {e}")
            return "runtime/database/books_history.db"

        # 优先使用命令行参数指定的路径
        if self.db_path:
            return self.db_path

        db_config = config.get('douban', {}).get('database', {})

        # 从配置中获取完整路径
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
            self.logger.info(f"成功连接到数据库: {self.db_path}")
            return True
        except Exception as e:
            self.logger.error(f"数据库连接失败: {e}")
            return False

    def convert_value(self, value, target_type, target_field=None):
        """转换数据类型"""
        if value is None or value == '':
            return None

        try:
            if target_type == 'INTEGER':
                if isinstance(value, (int, float)):
                    return int(value)

                # 清洗数据中的特殊格式
                value_str = str(value).strip()

                # 特殊处理豆瓣出版年字段 - 从日期格式中提取年份
                year_match = re.match(r'(\d{4})', value_str)
                if year_match:
                    return int(year_match.group(1))

                # 特殊处理豆瓣评价人数字段 - 从 "XX人评价" 中提取数字
                count_match = re.search(r'(\d+)', value_str)
                if count_match:
                    return int(count_match.group(1))

                return int(value_str)

            elif target_type == 'REAL':
                if isinstance(value, (int, float)):
                    return float(value)
                return float(str(value).strip())
            elif target_type == 'TEXT':
                value_str = str(value).strip()

                # 特殊处理 additional_info 字段
                if target_field == 'additional_info':
                    clean_match = re.match(r'^(\d+)', value_str)
                    if clean_match:
                        return clean_match.group(1)

                # 特殊处理 ISBN 及 douban_isbn 字段
                if target_field in ['isbn', 'douban_isbn']:
                    value_str = str(value).strip()
                    if value_str.endswith('.0'):
                        value_str = value_str[:-2]
                    value_str = value_str.replace('-', '').replace(' ', '')
                    return value_str if value_str else None

                return value_str if value_str else None
            else:
                return value
        except (ValueError, TypeError):
            return None

    def get_table_schema(self, table_name):
        """获取表结构"""
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        schema = {col[1]: col[2] for col in columns}
        return schema

    def get_existing_record(self, barcode):
        """根据barcode获取现有记录"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT barcode, data_version, created_at, updated_at
            FROM books
            WHERE barcode = ?
        """, (barcode,))
        return cursor.fetchone()

    def increment_version(self, current_version):
        """
        递增版本号
        1.0 -> 1.1 -> 1.2 -> ... -> 1.9 -> 2.0 -> 2.1 -> ...
        """
        try:
            if current_version is None:
                return "1.0"
            
            # 解析版本号
            parts = current_version.split('.')
            if len(parts) != 2:
                return "1.0"
            
            major = int(parts[0])
            minor = int(parts[1])
            
            # 递增小版本号
            minor += 1
            
            # 如果小版本号达到10，则递增大版本号并重置小版本号
            if minor >= 10:
                major += 1
                minor = 0
            
            return f"{major}.{minor}"
        except (ValueError, AttributeError):
            return "1.0"

    def import_to_books_table(self, df):
        """导入数据到books表（带版本控制）"""
        self.logger.info("\n开始导入books表（带版本控制）...")

        # 从统一字段映射配置获取映射
        mapping = self.column_mapping.get('books', {})
        if not mapping:
            self.logger.error("未找到books字段映射配置")
            return 0

        schema = self.get_table_schema('books')
        
        # 获取当前时间戳
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 准备数据
        self.stats['total_records'] = len(df)
        
        cursor = self.conn.cursor()
        
        # 开始事务
        cursor.execute("BEGIN TRANSACTION")
        
        try:
            for index, row in df.iterrows():
                try:
                    # 检查豆瓣数据来源过滤条件
                    if '豆瓣数据来源' in df.columns:
                        source_value = str(row['豆瓣数据来源']).strip()
                        if source_value.lower() != 'api':
                            self.logger.info(f"第{index+1}行：豆瓣数据来源为'{source_value}'，跳过记录（只导入api来源）")
                            self.stats['skipped_records'] += 1
                            continue
                    else:
                        self.logger.warning(f"第{index+1}行：未找到豆瓣数据来源列，跳过记录")
                        self.stats['skipped_records'] += 1
                        continue
                    
                    # 提取barcode
                    barcode_col = None
                    for excel_col, db_col in mapping.items():
                        if db_col == 'barcode' and excel_col in df.columns:
                            barcode_col = excel_col
                            break
                    
                    if not barcode_col:
                        self.logger.warning(f"第{index+1}行：未找到书目条码列，跳过记录")
                        self.stats['skipped_records'] += 1
                        continue
                    
                    barcode = str(row[barcode_col]).strip()
                    if not barcode or barcode == 'nan':
                        self.logger.warning(f"第{index+1}行：书目条码为空，跳过记录")
                        self.stats['skipped_records'] += 1
                        continue
                    
                    # 检查是否已存在
                    existing_record = self.get_existing_record(barcode)
                    
                    # 准备记录数据
                    book_record = {}
                    
                    # 处理字段映射
                    for excel_col, db_col in mapping.items():
                        if excel_col in df.columns and db_col in schema:
                            value = row[excel_col]
                            if pd.notna(value) and value != '':
                                target_type = schema[db_col]
                                book_record[db_col] = self.convert_value(value, target_type, db_col)
                    
                    # 验证必要字段
                    if not book_record.get('barcode') or not book_record.get('call_no') or not book_record.get('book_title'):
                        self.logger.warning(f"条码 {barcode}：缺少必要字段，跳过记录")
                        self.stats['skipped_records'] += 1
                        continue
                    
                    if existing_record:
                        # 记录已存在，进行更新
                        old_version = existing_record[1]
                        old_created_at = existing_record[2]
                        
                        # 递增版本号
                        new_version = self.increment_version(old_version)
                        
                        # 设置时间戳和版本
                        book_record['data_version'] = new_version
                        book_record['updated_at'] = current_time
                        book_record['created_at'] = old_created_at  # 保持原创建时间
                        
                        # 执行更新
                        placeholders = ', '.join([f"{key} = ?" for key in book_record.keys()])
                        sql = f"""
                            UPDATE books 
                            SET {placeholders}
                            WHERE barcode = ?
                        """
                        values = list(book_record.values()) + [barcode]
                        
                        cursor.execute(sql, values)
                        self.stats['updated_records'] += 1
                        
                        self.logger.info(f"更新记录: 条码={barcode}, 版本={old_version}→{new_version}")
                        
                    else:
                        # 新记录，进行插入
                        book_record['created_at'] = current_time
                        book_record['updated_at'] = current_time
                        book_record['data_version'] = '1.0'  # 初始版本
                        
                        placeholders = ','.join(['?' for _ in book_record])
                        columns = ','.join(book_record.keys())
                        values = list(book_record.values())
                        
                        sql = f"""
                            INSERT INTO books ({columns})
                            VALUES ({placeholders})
                        """
                        
                        cursor.execute(sql, values)
                        self.stats['new_records'] += 1
                        
                        self.logger.info(f"新增记录: 条码={barcode}, 版本=1.0")
                
                except Exception as e:
                    self.logger.error(f"处理第{index+1}行时发生错误: {e}")
                    self.stats['error_records'] += 1
                    continue
            
            # 提交事务
            cursor.execute("COMMIT")
            
        except Exception as e:
            # 回滚事务
            cursor.execute("ROLLBACK")
            self.logger.error(f"导入过程中发生错误，已回滚: {e}")
            raise
        
        self.logger.info(f"\n导入完成统计:")
        self.logger.info(f"  总记录数: {self.stats['total_records']}")
        self.logger.info(f"  新增记录: {self.stats['new_records']}")
        self.logger.info(f"  更新记录: {self.stats['updated_records']}")
        self.logger.info(f"  跳过记录: {self.stats['skipped_records']}")
        self.logger.info(f"  错误记录: {self.stats['error_records']}")
        
        return self.stats['new_records'] + self.stats['updated_records']

    def import_excel(self, excel_path, sheet_name=0):
        """
        导入Excel文件

        Args:
            excel_path: Excel文件路径
            sheet_name: 工作表名称或索引

        Returns:
            int: 成功导入的记录数
        """
        try:
            self.logger.info(f"\n正在读取Excel文件: {excel_path}")
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            self.logger.info(f"成功读取 {len(df)} 行数据")

            # 显示列名
            self.logger.info(f"\nExcel文件包含以下列:")
            for i, col in enumerate(df.columns, 1):
                self.logger.info(f"  {i:2d}. {col}")

            # 导入到books表
            count = self.import_to_books_table(df)
            return count

        except FileNotFoundError:
            self.logger.error(f"Excel文件不存在: {excel_path}")
            return 0
        except Exception as e:
            self.logger.error(f"导入Excel文件时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.logger.info(f"\n数据库连接已关闭")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='导入Excel数据到SQLite数据库（带版本控制）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s data.xlsx                          # 导入Excel文件
  %(prog)s data.xlsx --db-path custom.db     # 指定数据库路径
  %(prog)s data.xlsx --sheet sheet1          # 指定工作表
        """
    )

    parser.add_argument('excel_path', help='Excel文件路径')
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
        '--sheet',
        type=str,
        default=0,
        help='工作表名称或索引（默认: 第一个工作表）'
    )

    args = parser.parse_args()

    # 检查Excel文件是否存在
    if not os.path.exists(args.excel_path):
        print(f"[错误] 文件不存在: {args.excel_path}")
        sys.exit(1)

    # 创建导入器
    importer = ExcelImporterWithVersion(db_path=args.db_path, config_path=args.config)

    try:
        # 连接数据库
        if not importer.connect():
            sys.exit(1)

        # 执行导入
        print("\n" + "="*60)
        print("开始导入Excel数据（带版本控制）...")
        print("="*60)

        count = importer.import_excel(
            args.excel_path,
            sheet_name=args.sheet
        )

        # 显示结果
        print("\n" + "="*60)
        print("导入完成!")
        print("="*60)
        print(f"  成功处理记录数: {count}")
        print("="*60)

    except Exception as e:
        print(f"\n[错误] 导入过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        importer.close()


if __name__ == "__main__":
    main()