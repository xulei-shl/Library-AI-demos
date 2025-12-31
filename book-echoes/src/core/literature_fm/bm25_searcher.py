"""
BM25检索器
基于 rank-bm25 实现字面召回（关键词匹配检索）
"""

import json
import random
import sqlite3
from typing import Dict, List, Optional, Set

import jieba
import numpy as np
from rank_bm25 import BM25Okapi

from src.utils.logger import get_logger

logger = get_logger(__name__)


class BM25Searcher:
    """
    BM25全文检索器

    基于 search_keywords 对书名、作者、简介进行BM25检索
    支持懒加载：首次调用 search() 时构建索引
    """

    def __init__(
        self,
        db_path: str = "runtime/database/books_history.db",
        table: str = "literary_tags",
        k1: float = 1.5,
        b: float = 0.75,
        field_weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化BM25检索器

        Args:
            db_path: 数据库文件路径
            table: 表名
            k1: BM25词频饱和参数 (1.2-2.0)
            b: BM25长度归一化参数 (0.5-0.75)
            field_weights: 字段权重 {"title": 2.0, "author": 1.0, "summary": 1.5}
        """
        self.db_path = db_path
        self.table = table
        self.k1 = k1
        self.b = b
        self.field_weights = field_weights or {"title": 2.0, "author": 1.0, "summary": 1.5}

        # 懒加载相关
        self._index_loaded = False
        self.bm25 = None
        self.corpus = []  # 分词后的文档列表
        self.book_mapping = []  # 索引 -> book_id 映射
        self.book_cache = {}  # book_id -> 书籍信息缓存

    def search(
        self,
        keywords: List[str],
        top_k: int = 50,
        excluded_ids: Optional[Set[int]] = None
    ) -> List[Dict]:
        """
        BM25检索

        Args:
            keywords: 关键词列表
            top_k: 返回结果数量
            excluded_ids: 排除的book_id集合

        Returns:
            [
                {
                    "book_id": 123,
                    "title": "...",
                    "author": "...",
                    "call_no": "...",
                    "tags_json": "...",
                    "bm25_score": 3.45,
                    "source": "bm25"
                }
            ]
        """
        try:
            # 懒加载索引
            if not self._index_loaded:
                self._load_index()

            if not self.bm25:
                logger.warning("BM25索引未构建，返回空结果")
                return []

            # 分词查询
            query_text = " ".join(keywords)
            query_tokens = list(jieba.cut(query_text))

            if not query_tokens:
                logger.warning("查询分词为空，返回空结果")
                return []

            logger.debug(f"BM25查询分词: {query_tokens[:10]}...")

            # BM25打分
            scores = self.bm25.get_scores(query_tokens)

            # 排序并返回TopK
            top_indices = np.argsort(scores)[::-1]

            results = []
            for idx in top_indices:
                book_id = self.book_mapping[idx]
                score = scores[idx]

                # 过滤掉零分和排除项
                if score <= 0:
                    break
                if excluded_ids and book_id in excluded_ids:
                    continue

                # 获取书籍信息
                book_info = self._get_book_info(book_id)
                if not book_info:
                    continue

                results.append({
                    "book_id": book_id,
                    "title": book_info.get("title", ""),
                    "author": book_info.get("author", ""),
                    "call_no": book_info.get("call_no", ""),
                    "tags_json": book_info.get("tags_json", ""),
                    "bm25_score": round(float(score), 4),
                    "source": "bm25"
                })

                if len(results) >= top_k:
                    break

            logger.info(f"BM25检索完成: 关键词={keywords}, 结果数={len(results)}")
            return results

    def search_with_randomness(
        self,
        keywords: List[str],
        top_k: int = 50,
        excluded_ids: Optional[Set[int]] = None,
        randomness: float = 0.2,
        score_threshold: Optional[float] = None
    ) -> List[Dict]:
        """
        带随机性的BM25检索

        策略：
        1. 先执行标准检索，获取高分结果
        2. 降低分数阈值，扩展候选池
        3. 从扩展候选中随机抽取部分结果
        4. 合并并去重

        Args:
            keywords: 关键词列表
            top_k: 返回结果数量
            excluded_ids: 排除的book_id集合
            randomness: 随机性因子 (0-1)，例如 0.2 表示 20% 结果来自随机采样
            score_threshold: 随机采样的分数阈值，None 表示自动推断

        Returns:
            检索结果列表
        """
        try:
            # 懒加载索引
            if not self._index_loaded:
                self._load_index()

            if not self.bm25:
                logger.warning("BM25索引未构建，返回空结果")
                return []

            if randomness <= 0:
                # 无随机性，使用标准检索
                return self.search(keywords, top_k, excluded_ids)

            # 分词查询
            query_text = " ".join(keywords)
            query_tokens = list(jieba.cut(query_text))

            if not query_tokens:
                logger.warning("查询分词为空，返回空结果")
                return []

            # 1. 计算所有文档的分数
            scores = self.bm25.get_scores(query_tokens)

            # 2. 自动推断分数阈值（取 top_k * 3 的分数作为基准）
            if score_threshold is None:
                threshold_idx = min(top_k * 3, len(scores) - 1)
                sorted_indices = np.argsort(scores)[::-1]
                score_threshold = max(0.1, scores[sorted_indices[threshold_idx]] * 0.5)

            # 3. 筛选高分候选
            high_score_indices = np.where(scores >= score_threshold)[0]
            logger.debug(f"高分候选数: {len(high_score_indices)}, 阈值: {score_threshold:.4f}")

            # 4. 按分数排序
            sorted_candidates = sorted(
                high_score_indices,
                key=lambda idx: scores[idx],
                reverse=True
            )

            # 5. 分离主结果和随机候选池
            main_count = int(top_k * (1 - randomness))
            random_count = top_k - main_count

            main_results = []
            random_pool = []

            for idx in sorted_candidates:
                book_id = self.book_mapping[idx]
                score = scores[idx]

                if excluded_ids and book_id in excluded_ids:
                    continue

                book_info = self._get_book_info(book_id)
                if not book_info:
                    continue

                result = {
                    "book_id": book_id,
                    "title": book_info.get("title", ""),
                    "author": book_info.get("author", ""),
                    "call_no": book_info.get("call_no", ""),
                    "tags_json": book_info.get("tags_json", ""),
                    "bm25_score": round(float(score), 4),
                    "source": "bm25_random" if score < score_threshold * 1.5 else "bm25"
                }

                if len(main_results) < main_count and score >= score_threshold * 1.5:
                    main_results.append(result)
                else:
                    random_pool.append(result)

            # 6. 从候选池随机采样
            if random_count > 0 and len(random_pool) > 0:
                sample_size = min(random_count, len(random_pool))
                random_sample = random.sample(random_pool, sample_size)
                main_results.extend(random_sample)

            # 7. 按分数排序最终结果
            main_results.sort(key=lambda x: x["bm25_score"], reverse=True)
            final_results = main_results[:top_k]

            # 统计
            random_count_actual = sum(1 for r in final_results if r["source"] == "bm25_random")

            logger.info(
                f"BM25随机检索完成: 关键词={keywords}, "
                f"总数={len(final_results)}, 随机={random_count_actual}, "
                f"阈值={score_threshold:.4f}"
            )

            return final_results

        except Exception as e:
            logger.error(f"BM25随机检索失败: {str(e)}")
            # 降级到标准检索
            return self.search(keywords, top_k, excluded_ids)

    def _load_index(self):
        """
        懒加载：从数据库加载书籍数据并构建BM25索引
        """
        try:
            logger.info("开始构建BM25索引...")

            # 从数据库加载书籍数据
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(f"""
                SELECT id, book_id, call_no, title, tags_json
                FROM {self.table}
                WHERE llm_status = 'success'
            """)

            books = [dict(row) for row in cursor.fetchall()]
            conn.close()

            logger.info(f"从数据库加载 {len(books)} 本书籍")

            # 构建索引
            self.corpus = []
            self.book_mapping = []

            for book in books:
                book_id = book.get("book_id") or book.get("id")

                # 缓存书籍信息
                self.book_cache[book_id] = {
                    "title": book.get("title", ""),
                    "author": self._extract_author_from_tags(book.get("tags_json", "")),
                    "call_no": book.get("call_no", ""),
                    "tags_json": book.get("tags_json", "")
                }

                # 构建文档文本（加权）
                doc_text = self._build_doc_text(book)
                doc_tokens = list(jieba.cut(doc_text))

                self.corpus.append(doc_tokens)
                self.book_mapping.append(book_id)

            # 构建BM25索引
            self.bm25 = BM25Okapi(self.corpus, k1=self.k1, b=self.b)
            self._index_loaded = True

            logger.info(f"✓ BM25索引构建完成: {len(self.corpus)} 篇文档")

        except Exception as e:
            logger.error(f"BM25索引构建失败: {str(e)}")
            raise

    def _build_doc_text(self, book: Dict) -> str:
        """
        构建文档文本（按字段权重重复）

        Args:
            book: 书籍信息字典

        Returns:
            str: 加权后的文档文本
        """
        parts = []

        try:
            # 解析 tags_json
            tags_json = book.get("tags_json", "{}")
            tags = json.loads(tags_json) if tags_json else {}
        except json.JSONDecodeError:
            tags = {}

        # 书名（高权重）
        title = tags.get("douban_title", book.get("title", ""))
        if title:
            repeat = int(self.field_weights.get("title", 2.0))
            parts.extend([title] * repeat)

        # 作者（中权重）
        author = tags.get("douban_author", "")
        if author:
            repeat = int(self.field_weights.get("author", 1.0))
            parts.extend([author] * repeat)

        # 简介（中高权重）
        summary = tags.get("douban_summary", "")
        if summary:
            repeat = int(self.field_weights.get("summary", 1.5))
            parts.extend([summary] * repeat)

        # LLM推理（最高权重，如果有）
        reasoning = tags.get("reasoning", "")
        if reasoning:
            parts.extend([reasoning] * 2)

        return " ".join(parts)

    def _extract_author_from_tags(self, tags_json: str) -> str:
        """从 tags_json 中提取作者"""
        try:
            tags = json.loads(tags_json) if tags_json else {}
            return tags.get("douban_author", "")
        except json.JSONDecodeError:
            return ""

    def _get_book_info(self, book_id: int) -> Optional[Dict]:
        """获取书籍信息（从缓存）"""
        return self.book_cache.get(book_id)

    def reload_index(self):
        """
        重新加载索引（用于数据更新后）

        Note: 这会清空现有索引并重新构建
        """
        logger.info("重新加载BM25索引...")
        self._index_loaded = False
        self.bm25 = None
        self.corpus = []
        self.book_mapping = []
        self.book_cache = {}
        self._load_index()

    def get_index_stats(self) -> Dict:
        """获取索引统计信息"""
        return {
            "index_loaded": self._index_loaded,
            "total_docs": len(self.corpus),
            "total_books": len(self.book_mapping),
            "cached_books": len(self.book_cache)
        }
