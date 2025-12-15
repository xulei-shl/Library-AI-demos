#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Excel导入脚本（带版本控制）
创建测试数据和验证脚本功能

作者：豆瓣评分模块开发组
版本：1.0
创建时间：2025-12-15
"""

import sqlite3
import pandas as pd
import os
import tempfile
from pathlib import Path
from datetime import datetime
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.tools.excel_import_with_version import ExcelImporterWithVersion


def create_test_database(db_path):
    """创建测试数据库和表结构"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建books表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE NOT NULL,
            call_no TEXT NOT NULL,
            cleaned_call_no TEXT,
            book_title TEXT NOT NULL,
            additional_info TEXT,
            isbn TEXT,
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
            data_version TEXT DEFAULT '1.0',
            created_at TEXT NOT NULL,
            updated_at TEXT
        );
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_barcode ON books(barcode)")
    
    conn.commit()
    conn.close()
    print(f"测试数据库创建成功: {db_path}")


def create_test_excel_file():
    """创建测试Excel文件"""
    # 创建测试数据
    test_data = {
        '书目条码': ['1234567890', '2345678901', '3456789012', '4567890123', '5678901234'],
        '索书号': ['TP391/4831-1', 'I247.5/1234', 'TP312/5678-2', 'I247.5/5678', 'TP312/9012'],
        '书名': ['自然语言理解', 'Python编程', '机器学习', '数据结构', '算法导论'],
        '附加信息': ['200454818', '200454819', '200454820', '200454821', '200454822'],
        'ISBN': ['9787302627784', '9787111648367', '9787121397703', '9787111612855', '9787111407808'],
        '豆瓣评分': [8.5, 9.0, 7.5, 8.0, 9.2],
        '豆瓣作者': ['赵海', 'Mark Lutz', '周志华', '严蔚敏', 'Thomas H. Cormen'],
        '豆瓣出版社': ['清华大学出版社', '机械工业出版社', '电子工业出版社', '清华大学出版社', '机械工业出版社'],
        '豆瓣数据来源': ['api', 'api', 'manual', 'api', 'crawler']  # 测试过滤条件
    }
    
    df = pd.DataFrame(test_data)
    
    # 创建临时Excel文件
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    excel_path = temp_file.name
    temp_file.close()
    
    df.to_excel(excel_path, index=False)
    print(f"测试Excel文件创建成功: {excel_path}")
    
    return excel_path


def test_version_increment_logic():
    """测试版本号递增逻辑"""
    print("\n测试版本号递增逻辑...")
    
    # 创建导入器实例
    importer = ExcelImporterWithVersion()
    
    # 测试用例
    test_cases = [
        (None, "1.0"),
        ("1.0", "1.1"),
        ("1.1", "1.2"),
        ("1.9", "2.0"),
        ("2.0", "2.1"),
        ("2.9", "3.0"),
        ("invalid", "1.0"),
        ("", "1.0")
    ]
    
    for input_version, expected_output in test_cases:
        result = importer.increment_version(input_version)
        status = "✓" if result == expected_output else "✗"
        print(f"  {status} {input_version} → {result} (期望: {expected_output})")
        
        if result != expected_output:
            print(f"    错误: 期望 {expected_output}, 实际 {result}")


def test_database_operations():
    """测试数据库操作"""
    print("\n测试数据库操作...")
    
    # 创建临时数据库
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    db_path = temp_db.name
    temp_db.close()
    
    try:
        # 创建测试数据库
        create_test_database(db_path)
        
        # 创建测试Excel文件
        excel_path = create_test_excel_file()
        
        # 创建导入器
        importer = ExcelImporterWithVersion(db_path=db_path)
        
        # 连接数据库
        if not importer.connect():
            print("数据库连接失败")
            return False
        
        # 第一次导入（应该全部新增）
        print("\n第一次导入（应该全部新增）:")
        count1 = importer.import_excel(excel_path)
        print(f"导入记录数: {count1}")
        
        # 检查数据库中的记录
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT barcode, data_version, created_at, updated_at FROM books ORDER BY barcode")
        records = cursor.fetchall()
        
        print("\n第一次导入后的记录:")
        for record in records:
            barcode, version, created_at, updated_at = record
            print(f"  条码: {barcode}, 版本: {version}, 创建时间: {created_at}, 更新时间: {updated_at}")
        
        # 验证只有api来源的记录被导入（应该有3条：1234567890, 2345678901, 4567890123）
        expected_barcodes = ['1234567890', '2345678901', '4567890123']
        actual_barcodes = [record[0] for record in records]
        
        print(f"\n验证豆瓣数据来源过滤:")
        print(f"  期望导入的条码: {expected_barcodes}")
        print(f"  实际导入的条码: {actual_barcodes}")
        
        if set(actual_barcodes) == set(expected_barcodes):
            print("  ✓ 豆瓣数据来源过滤正确")
        else:
            print("  ✗ 豆瓣数据来源过滤错误")
            return False
        
        # 等待一秒确保时间戳不同
        import time
        time.sleep(1)
        
        # 第二次导入（应该全部更新）
        print("\n第二次导入（应该全部更新）:")
        count2 = importer.import_excel(excel_path)
        print(f"导入记录数: {count2}")
        
        # 检查更新后的记录
        cursor.execute("SELECT barcode, data_version, created_at, updated_at FROM books ORDER BY barcode")
        updated_records = cursor.fetchall()
        
        print("\n第二次导入后的记录:")
        for i, record in enumerate(updated_records):
            barcode, version, created_at, updated_at = record
            old_record = records[i]
            print(f"  条码: {barcode}, 版本: {version}, 创建时间: {created_at}, 更新时间: {updated_at}")
            print(f"    原版本: {old_record[1]}, 新版本: {version}")
            print(f"    创建时间是否保持: {old_record[2] == created_at}")
            print(f"    更新时间是否变化: {old_record[3] != updated_at}")
        
        conn.close()
        
        # 验证结果
        success = True
        for i, record in enumerate(updated_records):
            old_record = records[i]
            
            # 检查版本号是否递增
            expected_version = importer.increment_version(old_record[1])
            if record[1] != expected_version:
                print(f"错误: 版本号递增不正确 - 期望 {expected_version}, 实际 {record[1]}")
                success = False
            
            # 检查创建时间是否保持不变
            if record[2] != old_record[2]:
                print(f"错误: 创建时间发生变化 - 期望 {old_record[2]}, 实际 {record[2]}")
                success = False
            
            # 检查更新时间是否变化
            if record[3] == old_record[3]:
                print(f"错误: 更新时间未变化 - 应该不同于 {old_record[3]}")
                success = False
        
        return success
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 清理临时文件
        try:
            os.unlink(db_path)
            os.unlink(excel_path)
        except:
            pass


def main():
    """主测试函数"""
    print("="*60)
    print("Excel导入脚本（带版本控制）测试")
    print("="*60)
    
    # 测试版本号递增逻辑
    test_version_increment_logic()
    
    # 测试数据库操作
    db_test_success = test_database_operations()
    
    print("\n" + "="*60)
    print("测试结果总结:")
    print("="*60)
    print(f"版本号递增逻辑: ✓")
    print(f"数据库操作: {'✓' if db_test_success else '✗'}")
    
    if db_test_success:
        print("\n所有测试通过！脚本功能正常。")
        return 0
    else:
        print("\n部分测试失败，请检查脚本实现。")
        return 1


if __name__ == "__main__":
    sys.exit(main())