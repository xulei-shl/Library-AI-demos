"""
标签检索器
基于 SQLite 标签匹配检索（带随机性策略）
"""

import random
import sqlite3
from typing import Dict, List, Optional
from dataclasses import dataclass

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TagSearchResult:
    """标签检索结果"""
    book_id: int
    title: str
    author: str
    call_no: str
    tags_json: str
    tag_score: float
    confidence: float
    source: str = 'tag'


class TagSearcher:
    """标签检索器（带随机性策略）"""

    def __init__(self, db_path: str = "runtime/database/books_history.db", table: str = "literary_tags"):
        """
        初始化标签检索器

        Args:
            db_path: 数据库文件路径
            table: 表名
        """
        self.db_path = db_path
        self.table = table

    def search(
        self,
        conditions: Dict[str, List[str]],
        min_confidence: float = 0.65,
        limit: int = 50,
        randomness: float = 0.2
    ) -> List[TagSearchResult]:
        """
        带随机性的标签检索

        Args:
            conditions: 检索条件（各维度的标签列表）
            min_confidence: 最小置信度
            limit: 返回结果数量
            randomness: 随机性因子（0-1）

        Returns:
            检索结果列表
        """
        try:
            # 1. 高置信度基础查询
            base_results = self._query_by_conditions(
                conditions,
                min_confidence=min_confidence,
                limit=limit
            )

            # 2. 随机性扩展查询
            if randomness > 0:
                expanded_results = self._query_by_conditions(
                    conditions,
                    min_confidence=min_confidence * (1 - randomness),
                    limit=limit
                )

                # 随机选取部分扩展结果
                expand_count = int(limit * randomness)
                if len(expanded_results) > expand_count:
                    random.shuffle(expanded_results)
                    expanded_results = expanded_results[:expand_count]

                # 合并结果
                base_results.extend(expanded_results)

            # 3. 按分数排序并去重
            seen_ids = set()
            unique_results = []
            for r in base_results:
                if r.book_id not in seen_ids:
                    seen_ids.add(r.book_id)
                    unique_results.append(r)

            unique_results.sort(key=lambda x: x.tag_score, reverse=True)
            final_results = unique_results[:limit]

            logger.info(f"标签检索完成: 条件={conditions}, 结果数={len(final_results)}")
            return final_results

        except Exception as e:
            logger.error(f"标签检索失败: {str(e)}")
            return []

    def _query_by_conditions(
        self,
        conditions: Dict[str, List[str]],
        min_confidence: float,
        limit: int
    ) -> List[TagSearchResult]:
        """根据条件查询数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # 构建查询
        where_clauses = []
        params = []

        for dimension, tags in conditions.items():
            if tags:
                # 构建该维度的 OR 条件：(tags_json LIKE ? AND tags_json LIKE ?) OR (tags_json LIKE ? AND tags_json LIKE ?)
                dimension_clauses = []
                for tag in tags:
                    dimension_clauses.append(
                        f"(tags_json LIKE ? AND tags_json LIKE ?)"
                    )
                    # 匹配维度名和标签值
                    params.append(f'%"{dimension}"%')
                    params.append(f'%"{tag}"%')
                # 该维度内的所有标签用 OR 连接
                if dimension_clauses:
                    where_clauses.append(f"({' OR '.join(dimension_clauses)})")

        if not where_clauses:
            conn.close()
            return []

        # 不同维度之间用 AND 连接
        where_sql = ' AND '.join(where_clauses)

        query = f"""
        SELECT id, book_id, call_no, title, tags_json
        FROM {self.table}
        WHERE llm_status = 'success' AND {where_sql}
        ORDER BY id DESC
        LIMIT ?
        """

        cursor = conn.execute(query, params + [limit])
        results = []

        for row in cursor.fetchall():
            # 计算置信度分数
            tags_json = row['tags_json'] or '{}'
            confidence = self._calculate_confidence(tags_json, conditions)

            if confidence >= min_confidence:
                results.append(TagSearchResult(
                    book_id=row['book_id'] or row['id'],
                    title=row['title'] or '',
                    author='',
                    call_no=row['call_no'] or '',
                    tags_json=tags_json,
                    tag_score=confidence,
                    confidence=confidence,
                    source='tag'
                ))

        conn.close()
        return results

    def _calculate_confidence(self, tags_json: str, conditions: Dict) -> float:
        """计算匹配置信度"""
        try:
            import json
            tags = json.loads(tags_json)
        except (json.JSONDecodeError, TypeError):
            return 0.0

        matches = 0
        total = 0

        for dimension, dim_tags in conditions.items():
            if dim_tags:
                total += len(dim_tags)
                book_tags = tags.get(dimension, [])
                if isinstance(book_tags, list):
                    for tag in dim_tags:
                        if tag in book_tags:
                            matches += 1

        return matches / total if total > 0 else 0.0

    def get_all_tagged_books(self, limit: int = 1000) -> List[Dict]:
        """获取所有已打标的书籍（用于构建向量索引）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(f"""
            SELECT id as book_id, call_no, title, tags_json
            FROM {self.table}
            WHERE llm_status = 'success' AND embedding_status != 'completed'
            LIMIT ?
        """, (limit,))

        books = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return books
