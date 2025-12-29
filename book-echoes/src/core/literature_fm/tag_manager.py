"""
标签状态管理器
管理 literary_tags 表的 CRUD 操作
"""

import sqlite3
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
import pandas as pd

from src.utils.logger import get_logger
from .db_init import init_literary_tags_table

logger = get_logger(__name__)


class TagManager:
    """管理 literary_tags 表的 CRUD 操作"""
    
    def __init__(self, db_path: str = "runtime/database/books_history.db"):
        """
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._ensure_table_exists()
    
    def _ensure_table_exists(self) -> None:
        """确保 literary_tags 表存在"""
        init_literary_tags_table(self.db_path)
    
    def get_tagged_book_ids(self, status: str = 'success') -> List[int]:
        """
        获取已打标的 book_id 列表
        
        Args:
            status: 状态过滤（success/failed/pending）
            
        Returns:
            List[int]: book_id 列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT book_id FROM literary_tags WHERE llm_status = ?",
                (status,)
            )
            
            book_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return book_ids
            
        except Exception as e:
            logger.error(f"获取已打标 book_id 失败: {str(e)}")
            return []
    
    def save_tags(
        self,
        book_id: int,
        call_no: str,
        title: str,
        tags_json: str,
        llm_model: str,
        llm_provider: str,
        llm_status: str = 'success',
        error_message: Optional[str] = None
    ) -> bool:
        """
        保存标签数据（INSERT OR REPLACE）
        
        Args:
            book_id: 书目ID
            call_no: 索书号
            title: 书名
            tags_json: 标签JSON字符串
            llm_model: 模型名称
            llm_provider: API提供商
            llm_status: 状态
            error_message: 错误信息
            
        Returns:
            bool: 是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO literary_tags (
                    book_id, call_no, title, tags_json,
                    llm_model, llm_provider, llm_status,
                    error_message, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                book_id, call_no, title, tags_json,
                llm_model, llm_provider, llm_status,
                error_message, datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"保存标签失败 (book_id={book_id}): {str(e)}")
            return False
    
    def update_status(
        self,
        book_id: int,
        llm_status: str,
        error_message: Optional[str] = None,
        increment_retry: bool = False
    ) -> bool:
        """
        更新打标状态
        
        Args:
            book_id: 书目ID
            llm_status: 新状态
            error_message: 错误信息
            increment_retry: 是否增加重试计数
            
        Returns:
            bool: 是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if increment_retry:
                cursor.execute("""
                    UPDATE literary_tags
                    SET llm_status = ?,
                        error_message = ?,
                        retry_count = retry_count + 1,
                        updated_at = ?
                    WHERE book_id = ?
                """, (llm_status, error_message, datetime.now(), book_id))
            else:
                cursor.execute("""
                    UPDATE literary_tags
                    SET llm_status = ?,
                        error_message = ?,
                        updated_at = ?
                    WHERE book_id = ?
                """, (llm_status, error_message, datetime.now(), book_id))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"更新状态失败 (book_id={book_id}): {str(e)}")
            return False
    
    def get_failed_records(self, max_retry_count: int = 3) -> List[Dict]:
        """
        获取失败记录（用于兜底重试）
        
        Args:
            max_retry_count: 最大重试次数过滤
            
        Returns:
            List[Dict]: 失败记录列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT b.id, b.book_title, b.douban_author, b.call_no,
                       b.douban_summary, b.douban_rating, b.douban_pub_year
                FROM books b
                INNER JOIN literary_tags lt ON b.id = lt.book_id
                WHERE lt.llm_status = 'failed'
                  AND lt.retry_count < ?
            """, (max_retry_count,))
            
            records = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return records
            
        except Exception as e:
            logger.error(f"获取失败记录失败: {str(e)}")
            return []
    
    def export_to_dataframe(self) -> pd.DataFrame:
        """
        导出标签数据为 DataFrame
        
        Returns:
            pd.DataFrame: 标签数据
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = """
                SELECT 
                    lt.book_id,
                    lt.call_no,
                    lt.title,
                    lt.tags_json,
                    lt.llm_model,
                    lt.llm_provider,
                    lt.llm_status,
                    lt.retry_count,
                    lt.error_message,
                    lt.created_at,
                    lt.updated_at
                FROM literary_tags lt
                WHERE lt.llm_status = 'success'
                ORDER BY lt.created_at DESC
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            return df
            
        except Exception as e:
            logger.error(f"导出 DataFrame 失败: {str(e)}")
            return pd.DataFrame()