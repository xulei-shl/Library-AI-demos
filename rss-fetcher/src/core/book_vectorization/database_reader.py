#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SQLite 数据库读取器

负责从 books_history.db 读取图书数据，并管理向量化状态
"""

import sqlite3
from typing import Dict, List, Optional
from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseReader:
    """SQLite 数据库读取器"""
    
    def __init__(self, db_config: Dict):
        """
        初始化数据库读取器
        
        Args:
            db_config: 数据库配置字典，包含 path 和 table
        """
        self.db_path = db_config['path']
        self.table = db_config['table']
        self._conn = None
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        获取或创建数据库连接（复用连接以提升性能）
        
        Returns:
            数据库连接对象
        """
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.debug("数据库连接已关闭")
    
    def load_books(self) -> List[Dict]:
        """
        加载所有书籍数据
        
        Returns:
            书籍列表，每本书为一个字典
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT * FROM {self.table}")
        rows = cursor.fetchall()
        
        books = [dict(row) for row in rows]
        
        logger.info(f"从数据库加载 {len(books)} 本书")
        return books
    
    def get_book_by_id(self, book_id: int) -> Optional[Dict]:
        """
        根据 ID 获取单本书籍信息
        
        Args:
            book_id: 书籍ID
            
        Returns:
            书籍信息字典，如果不存在则返回 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT * FROM {self.table} WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        
        return dict(row) if row else None
    
    def update_embedding_status(
        self, 
        book_id: int, 
        status: str, 
        embedding_id: Optional[str] = None,
        retry_count: Optional[int] = None,
        error: Optional[str] = None,
        clear_error: bool = False
    ):
        """
        更新书籍的向量化状态
        
        Args:
            book_id: 书籍ID
            status: 新状态 (pending/filtered_out/completed/failed/failed_final)
            embedding_id: ChromaDB 文档ID（可选）
            retry_count: 重试次数（可选）
            error: 错误信息（可选）
            clear_error: 是否清除错误信息（成功时使用）
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 构建更新语句
        update_fields = ["embedding_status = ?"]
        params = [status]
        
        if embedding_id:
            update_fields.append("embedding_id = ?")
            params.append(embedding_id)
        
        if retry_count is not None:
            update_fields.append("retry_count = ?")
            params.append(retry_count)
        
        if error:
            update_fields.append("embedding_error = ?")
            params.append(error)
        
        if clear_error:
            update_fields.append("embedding_error = NULL")
            update_fields.append("retry_count = 0")
        
        # 成功时更新完成时间
        if status == 'completed':
            update_fields.append("embedding_date = ?")
            params.append(datetime.now().isoformat())
        
        params.append(book_id)
        
        sql = f"""
            UPDATE {self.table} 
            SET {', '.join(update_fields)}
            WHERE id = ?
        """
        
        cursor.execute(sql, params)
        conn.commit()
        
        logger.debug(f"更新书籍状态: book_id={book_id}, status={status}")
    
    def reset_embedding_status(self):
        """重置所有书籍的向量化状态（用于 rebuild 模式）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            UPDATE {self.table}
            SET 
                embedding_status = 'pending',
                embedding_id = NULL,
                embedding_date = NULL,
                embedding_error = NULL,
                retry_count = 0
        """)
        
        conn.commit()
        
        logger.warning("已重置所有书籍的向量化状态")
    
    def get_books_by_category(self, call_no_prefix: str, limit: int = 10) -> List[Dict]:
        """
        根据索书号首字母查询书籍
        
        Args:
            call_no_prefix: 索书号首字母
            limit: 返回结果数量限制
            
        Returns:
            书籍列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT * FROM {self.table}
            WHERE call_no LIKE ?
            AND embedding_status = 'completed'
            ORDER BY douban_rating DESC
            LIMIT ?
        """, (f"{call_no_prefix}%", limit))
        
        rows = cursor.fetchall()
        books = [dict(row) for row in rows]
        
        return books

    def search_books_by_terms(self, terms: List[str], limit: int = 20, match_fields: List[str] = None) -> List[Dict]:
        """
        根据关键词/书名进行精确匹配检索

        Args:
            terms: 待匹配的关键词列表
            limit: 返回数量上限
            match_fields: 检索字段列表，默认为 ['douban_title', 'douban_author', 'custom_keywords']

        Returns:
            匹配的书籍列表，每条记录包含 exact_match_score 与 match_source
        """
        if not terms:
            return []

        if match_fields is None:
            match_fields = ['douban_title', 'douban_author', 'custom_keywords']

        conn = self._get_connection()
        cursor = conn.cursor()

        # 权重定义
        field_weight = {
            'douban_title': 1.0,
            'douban_author': 0.9,
            'custom_keywords': 0.8,
        }

        # 构造查询条件
        where_clauses = []
        params: List[str] = []
        for term in terms:
            term_lower = term.lower()
            for field in match_fields:
                if field in field_weight:
                    where_clauses.append(f"LOWER({field}) LIKE ?")
                    params.append(f"%{term_lower}%")

        # 只检索已完成向量化的书
        where_clauses.append("embedding_status = 'completed'")
        params.append(limit)

        sql = f"""
            SELECT id, douban_title, douban_author, douban_rating, douban_summary, call_no
            FROM {self.table}
            WHERE ({' OR '.join(where_clauses)})
            ORDER BY douban_rating DESC
            LIMIT ?
        """

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        result: List[Dict] = []

        for row in rows:
            book_dict = dict(row)
            term_lower = [t.lower() for t in terms]

            # 计算最佳匹配源与得分
            best_score = 0.0
            best_source = ""
            for field in match_fields:
                if field not in field_weight:
                    continue
                value = str(book_dict.get(field, ""))
                if not value:
                    continue
                for t in term_lower:
                    if t in value.lower():
                        score = field_weight[field]
                        if score > best_score:
                            best_score = score
                            best_source = field

            if best_score > 0:
                book_dict["exact_match_score"] = best_score
                book_dict["match_source"] = best_source
                result.append(book_dict)

        logger.info(
            "精确匹配检索: terms=%s, 返回=%s条, top_score=%.2f",
            terms,
            len(result),
            max((r.get("exact_match_score", 0) for r in result), default=0),
        )
        return result

    def get_statistics(self) -> Dict:
        """
        获取向量化统计信息
        
        Returns:
            统计信息字典
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # 各状态数量统计
        cursor.execute(f"""
            SELECT embedding_status, COUNT(*) as count
            FROM {self.table}
            GROUP BY embedding_status
        """)
        
        for row in cursor.fetchall():
            status = row[0] or 'pending'
            stats[status] = row[1]
        
        # 总数
        stats['total'] = sum(stats.values())
        
        # 成功率
        completed = stats.get('completed', 0)
        stats['completion_rate'] = f"{completed/stats['total']*100:.2f}%" if stats['total'] > 0 else "0%"
        
        return stats
