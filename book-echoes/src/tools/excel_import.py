#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Excel数据导入脚本
将Excel文件中的数据导入到SQLite数据库中

作者：豆瓣评分模块开发组
版本：1.0
创建时间：2025-11-05
"""

import sqlite3
import pandas as pd
import argparse
import sys
from datetime import datetime
from pathlib import Path
import yaml
import os
import calendar
import re


class ExcelImporter:
    """Excel数据导入器"""

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

        # 从配置文件加载字段映射
        self.column_mapping = self._load_field_mapping()

    def _load_field_mapping(self):
        """
        从配置文件加载字段映射

        Returns:
            dict: 字段映射字典（Excel列名 → 数据库字段名）
        """
        config = self.load_config()

        # 从统一字段映射配置加载
        fields_mapping = config.get('fields_mapping', {})
        excel_to_db_mapping = fields_mapping.get('excel_to_database', {})

        if excel_to_db_mapping:
            print("[信息] 使用统一字段映射配置 (fields_mapping)")
            return excel_to_db_mapping
        else:
            print("[错误] 未找到统一字段映射配置")
            return {}

    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            print(f"[警告] 配置文件不存在: {self.config_path}")
            return {}
        except yaml.YAMLError as e:
            print(f"[错误] 解析配置文件失败: {e}")
            return {}
        except Exception as e:
            print(f"[错误] 读取配置文件时发生错误: {e}")
            return {}

    def get_db_path_from_config(self):
        """从配置文件中获取数据库路径"""
        config = self.load_config()

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
            print(f"[成功] 连接到数据库: {self.db_path}")
            return True
        except Exception as e:
            print(f"[错误] 数据库连接失败: {e}")
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
                # 例如：2023-7 -> 2023, 2024-5 -> 2024, 2020-5-15 -> 2020
                # 使用正则表达式提取年份部分
                year_match = re.match(r'(\d{4})', value_str)
                if year_match:
                    return int(year_match.group(1))

                # 特殊处理豆瓣评价人数字段 - 从 "XX人评价" 中提取数字
                # 例如：107人评价 -> 107, 154人评价 -> 154
                # 匹配数字部分
                count_match = re.search(r'(\d+)', value_str)
                if count_match:
                    return int(count_match.group(1))

                # 如果以上都不匹配，尝试直接转换为整数
                return int(value_str)

            elif target_type == 'REAL':
                if isinstance(value, (int, float)):
                    return float(value)
                return float(str(value).strip())
            elif target_type == 'TEXT':
                value_str = str(value).strip()

                # 特殊处理 additional_info 字段 - 去除 [.*] 格式的附件信息
                if target_field == 'additional_info':
                    # 例如：200620395[附件:0(0);] -> 200620395
                    clean_match = re.match(r'^(\d+)', value_str)
                    if clean_match:
                        return clean_match.group(1)

                # 特殊处理 ISBN 及 douban_isbn 字段 - 去除 .0 后缀、连字符和空格
                if target_field in ['isbn', 'douban_isbn']:
                    # 如果是数值类型（如 float/int），先转为字符串
                    value_str = str(value).strip()
                    # 去除尾部的“.0”
                    if value_str.endswith('.0'):
                        value_str = value_str[:-2]
                    # 移除连字符和空格
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
        schema = {col[1]: col[2] for col in columns}  # {column_name: data_type}
        return schema

    def import_to_books_table(self, df):
        """导入数据到books表"""
        print("\n[信息] 开始导入books表...")

        # 从统一字段映射配置获取映射
        mapping = self.column_mapping.get('books', {})
        if not mapping:
            print("[错误] 未找到books字段映射配置")
            return 0

        schema = self.get_table_schema('books')

        # 准备数据
        books_data = []
        for _, row in df.iterrows():
            book_record = {}
            book_record['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            book_record['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            book_record['data_version'] = '1.0'

            for excel_col, db_col in mapping.items():
                if excel_col in df.columns and db_col in schema:
                    value = row[excel_col]
                    if pd.notna(value) and value != '':
                        target_type = schema[db_col]
                        book_record[db_col] = self.convert_value(value, target_type, db_col)

            # 验证必要字段
            if book_record.get('barcode') and book_record.get('call_no') and book_record.get('book_title'):
                books_data.append(book_record)

        if not books_data:
            print("[警告] 没有有效的books数据可导入")
            return 0

        # 插入数据（使用REPLACE处理重复）
        cursor = self.conn.cursor()
        count = 0
        for record in books_data:
            placeholders = ','.join(['?' for _ in record])
            columns = ','.join(record.keys())
            values = list(record.values())

            sql = f"""
                INSERT OR REPLACE INTO books ({columns})
                VALUES ({placeholders})
            """
            try:
                cursor.execute(sql, values)
                count += 1
            except Exception as e:
                print(f"[错误] 插入books记录失败: {e}")
                print(f"  条码: {record.get('barcode')}")

        self.conn.commit()
        print(f"[成功] 成功导入 {count} 条books记录")
        return count

    def import_to_borrow_records_table(self, df):
        """导入数据到borrow_records表"""
        print("\n[信息] 开始导入borrow_records表...")

        # 从统一字段映射配置获取映射
        mapping = self.column_mapping.get('borrow_records', {})
        if not mapping:
            print("[错误] 未找到borrow_records字段映射配置")
            return 0

        schema = self.get_table_schema('borrow_records')

        records_data = []
        for _, row in df.iterrows():
            record = {}
            record['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            for excel_col, db_col in mapping.items():
                if excel_col in df.columns and db_col in schema:
                    value = row[excel_col]
                    if pd.notna(value) and value != '':
                        target_type = schema[db_col]
                        record[db_col] = self.convert_value(value, target_type, db_col)

            # 验证必要字段
            if record.get('barcode') and record.get('reader_card_no'):
                records_data.append(record)

        if not records_data:
            print("[警告] 没有有效的borrow_records数据可导入")
            return 0

        # 插入数据
        cursor = self.conn.cursor()
        count = 0
        for record in records_data:
            placeholders = ','.join(['?' for _ in record])
            columns = ','.join(record.keys())
            values = list(record.values())

            sql = f"""
                INSERT INTO borrow_records ({columns})
                VALUES ({placeholders})
            """
            try:
                cursor.execute(sql, values)
                count += 1
            except Exception as e:
                print(f"[错误] 插入borrow_records记录失败: {e}")
                print(f"  条码: {record.get('barcode')}, 读者卡号: {record.get('reader_card_no')}")

        self.conn.commit()
        print(f"[成功] 成功导入 {count} 条borrow_records记录")
        return count

    def import_to_borrow_statistics_table(self, df):
        """导入数据到borrow_statistics表"""
        print("\n[信息] 开始导入borrow_statistics表...")

        # 从统一字段映射配置获取映射
        mapping = self.column_mapping.get('borrow_statistics', {})
        if not mapping:
            print("[错误] 未找到borrow_statistics字段映射配置")
            return 0

        schema = self.get_table_schema('borrow_statistics')

        # 获取统计周期（从配置文件读取target_month）
        config = self.load_config()
        target_month = config.get('statistics', {}).get('target_month')
        if target_month:
            # 从配置文件中解析目标月份
            try:
                stat_year, stat_month = map(int, target_month.split('-'))
                # 解析目标月份（YYYY-MM格式）
                # 先取该月第一天
                first_day = datetime.strptime(target_month + '-01', '%Y-%m-%d')
                # 计算该月最后一天
                last_day = calendar.monthrange(stat_year, stat_month)[1]
                period_end = first_day.replace(day=last_day)
            except (ValueError, AttributeError) as e:
                print(f"[警告] target_month格式错误，使用当前日期作为统计周期: {e}")
                target_month = None
        else:
            print("[警告] 配置文件中未找到target_month，使用当前日期作为统计周期")

        if not target_month:
            # 如果配置文件中没有或格式错误，使用当前日期
            current_date = datetime.now()
            stat_year = current_date.year
            stat_month = current_date.month
            # 当月最后一天
            last_day = calendar.monthrange(stat_year, stat_month)[1]
            period_end = current_date.replace(day=last_day)

        # 计算周期范围（最近三个月）
        from dateutil.relativedelta import relativedelta
        if not target_month:
            period_start = (current_date - relativedelta(months=2)).replace(day=1)  # 修正为第一天
        else:
            period_start = (first_day - relativedelta(months=2)).replace(day=1)  # 修正为第一天

        statistics_data = []
        for _, row in df.iterrows():
            stat_record = {}
            stat_record['stat_period'] = f"{stat_year}-{stat_month:02d}"
            stat_record['stat_year'] = stat_year
            stat_record['stat_month'] = stat_month
            stat_record['period_start'] = period_start.strftime('%Y-%m-%d')
            stat_record['period_end'] = period_end.strftime('%Y-%m-%d')
            stat_record['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            stat_record['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            for excel_col, db_col in mapping.items():
                if excel_col in df.columns and db_col in schema:
                    value = row[excel_col]
                    if pd.notna(value) and value != '':
                        target_type = schema[db_col]
                        stat_record[db_col] = self.convert_value(value, target_type, db_col)

            # 验证必要字段
            if stat_record.get('barcode'):
                statistics_data.append(stat_record)

        if not statistics_data:
            print("[警告] 没有有效的borrow_statistics数据可导入")
            return 0

        # 插入数据（使用REPLACE处理重复）
        cursor = self.conn.cursor()
        count = 0
        for record in statistics_data:
            placeholders = ','.join(['?' for _ in record])
            columns = ','.join(record.keys())
            values = list(record.values())

            sql = f"""
                INSERT OR REPLACE INTO borrow_statistics ({columns})
                VALUES ({placeholders})
            """
            try:
                cursor.execute(sql, values)
                count += 1
            except Exception as e:
                print(f"[错误] 插入borrow_statistics记录失败: {e}")
                print(f"  条码: {record.get('barcode')}")

        self.conn.commit()
        print(f"[成功] 成功导入 {count} 条borrow_statistics记录")
        return count

    def import_excel(self, excel_path, sheet_name=0):
        """
        导入Excel文件

        Args:
            excel_path: Excel文件路径
            sheet_name: 工作表名称或索引

        Returns:
            tuple: (books_count, borrow_records_count, borrow_statistics_count)
        """
        try:
            print(f"\n[信息] 正在读取Excel文件: {excel_path}")
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            print(f"[信息] 成功读取 {len(df)} 行数据")

            # 显示列名
            print(f"\n[信息] Excel文件包含以下列:")
            for i, col in enumerate(df.columns, 1):
                print(f"  {i:2d}. {col}")

            # 导入到各个表
            books_count = self.import_to_books_table(df)
            borrow_records_count = self.import_to_borrow_records_table(df)
            borrow_statistics_count = self.import_to_borrow_statistics_table(df)

            return (books_count, borrow_records_count, borrow_statistics_count)

        except FileNotFoundError:
            print(f"[错误] Excel文件不存在: {excel_path}")
            return (0, 0, 0)
        except Exception as e:
            print(f"[错误] 导入Excel文件时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return (0, 0, 0)

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            print(f"\n[信息] 数据库连接已关闭")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='导入Excel数据到SQLite数据库',
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
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='预览模式，只显示要导入的数据统计，不实际插入'
    )

    args = parser.parse_args()

    # 检查Excel文件是否存在
    if not os.path.exists(args.excel_path):
        print(f"[错误] 文件不存在: {args.excel_path}")
        sys.exit(1)

    # 创建导入器
    importer = ExcelImporter(db_path=args.db_path, config_path=args.config)

    try:
        # 连接数据库
        if not importer.connect():
            sys.exit(1)

        # 执行导入
        print("\n" + "="*60)
        print("开始导入Excel数据...")
        print("="*60)

        books_count, borrow_records_count, borrow_statistics_count = importer.import_excel(
            args.excel_path,
            sheet_name=args.sheet
        )

        # 显示结果
        print("\n" + "="*60)
        print("导入完成!")
        print("="*60)
        print(f"  books表: {books_count} 条记录")
        print(f"  borrow_records表: {borrow_records_count} 条记录")
        print(f"  borrow_statistics表: {borrow_statistics_count} 条记录")
        print(f"  总计: {books_count + borrow_records_count + borrow_statistics_count} 条记录")
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
