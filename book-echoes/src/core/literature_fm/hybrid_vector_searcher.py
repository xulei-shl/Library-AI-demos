"""
增强向量检索器
扩展现有 VectorSearcher，支持 filter_conditions 的过滤逻辑

设计模式：装饰器模式，包装 VectorSearcher
"""

from typing import Dict, List, Optional

from src.utils.logger import get_logger
from .vector_searcher import VectorSearcher

logger = get_logger(__name__)


class HybridVectorSearcher:
    """
    增强向量检索器

    扩展 VectorSearcher，支持 filter_conditions 的过滤逻辑：
    - MUST: Pre-filter（使用 ChromaDB 的 where 参数）
    - MUST_NOT: Post-filter（直接排除）
    - SHOULD: 多次检索合并（每个值检索一次，然后合并去重）
    """

    def __init__(self, base_searcher: VectorSearcher):
        """
        初始化增强向量检索器

        Args:
            base_searcher: 基础向量检索器实例
        """
        self.base_searcher = base_searcher

    def search(
        self,
        query_text: str,
        filter_conditions: Optional[List[Dict]] = None,
        top_k: int = 50,
        min_confidence: float = 0.65,
        excluded_ids: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        增强向量检索

        Args:
            query_text: 合成查询词 (synthetic_query)
            filter_conditions: [
                {"field": "reading_context", "values": ["A", "B"], "operator": "SHOULD"},
                {"field": "reading_load", "values": ["C"], "operator": "MUST"},
                {"field": "spatial_atmosphere", "values": ["D"], "operator": "MUST_NOT"}
            ]
            top_k: 返回数量
            min_confidence: 最小置信度
            excluded_ids: 排除的book_id列表

        Returns:
            检索结果列表
        """
        try:
            if not filter_conditions:
                # 无过滤条件，直接使用基础检索器
                return self.base_searcher.search(
                    query_text=query_text,
                    top_k=top_k,
                    min_confidence=min_confidence
                )

            # 解析过滤条件
            must_conditions = [c for c in filter_conditions if c["operator"] == "MUST"]
            should_conditions = [c for c in filter_conditions if c["operator"] == "SHOULD"]
            must_not_conditions = [c for c in filter_conditions if c["operator"] == "MUST_NOT"]

            # 检查是否有SHOULD条件
            has_should = len(should_conditions) > 0

            # 如果有SHOULD条件，使用多次检索合并策略
            if has_should:
                return self._search_with_should(
                    query_text=query_text,
                    must_conditions=must_conditions,
                    should_conditions=should_conditions,
                    must_not_conditions=must_not_conditions,
                    top_k=top_k,
                    min_confidence=min_confidence,
                    excluded_ids=excluded_ids
                )
            else:
                # 只有MUST和MUST_NOT，使用单次检索
                return self._search_without_should(
                    query_text=query_text,
                    must_conditions=must_conditions,
                    must_not_conditions=must_not_conditions,
                    top_k=top_k,
                    min_confidence=min_confidence,
                    excluded_ids=excluded_ids
                )

        except Exception as e:
            logger.error(f"增强向量检索失败: {str(e)}")
            # 降级到基础检索
            return self.base_searcher.search(
                query_text=query_text,
                top_k=top_k,
                min_confidence=min_confidence * 0.8  # 降低阈值
            )

    def _search_without_should(
        self,
        query_text: str,
        must_conditions: List[Dict],
        must_not_conditions: List[Dict],
        top_k: int,
        min_confidence: float,
        excluded_ids: Optional[List[int]]
    ) -> List[Dict]:
        """
        无SHOULD条件的检索（MUST + MUST_NOT）

        Args:
            query_text: 查询文本
            must_conditions: MUST条件列表
            must_not_conditions: MUST_NOT条件列表
            top_k: 返回数量
            min_confidence: 最小置信度
            excluded_ids: 排除的book_id列表

        Returns:
            检索结果列表
        """
        # 构建MUST过滤器（ChromaDB where语法）
        pre_filter = self._build_must_filter(must_conditions) if must_conditions else None

        # 获取查询向量
        query_vector = self.base_searcher.embedding_client.get_embedding(query_text)

        # 向量检索（带Pre-filter）
        results = self.base_searcher.vector_store.search(
            query_embedding=query_vector,
            top_k=top_k * 2,  # 多取一些，因为Post-filter会过滤掉一部分
            filter_metadata=pre_filter
        )

        # 应用MUST_NOT过滤器（Post-filter）
        if must_not_conditions:
            results = self._apply_must_not_filter(results, must_not_conditions)

        # 补充书籍信息并过滤
        enriched = self._enrich_and_filter_results(
            results,
            query_text,
            top_k,
            min_confidence,
            excluded_ids
        )

        return enriched

    def _search_with_should(
        self,
        query_text: str,
        must_conditions: List[Dict],
        should_conditions: List[Dict],
        must_not_conditions: List[Dict],
        top_k: int,
        min_confidence: float,
        excluded_ids: Optional[List[int]]
    ) -> List[Dict]:
        """
        带SHOULD条件的检索（多次检索合并策略）

        Args:
            query_text: 查询文本
            must_conditions: MUST条件列表
            should_conditions: SHOULD条件列表
            must_not_conditions: MUST_NOT条件列表
            top_k: 返回数量
            min_confidence: 最小置信度
            excluded_ids: 排除的book_id列表

        Returns:
            检索结果列表
        """
        all_results = {}

        # 构建SHOULD查询列表（笛卡尔积展开）
        should_queries = self._expand_should_conditions(should_conditions)

        logger.info(f"SHOULD条件展开为 {len(should_queries)} 个查询")

        # 在循环外部获取一次 embedding，避免重复调用 API
        query_vector = self.base_searcher.embedding_client.get_embedding(query_text)

        # 对每个SHOULD查询组合执行检索
        for idx, should_filter in enumerate(should_queries):
            # 合并MUST和SHOULD过滤器
            combined_filter = self._merge_filters(must_conditions, should_filter)

            # 检索（复用 query_vector）
            results = self.base_searcher.vector_store.search(
                query_embedding=query_vector,
                top_k=top_k,
                filter_metadata=combined_filter
            )

            # 应用MUST_NOT过滤器
            if must_not_conditions:
                results = self._apply_must_not_filter(results, must_not_conditions)

            # 合并结果（保留最高分）
            for result in results:
                book_id = result["metadata"].get("id")
                if not book_id:
                    continue

                distance = result["distance"]
                similarity = 1 - distance

                if book_id not in all_results or similarity > all_results[book_id]["similarity"]:
                    all_results[book_id] = {
                        "metadata": result["metadata"],
                        "distance": distance,
                        "similarity": similarity
                    }

        logger.info(f"SHOULD多路检索合并: {len(all_results)} 个唯一书籍")

        # 转换为列表并排序
        sorted_results = sorted(
            all_results.values(),
            key=lambda x: x["similarity"],
            reverse=True
        )

        # 补充书籍信息并过滤
        enriched = self._enrich_and_filter_results(
            [{"metadata": r["metadata"], "distance": r["distance"]} for r in sorted_results],
            query_text,
            top_k,
            min_confidence,
            excluded_ids
        )

        return enriched

    def _build_must_filter(self, must_conditions: List[Dict]) -> Optional[Dict]:
        """
        构建MUST过滤器（ChromaDB where语法）

        Note: ChromaDB的where只支持AND逻辑，不支持OR
              因此MUST条件使用精确匹配（单值或AND）
        """
        if not must_conditions:
            return None

        filters = {}
        for cond in must_conditions:
            field = cond["field"]
            values = cond["values"]

            # MUST使用精确匹配（取第一个值，因为ChromaDB不支持OR）
            if values:
                filters[field] = values[0]

        return filters if filters else None

    def _apply_must_not_filter(self, results: List[Dict], must_not_conditions: List[Dict]) -> List[Dict]:
        """
        应用MUST_NOT过滤器（Post-filter）

        排除匹配任一MUST_NOT条件的结果
        """
        if not must_not_conditions:
            return results

        filtered = []
        for result in results:
            metadata = result.get("metadata", {})
            exclude = False

            for cond in must_not_conditions:
                field = cond["field"]
                values = cond["values"]

                # 获取metadata中的字段值（逗号分隔）
                field_value = metadata.get(field, "")
                field_values = field_value.split(",") if field_value else []

                # 如果有任一匹配，则排除
                if set(field_values) & set(values):
                    exclude = True
                    break

            if not exclude:
                filtered.append(result)

        logger.debug(f"MUST_NOT过滤: {len(results)} -> {len(filtered)}")
        return filtered

    def _expand_should_conditions(self, should_conditions: List[Dict]) -> List[Dict]:
        """
        展开SHOULD条件为多个查询（笛卡尔积）

        例如：
        [
            {"field": "reading_context", "values": ["A", "B"]},
            {"field": "reading_load", "values": ["C"]}
        ]
        展开为：
        [
            {"reading_context": "A"},
            {"reading_context": "B"},
            {"reading_context": "A", "reading_load": "C"},
            {"reading_context": "B", "reading_load": "C"}
        ]

        Note: 为了避免组合爆炸，我们采用简化策略：
              1. 每个SHOULD条件单独展开
              2. 合并所有展开结果
        """
        queries = []

        for cond in should_conditions:
            field = cond["field"]
            values = cond["values"]

            for value in values:
                queries.append({field: value})

        # 如果有多个SHOULD条件，生成组合查询（可选）
        # 为了避免组合爆炸，我们暂时只使用单一维度查询
        # 如果需要组合查询，可以取消下面的注释
        # if len(should_conditions) > 1:
        #     import itertools
        #     for combination in itertools.product(*[c["values"] for c in should_conditions]):
        #         query = {c["field"]: combination[idx] for idx, c in enumerate(should_conditions)}
        #         queries.append(query)

        return queries

    def _merge_filters(self, must_conditions: List[Dict], should_filter: Dict) -> Dict:
        """合并MUST和SHOULD过滤器"""
        merged = {}

        # 添加MUST条件
        if must_conditions:
            must_filter = self._build_must_filter(must_conditions)
            if must_filter:
                merged.update(must_filter)

        # 添加SHOULD条件
        merged.update(should_filter)

        return merged if merged else None

    def _enrich_and_filter_results(
        self,
        results: List[Dict],
        query_text: str,
        top_k: int,
        min_confidence: float,
        excluded_ids: Optional[List[int]]
    ) -> List[Dict]:
        """
        补充书籍信息并过滤结果
        """
        enriched = []
        candidates = []

        for result in results:
            metadata = result.get("metadata", {})
            book_id = metadata.get("id")

            if not book_id:
                continue

            # 排除指定书籍
            if excluded_ids and book_id in excluded_ids:
                continue

            similarity = 1 - result.get("distance", 1.0)
            candidates.append((book_id, similarity, result))

        # 动态阈值：借鉴基础 VectorSearcher，避免高阈值导致结果为零
        if candidates:
            similarities = [item[1] for item in candidates]
            actual_threshold = self._calculate_dynamic_threshold(
                candidates,
                similarities,
                min_confidence
            )
        else:
            actual_threshold = min_confidence

        for book_id, similarity, result in candidates:
            # 置信度过滤
            if similarity < actual_threshold:
                continue

            # 获取书籍完整信息
            book_info = self.base_searcher.db_reader.get_book_by_id(book_id)
            if not book_info:
                continue

            enriched.append({
                "book_id": book_id,
                "title": book_info.get("title", ""),
                "author": book_info.get("author", ""),
                "call_no": book_info.get("call_no", ""),
                "tags_json": book_info.get("tags_json", ""),
                "vector_score": round(similarity, 4),
                "embedding_id": result.get("embedding_id", ""),
                "source": "vector"
            })

            if len(enriched) >= top_k:
                break

        return enriched

    def _calculate_dynamic_threshold(
        self,
        candidates: List[tuple],
        similarities: List[float],
        min_confidence: float
    ) -> float:
        """
        计算动态阈值，保证在结果稀疏场景下也能返回一定数量的书籍
        """
        pairs = list(zip(candidates, similarities))
        pairs.sort(key=lambda x: x[1], reverse=True)
        top_pairs = pairs[:5]

        avg_similarity = sum(score for _, score in top_pairs) / len(top_pairs)
        dynamic_threshold = max(avg_similarity * 0.85, min_confidence * 0.7)

        top_log = [
            (f"book_{candidate[0]}", f"{score:.4f}")
            for candidate, score in top_pairs
        ]
        logger.info(
            f"动态阈值: {dynamic_threshold:.4f} (Top{len(top_pairs)}平均: {avg_similarity:.4f}, 固定阈值: {min_confidence}), "
            f"Top样本: {top_log}"
        )

        return dynamic_threshold
