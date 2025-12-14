#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图书检索接口（预留）

提供基于向量的语义检索功能，供后续推荐模块调用
"""

import yaml
from typing import Dict, List, Optional
from src.utils.logger import get_logger
from .embedding_client import EmbeddingClient
from .vector_store import VectorStore
from .database_reader import DatabaseReader

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
            book_id = result['metadata']['book_id']
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
                    'embedding_id': result['embedding_id']
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
    
    def close(self):
        """关闭资源"""
        self.db_reader.close()
        logger.info("检索器资源已释放")
