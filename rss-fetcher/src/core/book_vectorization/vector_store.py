#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ChromaDB 向量存储管理

负责向量的存储、检索和管理
"""

import time
from typing import Dict, List, Optional
import chromadb
from src.utils.logger import get_logger

logger = get_logger(__name__)


class VectorStore:
    """ChromaDB 存储管理"""
    
    def __init__(self, config: Dict):
        """
        初始化向量存储
        
        Args:
            config: 向量数据库配置字典
        """
        self.config = config
        self.client = self._init_client()
        self.collection = self._get_or_create_collection()
    
    def _init_client(self) -> chromadb.PersistentClient:
        """
        初始化 ChromaDB 客户端
        
        Returns:
            ChromaDB 客户端实例
        """
        client = chromadb.PersistentClient(
            path=self.config['persist_directory']
        )
        
        logger.info(f"ChromaDB 客户端初始化成功: path={self.config['persist_directory']}")
        return client
    
    def _get_or_create_collection(self):
        """
        获取或创建 Collection
        
        Returns:
            Collection 实例
        """
        collection = self.client.get_or_create_collection(
            name=self.config['collection_name'],
            metadata={"hnsw:space": self.config['distance_metric']}
        )
        
        logger.info(f"Collection 准备就绪: name={self.config['collection_name']}, metric={self.config['distance_metric']}")
        return collection
    
    def add(self, embedding: List[float], metadata: Dict, document: str) -> str:
        """
        添加向量到数据库
        
        Args:
            embedding: 向量数据
            metadata: 元数据
            document: 原始文档文本
            
        Returns:
            embedding_id: ChromaDB 中的文档ID
        """
        # 生成唯一 ID
        embedding_id = f"book_{metadata['book_id']}_{int(time.time())}"
        
        self.collection.add(
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[document],
            ids=[embedding_id]
        )
        
        logger.debug(f"向量添加成功: embedding_id={embedding_id}")
        return embedding_id
    
    def add_batch(self, embeddings: List[List[float]], metadatas: List[Dict], documents: List[str]) -> List[str]:
        """
        批量添加向量到数据库（性能优化）
        
        Args:
            embeddings: 向量列表
            metadatas: 元数据列表
            documents: 文档文本列表
            
        Returns:
            embedding_ids: ChromaDB 中的文档ID列表
        """
        # 生成唯一 ID 列表
        embedding_ids = [
            f"book_{metadata['book_id']}_{int(time.time())}_{i}"
            for i, metadata in enumerate(metadatas)
        ]
        
        self.collection.add(
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
            ids=embedding_ids
        )
        
        logger.debug(f"批量向量添加成功: 数量={len(embedding_ids)}")
        return embedding_ids
    
    def search(
        self, 
        query_embedding: List[float], 
        top_k: int = 10, 
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        向量检索
        
        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量
            filter_metadata: 元数据过滤条件（例如: {"douban_rating": {"$gte": "8.0"}}）
        
        Returns:
            检索结果列表
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata  # 元数据过滤
        )
        
        # 格式化结果
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'embedding_id': results['ids'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i],
                'document': results['documents'][0][i]
            })
        
        logger.debug(f"向量检索完成: 查询结果数={len(formatted_results)}")
        return formatted_results
    
    def reset(self):
        """重置向量库（删除所有数据）"""
        try:
            self.client.delete_collection(self.config['collection_name'])
            logger.warning(f"Collection 已删除: {self.config['collection_name']}")
        except Exception as e:
            logger.warning(f"删除 Collection 失败（可能不存在）: {str(e)}")
        
        # 重新创建
        self.collection = self._get_or_create_collection()
        logger.warning("向量库已重置")
    
    def get_count(self) -> int:
        """
        获取向量库中的文档数量
        
        Returns:
            文档数量
        """
        count = self.collection.count()
        logger.debug(f"向量库文档数量: {count}")
        return count
