#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图书检索接口（预留）

提供基于向量的语义检索功能，供后续推荐模块调用
"""

import yaml
from typing import Dict, List, Optional, Sequence
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
            filter_metadata['douban_rating'] = {"$gte": str(min_rating)}
        
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
                    'title': book_info['douban_title'],
                    'author': book_info['douban_author'],
                    'rating': book_info['douban_rating'],
                    'summary': book_info.get('douban_summary', ''),
                    'call_no': book_info.get('call_no', ''),
                    'similarity_score': 1 - result['distance'],  # 转换为相似度
                    'embedding_id': result['embedding_id'],
                    'source_query_text': query_text,
                })
        
        logger.info(f"文本检索完成: 返回 {len(enriched_results)} 本书")
        return enriched_results
    
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
                logger.info("执行子查询: type=%s, top_k=%s", bucket, top_k_each)
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
        if rerank:
            if not self.reranker.enabled:
                logger.warning("已请求 rerank 但配置未启用，将跳过该步骤。")
            else:
                anchor_query = self._select_anchor_query(package_dict, priorities)
                fused_results = self._apply_rerank(anchor_query, fused_results)
        return fused_results
    
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

    @staticmethod
    def _compose_candidate_text(candidate: Dict) -> str:
        parts = [candidate.get('title', ''), candidate.get('author', ''), candidate.get('summary', '')]
        return '\n'.join(part for part in parts if part)
