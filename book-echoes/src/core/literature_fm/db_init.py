"""
数据库表初始化脚本
创建 literary_tags 表和 literature_recommendation_history 表
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger(__name__)


def init_literary_tags_table(db_path: str = "runtime/database/books_history.db") -> bool:
    """
    初始化 literary_tags 表
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        bool: 是否成功
    """
    try:
        # 确保数据库目录存在
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建 literary_tags 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS literary_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                call_no TEXT,
                title TEXT,
                
                -- 标签数据（JSON格式）
                tags_json TEXT,
                
                -- LLM调用元数据
                llm_model TEXT,
                llm_provider TEXT,
                llm_status TEXT DEFAULT 'pending',
                retry_count INTEGER DEFAULT 0,
                error_message TEXT,
                
                -- 时间戳
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- 唯一约束
                UNIQUE(book_id)
            )
        """)

        # 添加向量化状态字段（如果不存在）
        cursor.execute("""
            SELECT COUNT(*) FROM pragma_table_info('literary_tags')
            WHERE name='embedding_status'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                ALTER TABLE literary_tags
                ADD COLUMN embedding_status TEXT DEFAULT 'pending'
            """)
            cursor.execute("""
                ALTER TABLE literary_tags
                ADD COLUMN embedding_id TEXT
            """)
            cursor.execute("""
                ALTER TABLE literary_tags
                ADD COLUMN embedding_date TEXT
            """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_literary_tags_book_id 
            ON literary_tags(book_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_literary_tags_status 
            ON literary_tags(llm_status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_literary_tags_call_no 
            ON literary_tags(call_no)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info(f"✓ literary_tags 表初始化成功: {db_path}")
        return True

    except Exception as e:
        logger.error(f"✗ literary_tags 表初始化失败: {str(e)}")
        return False


def init_recommendation_history_table(db_path: str = "runtime/database/books_history.db") -> bool:
    """
    初始化 literature_recommendation_history 表

    Args:
        db_path: 数据库文件路径

    Returns:
        bool: 是否成功
    """
    try:
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 创建推荐历史表
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS literature_recommendation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_input TEXT NOT NULL,
                llm_conditions TEXT NOT NULL,
                final_theme TEXT,
                book_ids TEXT NOT NULL,
                passed_book_ids TEXT,
                use_vector INTEGER DEFAULT 0,
                vector_weight REAL DEFAULT 0.5,
                randomness REAL DEFAULT 0.2,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建索引
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_history_input
            ON literature_recommendation_history(user_input)
        """)
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_history_conditions
            ON literature_recommendation_history(llm_conditions)
        """)

        conn.commit()
        conn.close()

        logger.info(f"✓ literature_recommendation_history 表初始化成功: {db_path}")
        return True

    except Exception as e:
        logger.error(f"✗ literature_recommendation_history 表初始化失败: {str(e)}")
        return False


if __name__ == "__main__":
    # 直接运行此脚本可初始化表
    init_literary_tags_table()
