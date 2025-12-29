"""
去重器
管理推荐历史，避免重复推荐
"""

import sqlite3
import json
from typing import Dict, List, Set, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ThemeDeduplicator:
    """推荐去重器"""

    def __init__(self, db_path: str = "runtime/database/books_history.db",
                 history_table: str = "literature_recommendation_history"):
        """
        初始化去重器

        Args:
            db_path: 数据库文件路径
            history_table: 推荐历史表名
        """
        self.db_path = db_path
        self.history_table = history_table
        self._ensure_table_exists()

    def _ensure_table_exists(self) -> None:
        """确保历史表存在"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.history_table} (
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
                ON {self.history_table}(user_input)
            """)
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_history_conditions
                ON {self.history_table}(llm_conditions)
            """)

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"创建历史表失败: {str(e)}")

    def get_excluded_book_ids(
        self,
        user_input: str,
        conditions: Dict,
        similarity_threshold: float = 0.8
    ) -> Set[int]:
        """
        获取应排除的已推荐书目ID

        Args:
            user_input: 用户原始输入
            conditions: 检索条件
            similarity_threshold: 相似度阈值

        Returns:
            应排除的书目ID集合
        """
        excluded = set()

        try:
            # 1. 检查相似输入的历史推荐
            similar_history = self._find_similar_inputs(user_input, similarity_threshold)

            # 2. 检查相似条件的历史推荐
            condition_history = self._find_similar_conditions(conditions, similarity_threshold)

            for row in similar_history + condition_history:
                passed_ids = self._parse_book_ids(row['passed_book_ids'])
                excluded.update(passed_ids)

            if excluded:
                logger.info(f"去重: 排除 {len(excluded)} 本已推荐书目")

        except Exception as e:
            logger.error(f"获取排除ID失败: {str(e)}")

        return excluded

    def save_recommendation(
        self,
        user_input: str,
        conditions: Dict,
        book_ids: List[int],
        final_theme: Optional[str] = None,
        vector_weight: float = 0.5,
        randomness: float = 0.2
    ) -> bool:
        """
        保存推荐记录

        Args:
            user_input: 用户原始输入
            conditions: 检索条件
            book_ids: 推荐的书目ID列表
            final_theme: 最终主题名称
            vector_weight: 向量检索权重
            randomness: 随机性因子

        Returns:
            是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(f"""
                INSERT INTO {self.history_table}
                (user_input, llm_conditions, final_theme, book_ids,
                 use_vector, vector_weight, randomness)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_input,
                json.dumps(conditions, ensure_ascii=False),
                final_theme,
                json.dumps(book_ids, ensure_ascii=False),
                1,
                vector_weight,
                randomness
            ))
            conn.commit()
            conn.close()

            logger.info(f"推荐记录已保存: {user_input[:30]}... -> {len(book_ids)} 本")
            return True

        except Exception as e:
            logger.error(f"保存推荐记录失败: {str(e)}")
            return False

    def _find_similar_inputs(
        self,
        user_input: str,
        threshold: float
    ) -> List[Dict]:
        """查找相似输入的历史记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(f"""
                SELECT * FROM {self.history_table}
                WHERE user_input = ?
            """, (user_input,))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows] if rows else []

        except Exception as e:
            logger.error(f"查找相似输入失败: {str(e)}")
            return []

    def _find_similar_conditions(
        self,
        conditions: Dict,
        threshold: float
    ) -> List[Dict]:
        """查找相似条件的历史记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(f"""
                SELECT * FROM {self.history_table}
            """)

            rows = cursor.fetchall()
            conn.close()

            similar = []
            for row in rows:
                try:
                    old_conditions = json.loads(row['llm_conditions'])
                    similarity = self._calculate_condition_similarity(conditions, old_conditions)
                    if similarity >= threshold:
                        similar.append(dict(row))
                except (json.JSONDecodeError, KeyError):
                    continue

            return similar

        except Exception as e:
            logger.error(f"查找相似条件失败: {str(e)}")
            return []

    def _calculate_condition_similarity(self, c1: Dict, c2: Dict) -> float:
        """计算两个条件的相似度"""
        all_keys = set(c1.keys()) | set(c2.keys())
        if not all_keys:
            return 0.0

        matches = 0
        for key in all_keys:
            tags1 = set(c1.get(key, []))
            tags2 = set(c2.get(key, []))
            if tags1 & tags2:
                matches += 1

        return matches / len(all_keys)

    def _parse_book_ids(self, book_ids_json: Optional[str]) -> Set[int]:
        """解析 JSON 格式的书目ID列表"""
        if not book_ids_json:
            return set()

        try:
            return set(json.loads(book_ids_json))
        except (json.JSONDecodeError, TypeError):
            return set()

    def get_history_count(self) -> int:
        """获取历史记录数量"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(f"SELECT COUNT(*) FROM {self.history_table}")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"获取历史记录数失败: {str(e)}")
            return 0
