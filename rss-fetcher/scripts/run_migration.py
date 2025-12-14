#!/usr/bin/env python3
"""
图书向量化数据库迁移脚本
用途: 使用Python执行数据库迁移，为books表添加向量化状态追踪字段
"""

import sqlite3
import sys
import os
from pathlib import Path

def main():
    # 数据库路径
    db_path = "F:\\Github\\Library-AI-demos\\book-echoes\\runtime\\database\\books_history.db"
    script_path = "scripts/migrate_add_embedding_fields.sql"
    
    # 检查数据库文件是否存在
    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在: {db_path}")
        sys.exit(1)
    
    # 检查迁移脚本是否存在
    if not os.path.exists(script_path):
        print(f"错误: 迁移脚本不存在: {script_path}")
        sys.exit(1)
    
    try:
        # 连接到数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"连接到数据库: {db_path}")
        print(f"SQLite版本: {sqlite3.sqlite_version}")
        
        # 读取并执行迁移脚本
        with open(script_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        print(f"执行迁移脚本: {script_path}")
        
        # 分割SQL语句并执行
        sql_statements = []
        current_statement = ""
        
        for line in sql_script.split('\n'):
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith('--'):
                continue
            current_statement += line + " "
            
            # 当遇到分号时，认为一个语句结束
            if line.endswith(';'):
                if current_statement.strip():
                    sql_statements.append(current_statement.strip())
                current_statement = ""
        
        # 执行每个SQL语句
        for i, statement in enumerate(sql_statements, 1):
            try:
                print(f"执行语句 {i}/{len(sql_statements)}: {statement[:50]}...")
                cursor.execute(statement)
            except sqlite3.Error as e:
                print(f"警告: 语句执行失败 - {e}")
                print(f"失败语句: {statement}")
                # 继续执行其他语句
        
        # 提交事务
        conn.commit()
        print("✓ 迁移执行完成，事务已提交")
        
        # 验证新字段是否添加成功
        print("\n验证新添加的字段:")
        cursor.execute("""
            SELECT name, type, dflt_value
            FROM pragma_table_info('books')
            WHERE name LIKE 'embedding%' OR name = 'retry_count'
            ORDER BY name
        """)
        
        fields = cursor.fetchall()
        if fields:
            print("新字段列表:")
            for field_name, field_type, default_value in fields:
                default_str = f" (默认: {default_value})" if default_value else ""
                print(f"  - {field_name}: {field_type}{default_str}")
        else:
            print("未找到预期的新字段")
        
        # 显示当前表结构摘要
        print(f"\n当前books表字段总数:")
        cursor.execute("SELECT COUNT(*) FROM pragma_table_info('books')")
        total_fields = cursor.fetchone()[0]
        print(f"  总字段数: {total_fields}")
        
        # 显示索引信息
        print(f"\n新创建的索引:")
        cursor.execute("""
            SELECT name 
            FROM sqlite_master 
            WHERE type='index' 
            AND name LIKE '%embedding%' OR name LIKE '%retry%'
        """)
        
        indexes = cursor.fetchall()
        if indexes:
            for index_name, in indexes:
                print(f"  - {index_name}")
        else:
            print("  未找到相关索引")
        
    except Exception as e:
        print(f"迁移过程中发生错误: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()
            print(f"\n数据库连接已关闭")

if __name__ == "__main__":
    main()
