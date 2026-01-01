#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：将borrow_statistics表从3个月迁移到4个月统计

迁移内容：
1. 重命名字段：borrow_count_3m -> borrow_count_4m
2. 重命名字段：unique_reader_count_3m -> unique_reader_count_4m
3. 新增字段：borrow_count_m4 (第四个月借阅次数，初始为0)

注意：此脚本会修改数据库结构，请先备份！
"""

import sqlite3
import os
import shutil
from pathlib import Path
from datetime import datetime


def get_db_path():
    """获取数据库文件路径"""
    # 默认路径
    default_db_path = "runtime/database/books_history.db"

    # 检查是否存在
    if os.path.exists(default_db_path):
        return default_db_path

    # 尝试从配置文件读取
    try:
        import yaml
        with open("config/setting.yaml", 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            db_path = config.get('douban', {}).get('database', {}).get('db_path')
            if db_path and os.path.exists(db_path):
                return db_path
    except Exception as e:
        print(f"[警告] 读取配置文件失败: {e}")

    return default_db_path


def backup_database(db_path):
    """备份数据库文件"""
    if not os.path.exists(db_path):
        print(f"[跳过] 数据库文件不存在: {db_path}")
        return None

    # 创建备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"

    try:
        shutil.copy2(db_path, backup_path)
        print(f"[成功] 数据库备份完成: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"[错误] 数据库备份失败: {e}")
        raise


def check_table_exists(conn, table_name):
    """检查表是否存在"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None


