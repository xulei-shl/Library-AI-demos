#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图书检索接口（预留）

提供基于向量的语义检索功能，供后续推荐模块调用
"""

import yaml
from typing import Dict, List, Optional, Sequence, Tuple
from src.utils.logger import get_logger
from .embedding_client import EmbeddingClient
from .vector_store import VectorStore
from .database_reader import DatabaseReader
from .fusion import FusionConfig, build_fusion_config, fuse_query_results
from .query_assets import QueryPackage
from .reranker import RerankerClient

logger = get_logger(__name__)


class BookRetriever:
    """图书检索接口（预留）"""
    
    def __init__(self, config_path: str):
        """
        初始化检索器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.embedding_client = EmbeddingClient(self.config['embedding'])
        self.vector_store = VectorStore(self.config['vector_db'])
        self.db_reader = DatabaseReader(self.config['database'])
        self.multi_query_options = self.config.get('multi_query', {})
        self.fusion_config = build_fusion_config(self.config.get('fusion'))
        self.reranker = RerankerClient(self.config.get('reranker', {}))
        self.exact_match_config = self.config.get('exact_match', {})
        
        logger.info("图书检索器初始化完成")
    
    def _load_config(self, config_path: str) -> Dict:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config
    
    def search_by_text(
        self, 
        query_text: str, 
        top_k: int = 10, 
        min_rating: Optional[float] = None
    ) -> List[Dict]:
        """
        根据文本查询相似书籍
        
        Args:
            query_text: 查询文本（例如：文章的 thematic_essence）
            top_k: 返回结果数量
            min_rating: 最低评分过滤
        
        Returns:
            书籍列表，包含相似度分数
        """
        logger.info(f"开始文本检索: query_text={query_text[:50]}..., top_k={top_k}")
        
        # 1. 将查询文本向量化
        query_embedding = self.embedding_client.get_embedding(query_text)
        
        # 2. 构建过滤条件
        filter_metadata = {}
        if min_rating:
            filter_metadata['douban_rating'] = {"$gte": min_rating}
        
        # 3. 向量检索
        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_metadata=filter_metadata if filter_metadata else None
        )
        
        # 4. 补充完整书籍信息（从 SQLite）
        enriched_results = []
        for result in results:
            # 使用 'id' 而不是 'book_id'
            book_id = result['metadata']['id']
            book_info = self.db_reader.get_book_by_id(book_id)
            
            if book_info:
                enriched_results.append({
                    'book_id': book_id,
                    'id': book_id,  # 保留原始ID用于去重判断
                    'title': book_info['douban_title'],
                    'author': book_info['douban_author'],
                    'rating': book_info['douban_rating'],
                    'summary': book_info.get('douban_summary', ''),
                    'call_no': book_info.get('call_no', ''),
                    'similarity_score': 1 - result['distance'],  # 转换为相似度
                    'embedding_id': result['embedding_id'],
                    'source_query_text': query_text,
                    'embedding_date': book_info.get('embedding_date', ''),  # 添加时间字段
                })
        
        # 5. 去重处理 - 基于 book_id 和 call_no 去重，保留最新的记录
        deduplicated_results = self._deduplicate_by_book_id(enriched_results)
        
        logger.info(f"文本检索完成: 返回 {len(deduplicated_results)} 本书（去重前: {len(enriched_results)} 本）")
        return deduplicated_results
    
    def search_by_category(self, call_no_prefix: str, top_k: int = 10) -> List[Dict]:
        """
        根据分类查询书籍
        
        Args:
            call_no_prefix: 索书号首字母
            top_k: 返回结果数量
            
        Returns:
            书籍列表
        """
        logger.info(f"开始分类检索: call_no_prefix={call_no_prefix}, top_k={top_k}")
        
        # 直接从数据库查询，不使用向量检索
        books = self.db_reader.get_books_by_category(call_no_prefix, limit=top_k)
        
        logger.info(f"分类检索完成: 返回 {len(books)} 本书")
        return books
    
    def search_multi_query(
        self,
        query_package: QueryPackage,
        min_rating: Optional[float] = None,
        per_query_top_k: Optional[int] = None,
        fusion_config: Optional[FusionConfig] = None,
        query_priority: Optional[Sequence[str]] = None,
        rerank: bool = False,
        final_top_k: Optional[int] = None,
    ) -> List[Dict]:
        """执行多子查询检索并融合结果。"""

        package_dict = query_package.as_dict()
        priorities = list(query_priority or self.multi_query_options.get('priorities') or ['primary', 'tags', 'insight', 'books'])
        max_queries = self.multi_query_options.get('max_queries_per_type', {})
        top_k_each = per_query_top_k or self.multi_query_options.get('top_k_per_query', 20)
        top_k_each = max(top_k_each, 1)
        query_results = []

        for bucket in priorities:
            queries = package_dict.get(bucket, [])
            if not queries:
                continue
            limit = max_queries.get(bucket)
            if isinstance(limit, int) and limit > 0:
                queries = queries[:limit]
            for query_text in queries:
                logger.info(
                    "执行子查询: type=%s, top_k=%s, query=%s",
                    bucket,
                    top_k_each,
                    self._shorten_text(query_text),
                )
                results = self.search_by_text(
                    query_text=query_text,
                    top_k=top_k_each,
                    min_rating=min_rating,
                )
                for item in results:
                    item['source_query_type'] = bucket
                query_results.append((bucket, results))

        if not query_results:
            logger.warning("多子查询未获取任何候选，返回空列表")
            return []

        active_fusion_config = fusion_config or self.fusion_config
        if final_top_k is not None:
            active_fusion_config = FusionConfig(
                weights=active_fusion_config.weights,
                final_top_k=final_top_k,
            )

        fused_results = fuse_query_results(query_results, active_fusion_config)
        # 并行精确匹配（若启用且未显式禁用）
        exact_enabled = self.exact_match_config.get('enabled', False) and not getattr(query_package, 'disable_exact_match', False)
        if exact_enabled:
            exact_results = self._search_exact_matches(query_package, min_rating, self.exact_match_config.get('top_k', 20))
        else:
            exact_results = []

        if rerank:
            if not self.reranker.enabled:
                logger.warning("已请求 rerank 但配置未启用，将跳过该步骤。")
            else:
                anchor_query = self._select_anchor_query(package_dict, priorities)
                fused_results = self._apply_rerank(anchor_query, fused_results)

        # 合并向量与精确匹配结果
        if exact_results:
            from .fusion import merge_exact_matches
            exact_weight = self.exact_match_config.get('final_weight', 1.1)
            final_results = merge_exact_matches(fused_results, exact_results, exact_weight)
        else:
            final_results = fused_results

        return final_results
    
    def close(self):
        """关闭资源"""
        self.db_reader.close()
        logger.info("检索器资源已释放")

    @staticmethod
    def _select_anchor_query(package_dict: Dict[str, List[str]], priorities: Sequence[str]) -> str:
        for bucket in list(priorities) + ['primary', 'tags', 'insight', 'books']:
            values = package_dict.get(bucket, [])
            if values:
                return values[0]
        return ''

    def _apply_rerank(self, anchor_query: str, candidates: List[Dict]) -> List[Dict]:
        if not candidates or not anchor_query:
            return candidates
        documents = [self._compose_candidate_text(item) for item in candidates]
        rerank_results = self.reranker.rerank(anchor_query, documents)
        if not rerank_results:
            return candidates
        score_map = {item.index: item.score for item in rerank_results}
        for idx, candidate in enumerate(candidates):
            rr_score = score_map.get(idx)
            base_score = candidate.get('fused_score', candidate.get('similarity_score', 0.0))
            if rr_score is not None:
                candidate['reranker_score'] = rr_score
                candidate['final_score'] = 0.7 * base_score + 0.3 * rr_score
            else:
                candidate['final_score'] = base_score
        candidates.sort(key=lambda item: item.get('final_score', item.get('fused_score', 0.0)), reverse=True)
        return candidates

    def _search_exact_matches(
        self,
        query_package: QueryPackage,
        min_rating: Optional[float],
        exact_match_top_k: int,
    ) -> List[Dict]:
        """精确匹配分支：从 QueryPackage 提取关键词/书名进行 SQL 精确匹配。"""
        raw_terms: List[Tuple[str, str]] = []
        raw_terms.extend((book, "books") for book in query_package.books)
        raw_terms.extend((tag, "tags") for tag in query_package.tags)

        primary_max_len = self.exact_match_config.get('primary_max_length', 10)
        primary_candidates = [term for term in query_package.primary if term and len(term) <= primary_max_len]
        logger.info(
            "精确匹配关键词准备: books=%s, tags=%s, primary候选(<=%s)=%s",
            len(query_package.books),
            len(query_package.tags),
            primary_max_len,
            len(primary_candidates),
        )
        for short_term in query_package.primary:
            if len(short_term) <= primary_max_len:
                raw_terms.append((short_term, "primary"))

        terms: List[str] = []
        seen = set()
        source_counts = {"books": 0, "tags": 0, "primary": 0}
        for term, source in raw_terms:
            normalized = (term or "").strip()
            if not normalized or normalized.lower() in {"无", "none"}:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            terms.append(normalized)
            if source in source_counts:
                source_counts[source] += 1

        if not terms:
            logger.info("无可用关键词/书名，跳过精确匹配分支")
            return []

        logger.info("正在执行精确匹配，terms=%s，来源统计=%s", terms, source_counts)

        match_fields = self.exact_match_config.get('match_fields', ['douban_title', 'douban_author', 'custom_keywords'])
        title_weight = self.exact_match_config.get('title_weight', 1.0)
        keyword_weight = self.exact_match_config.get('keyword_weight', 0.8)

        # 调用 DatabaseReader
        exact_results = self.db_reader.search_books_by_terms(
            terms=terms,
            limit=exact_match_top_k,
            match_fields=match_fields,
        )

        # 按评分过滤
        if min_rating is not None:
            exact_results = [r for r in exact_results if r.get('douban_rating', 0) >= min_rating]

        logger.info(
            "精确匹配完成: 返回=%s条，命中字段=[%s]",
            len(exact_results),
            ",".join(set(r.get('match_source', '') for r in exact_results)),
        )
        return exact_results

    @staticmethod
    def _compose_candidate_text(candidate: Dict) -> str:
        parts = [candidate.get('title', ''), candidate.get('author', ''), candidate.get('summary', '')]
        return '\n'.join(part for part in parts if part)

    def _deduplicate_by_book_id(self, results: List[Dict]) -> List[Dict]:
        """
        基于 book_id 和 call_no 双重去重，保留最新的记录
        
        优先级规则：
        1. 如果有 embedding_date 时间字段，保留时间最新的记录
        2. 如果没有时间字段，保留 book_id 最大的记录
        
        Args:
            results: 检索结果列表
            
        Returns:
            去重后的结果列表
        """
        if not results:
            return results
            
        # 第一步：基于 book_id 去重
        book_dict = {}
        for result in results:
            book_id = str(result.get('book_id', ''))
            if not book_id:
                continue
                
            # 判断是否应该保留当前记录
            should_keep = False
            if book_id not in book_dict:
                should_keep = True
            else:
                existing = book_dict[book_id]
                should_keep = self._is_record_newer(result, existing)
            
            if should_keep:
                book_dict[book_id] = result
        
        book_id_deduplicated = list(book_dict.values())
        
        # 第二步：基于 call_no 去重，处理数据库中的重复脏数据
        call_no_dict = {}
        for result in book_id_deduplicated:
            call_no = str(result.get('call_no') or '').strip()
            if not call_no:
                # 如果没有索书号，直接保留
                call_no_dict[f"no_call_no_{result.get('book_id')}"] = result
                continue
                
            # 判断是否应该保留当前记录
            should_keep = False
            if call_no not in call_no_dict:
                should_keep = True
            else:
                existing = call_no_dict[call_no]
                should_keep = self._is_record_newer(result, existing)
            
            if should_keep:
                call_no_dict[call_no] = result
        
        # 按相似度排序并返回
        deduplicated = list(call_no_dict.values())
        deduplicated.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        
        logger.info(f"双重去重完成: 原始结果 {len(results)} 条，book_id去重后 {len(book_id_deduplicated)} 条，最终去重后 {len(deduplicated)} 条")
        return deduplicated
    
    def _is_record_newer(self, current: Dict, existing: Dict) -> bool:
        """
        判断当前记录是否比已有记录更新
        
        优先级规则：
        1. 如果有 embedding_date 时间字段，比较时间
        2. 如果没有时间字段，比较 book_id
        
        Args:
            current: 当前记录
            existing: 已有记录
            
        Returns:
            True 如果当前记录更新，False 否则
        """
        # 尝试比较 embedding_date
        current_date = (current.get('embedding_date') or '').strip()
        existing_date = (existing.get('embedding_date') or '').strip()
        
        if current_date and existing_date:
            # 如果两个记录都有时间字段，比较时间
            return current_date > existing_date
        
        # 如果只有一个记录有时间字段，有时间字段的记录更新
        if current_date and not existing_date:
            return True
        
        if not current_date and existing_date:
            return False
        
        # 如果都没有时间字段，比较 book_id
        current_id = int(current.get('id', 0))
        existing_id = int(existing.get('id', 0))
        
        return current_id > existing_id

    @staticmethod
    def _shorten_text(text: str, limit: int = 80) -> str:
        snippet = (text or "").strip().replace("\n", " ")
        if len(snippet) <= limit:
            return snippet
        return snippet[:limit] + "..."
