#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
迁移 recommendation_results 表,添加 UNIQUE 约束

此脚本会:
1. 备份现有数据
2. 删除旧表
3. 创建新表(带 UNIQUE 约束)
4. 恢复数据
"""

import sqlite3
import os
from datetime import datetime

db_path = "runtime/database/books_history.db"

def migrate_recommendation_results():
    """迁移 recommendation_results 表"""
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("=" * 80)
        print("开始迁移 recommendation_results 表...")
        print("=" * 80)
        
        # 1. 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='recommendation_results'")
        if not cursor.fetchone():
            print("recommendation_results 表不存在,无需迁移")
            conn.close()
            return True
        
        # 2. 备份现有数据
        print("\n步骤1: 备份现有数据...")
        cursor.execute("SELECT * FROM recommendation_results")
        existing_data = cursor.fetchall()
        print(f"  - 找到 {len(existing_data)} 条记录")
        
        # 3. 删除旧表
        print("\n步骤2: 删除旧表...")
        cursor.execute("DROP TABLE IF EXISTS recommendation_results")
        print("  - 旧表已删除")
        
        # 4. 创建新表(带 UNIQUE 约束)
        print("\n步骤3: 创建新表(带 UNIQUE 约束)...")
        create_table_sql = """
        CREATE TABLE recommendation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL,

            -- ============ 评选批次信息 ============
            evaluation_batch TEXT,
            evaluation_date TEXT,

            -- ============ 初评信息 ============
            preliminary_result TEXT,
            preliminary_score REAL,
            preliminary_reason TEXT,
            preliminary_elimination_reason TEXT,
            preliminary_elimination_note TEXT,

            -- ============ 主题内决选信息 ============
            theme_final_result TEXT,
            theme_final_reason TEXT,

            -- ============ 终评信息 ============
            final_result TEXT,
            final_score REAL,
            final_reason TEXT,
            final_elimination_reason TEXT,
            final_elimination_note TEXT,

            -- ============ 人工评选信息 ============
            manual_selection TEXT,
            manual_recommendation TEXT,

            -- ============ 元数据 ============
            created_at TEXT NOT NULL,
            updated_at TEXT,

            -- 外键
            FOREIGN KEY (barcode) REFERENCES books(barcode) ON DELETE CASCADE,
            
            -- 确保同一本书在同一评选批次只有一条记录
            UNIQUE(barcode, evaluation_batch)
        );
        """
        cursor.execute(create_table_sql)
        print("  - 新表已创建")
        
        # 5. 创建索引
        print("\n步骤4: 创建索引...")
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
        print(f"  - 已创建 {len(indexes)} 个索引")
        
        # 6. 恢复数据
        if existing_data:
            print(f"\n步骤5: 恢复数据 ({len(existing_data)} 条记录)...")
            
            # 获取列名(排除 id)
            columns = [desc[0] for desc in cursor.description if desc[0] != 'id']
            
            restored_count = 0
            skipped_count = 0
            
            for row in existing_data:
                try:
                    # 准备数据(排除 id)
                    row_dict = dict(row)
                    if 'id' in row_dict:
                        del row_dict['id']
                    
                    # 插入数据
                    placeholders = ','.join(['?' for _ in row_dict])
                    column_names = ','.join(row_dict.keys())
                    
                    insert_sql = f"INSERT INTO recommendation_results ({column_names}) VALUES ({placeholders})"
                    cursor.execute(insert_sql, list(row_dict.values()))
                    restored_count += 1
                    
                except sqlite3.IntegrityError as e:
                    # 违反 UNIQUE 约束,跳过重复记录
                    skipped_count += 1
                    print(f"  - 跳过重复记录: barcode={row['barcode']}, batch={row.get('evaluation_batch', 'N/A')}")
                except Exception as e:
                    print(f"  - 恢复记录失败: {e}")
                    skipped_count += 1
            
            print(f"  - 成功恢复: {restored_count} 条")
            if skipped_count > 0:
                print(f"  - 跳过重复: {skipped_count} 条")
        else:
            print("\n步骤5: 无数据需要恢复")
        
        # 7. 提交事务
        conn.commit()
        
        print("\n" + "=" * 80)
        print("迁移完成!")
        print("=" * 80)
        
        # 8. 验证新表结构
        print("\n验证新表结构:")
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='recommendation_results'")
        result = cursor.fetchone()
        if result and 'UNIQUE(barcode, evaluation_batch)' in result[0]:
            print("  ✓ UNIQUE 约束已添加")
        else:
            print("  ✗ UNIQUE 约束未找到")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n错误: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("recommendation_results 表迁移工具")
    print("=" * 80)
    print(f"\n数据库路径: {os.path.abspath(db_path)}")
    print("\n此操作将:")
    print("  1. 备份现有数据")
    print("  2. 删除旧表")
    print("  3. 创建新表(添加 UNIQUE 约束)")
    print("  4. 恢复数据")
    print("\n警告: 此操作会修改数据库结构!")
    
    response = input("\n是否继续? (y/N): ")
    if response.lower() == 'y':
        success = migrate_recommendation_results()
        if success:
            print("\n迁移成功完成!")
        else:
            print("\n迁移失败!")
    else:
        print("\n已取消操作")