def check_column_exists(conn, table_name, column_name):
    """检查列是否存在"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def migrate_borrow_statistics(db_path):
    """
    迁移borrow_statistics表结构

    策略：SQLite不支持直接重命名列，需要重建表
    """
    print(f"\n{'='*60}")
    print("开始迁移borrow_statistics表")
    print(f"{'='*60}\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. 检查表是否存在
        if not check_table_exists(conn, 'borrow_statistics'):
            print("[跳过] borrow_statistics表不存在，无需迁移")
            return True

        # 2. 检查是否已经迁移过
        if check_column_exists(conn, 'borrow_statistics', 'borrow_count_4m'):
            print("[跳过] borrow_statistics表已经是新结构，无需迁移")
            return True

        # 3. 检查是否有旧字段
        has_old_structure = check_column_exists(conn, 'borrow_statistics', 'borrow_count_3m')
        if not has_old_structure:
            print("[警告] borrow_statistics表不是旧结构，无法迁移")
            return False

        print("[步骤1/7] 开始迁移...")

        # 4. 创建新表
        print("[步骤2/7] 创建新表结构...")
        cursor.execute("""
            CREATE TABLE borrow_statistics_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT NOT NULL,

                stat_period TEXT NOT NULL,
                stat_year INTEGER NOT NULL,
                stat_month INTEGER NOT NULL,
                period_start TEXT,
                period_end TEXT,

                borrow_count_4m INTEGER,
                borrow_count_m1 INTEGER,
                borrow_count_m2 INTEGER,
                borrow_count_m3 INTEGER,
                borrow_count_m4 INTEGER DEFAULT 0,
                unique_reader_count_4m INTEGER,

                created_at TEXT NOT NULL,
                updated_at TEXT,

                FOREIGN KEY (barcode) REFERENCES books(barcode) ON DELETE CASCADE,
                UNIQUE(barcode, stat_year, stat_month)
            );
        """)

        # 5. 迁移数据（重命名字段 + 新增borrow_count_m4=0）
        print("[步骤3/7] 迁移数据...")
        cursor.execute("""
            INSERT INTO borrow_statistics_new (
                id, barcode, stat_period, stat_year, stat_month, period_start, period_end,
                borrow_count_4m, borrow_count_m1, borrow_count_m2, borrow_count_m3,
                borrow_count_m4, unique_reader_count_4m,
                created_at, updated_at
            )
            SELECT
                id, barcode, stat_period, stat_year, stat_month, period_start, period_end,
                borrow_count_3m, borrow_count_m1, borrow_count_m2, borrow_count_m3,
                0, unique_reader_count_3m,
                created_at, updated_at
            FROM borrow_statistics
        """)

        migrated_count = cursor.rowcount
        print(f"[信息] 已迁移 {migrated_count} 条记录")

        # 6. 删除旧表
        print("[步骤4/7] 删除旧表...")
        cursor.execute("DROP TABLE borrow_statistics;")

        # 7. 重命名新表
        print("[步骤5/7] 重命名新表...")
        cursor.execute("ALTER TABLE borrow_statistics_new RENAME TO borrow_statistics;")

        # 8. 重建索引
        print("[步骤6/7] 重建索引...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_borrow_statistics_barcode ON borrow_statistics(barcode)",
            "CREATE INDEX IF NOT EXISTS idx_borrow_statistics_period ON borrow_statistics(stat_year, stat_month)",
            "CREATE INDEX IF NOT EXISTS idx_borrow_statistics_barcode_period ON borrow_statistics(barcode, stat_year, stat_month)"
        ]
        for index_sql in indexes:
            cursor.execute(index_sql)

        # 提交事务
        conn.commit()
        print("[步骤7/7] 迁移完成！")

        # 验证迁移结果
        cursor.execute("SELECT COUNT(*) FROM borrow_statistics")
        total_count = cursor.fetchone()[0]
        print(f"\n[验证] 当前表中记录数: {total_count}")

        cursor.execute("SELECT COUNT(*) FROM borrow_statistics WHERE borrow_count_m4 > 0")
        non_zero_m4 = cursor.fetchone()[0]
        print(f"[验证] borrow_count_m4 > 0 的记录数: {non_zero_m4} (应为0)")

        return True

    except Exception as e:
        conn.rollback()
        print(f"\n[错误] 迁移失败: {e}")
        print(f"[信息] 数据库已回滚到迁移前状态")
        return False

    finally:
        conn.close()


def verify_migration(db_path):
    """验证迁移结果"""
    print(f"\n{'='*60}")
    print("验证迁移结果")
    print(f"{'='*60}\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 检查新字段存在
        cursor.execute("PRAGMA table_info(borrow_statistics)")
        columns = [row[1] for row in cursor.fetchall()]

        required_columns = ['borrow_count_4m', 'borrow_count_m1', 'borrow_count_m2',
                          'borrow_count_m3', 'borrow_count_m4', 'unique_reader_count_4m']

        print("[验证] 检查字段:")
        all_exist = True
        for col in required_columns:
            exists = col in columns
            status = "✓" if exists else "✗"
            print(f"  {status} {col}")
            if not exists:
                all_exist = False

        if not all_exist:
            print("\n[失败] 部分字段缺失")
            return False

        # 检查旧字段不存在
        old_columns = ['borrow_count_3m', 'unique_reader_count_3m']
        print("\n[验证] 检查旧字段已删除:")
        all_removed = True
        for col in old_columns:
            exists = col in columns
            status = "✗" if exists else "✓"
            print(f"  {status} {col} (应不存在)")
            if exists:
                all_removed = False

        if not all_removed:
            print("\n[警告] 旧字段仍然存在")
            return False

        # 统计记录数
        cursor.execute("SELECT COUNT(*) FROM borrow_statistics")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM borrow_statistics WHERE borrow_count_4m IS NOT NULL")
        with_count = cursor.fetchone()[0]

        print(f"\n[统计] 总记录数: {total}")
        print(f"[统计] 有统计数据的记录: {with_count}")

        print("\n[成功] 迁移验证通过！")
        return True

    except Exception as e:
        print(f"\n[错误] 验证失败: {e}")
        return False

    finally:
        conn.close()


def main():
    """主函数"""
    print("=" * 60)
    print("borrow_statistics表迁移工具")
    print("从3个月统计 -> 4个月统计")
    print("=" * 60)

    # 获取数据库路径
    db_path = get_db_path()

    if not os.path.exists(db_path):
        print(f"\n[错误] 数据库文件不存在: {db_path}")
        print("\n请确认：")
        print("1. 数据库文件路径是否正确")
        print("2. 是否已运行过init_database.py初始化数据库")
        return 1

    print(f"\n[信息] 数据库路径: {db_path}")

    # 确认迁移
    print("\n[警告] 此操作将修改数据库结构！")
    response = input("是否继续？(yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("\n[取消] 用户取消操作")
        return 0

    # 备份数据库
    print("\n" + "=" * 60)
    print("步骤1: 备份数据库")
    print("=" * 60)
    backup_path = backup_database(db_path)

    if not backup_path:
        print("\n[错误] 备份失败，终止迁移")
        return 1

    # 执行迁移
    print("\n" + "=" * 60)
    print("步骤2: 迁移数据")
    print("=" * 60)

    success = migrate_borrow_statistics(db_path)

    if not success:
        print("\n[失败] 迁移失败")
        print(f"[提示] 可以从备份恢复: {backup_path}")
        return 1

    # 验证迁移
    print("\n" + "=" * 60)
    print("步骤3: 验证结果")
    print("=" * 60)

    verify_success = verify_migration(db_path)

    if not verify_success:
        print("\n[警告] 验证未通过，请手动检查")
        return 1

    # 完成
    print("\n" + "=" * 60)
    print("[成功] 迁移完成！")
    print("=" * 60)
    print(f"\n备份文件: {backup_path}")
    print(f"数据库文件: {db_path}")
    print("\n后续步骤：")
    print("1. 重新运行模块1生成新的统计数据")
    print("2. borrow_count_m4字段将自动填充")
    print("\n如需回滚，可以使用备份文件：")
    print(f"  cp {backup_path} {db_path}")

    return 0


if __name__ == "__main__":
    exit(main())
