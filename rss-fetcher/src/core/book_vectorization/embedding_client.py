#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Embedding API 调用封装

负责调用 OpenAI Embedding API 生成文本向量
"""

import os
import time
from typing import Dict, List
from openai import OpenAI
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingClient:
    """Embedding API 调用封装"""
    
    def __init__(self, config: Dict):
        """
        初始化 Embedding 客户端
        
        Args:
            config: Embedding 配置字典
        """
        self.config = config
        self.client = self._init_client()
    
    def _init_client(self) -> OpenAI:
        """
        初始化 OpenAI 客户端
        
        Returns:
            OpenAI 客户端实例
        """
        api_key = self._resolve_env(self.config['api_key'])
        
        client = OpenAI(
            api_key=api_key,
            base_url=self.config['base_url'],
            timeout=self.config['timeout']
        )
        
        logger.info(f"Embedding 客户端初始化成功: model={self.config['model']}")
        return client
    
    def get_embedding(self, text: str) -> List[float]:
        """
        获取文本的向量表示（带重试）
        
        Args:
            text: 输入文本
        
        Returns:
            向量列表
            
        Raises:
            Exception: API 调用失败
        """
        for attempt in range(self.config['max_retries']):
            try:
                response = self.client.embeddings.create(
                    model=self.config['model'],
                    input=text,
                    dimensions=self.config.get('dimensions')  # 可选参数
                )
                
                embedding = response.data[0].embedding
                logger.debug(f"Embedding 生成成功: 维度={len(embedding)}")
                return embedding
                
            except Exception as e:
                logger.warning(f"Embedding API 调用失败(尝试 {attempt+1}/{self.config['max_retries']}): {str(e)}")
                
                if attempt < self.config['max_retries'] - 1:
                    time.sleep(self.config['retry_delay'])
                else:
                    logger.error(f"Embedding API 调用最终失败: {str(e)}")
                    raise
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量获取多个文本的向量（性能优化）
        
        Args:
            texts: 文本列表（建议每批不超过100个）
        
        Returns:
            向量列表
            
        Raises:
            Exception: API 调用失败
        """
        for attempt in range(self.config['max_retries']):
            try:
                response = self.client.embeddings.create(
                    model=self.config['model'],
                    input=texts,  # 传入列表
                    dimensions=self.config.get('dimensions')
                )
                
                embeddings = [item.embedding for item in response.data]
                logger.debug(f"批量 Embedding 生成成功: 数量={len(embeddings)}")
                return embeddings
                
            except Exception as e:
                logger.warning(f"批量 Embedding API 调用失败(尝试 {attempt+1}/{self.config['max_retries']}): {str(e)}")
                
                if attempt < self.config['max_retries'] - 1:
                    time.sleep(self.config['retry_delay'])
                else:
                    logger.error(f"批量 Embedding API 调用最终失败: {str(e)}")
                    raise
    
    def _resolve_env(self, value: str) -> str:
        """
        解析环境变量
        
        Args:
            value: 配置值，如果以 'env:' 开头则从环境变量读取
            
        Returns:
            解析后的值
        """
        if value.startswith('env:'):
            env_var = value[4:]
            env_value = os.getenv(env_var)
            if not env_value:
                logger.warning(f"环境变量 {env_var} 未设置")
            return env_value
        return value
