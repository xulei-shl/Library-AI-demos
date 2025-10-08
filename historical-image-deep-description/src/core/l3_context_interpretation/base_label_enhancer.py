"""
标签扩展基础类

该模块提供标签扩展的通用基础架构，支持：
1. 可配置的实体类型和提示词策略
2. 统一的大模型调用管理
3. 标准化的结果处理流程
4. 可扩展的label增强策略

设计原则：
- 抽象共享逻辑，支持多种实体类型的标签扩展
- 配置驱动，便于扩展新的实体类型
- 与检索逻辑解耦，专注于标签扩展
"""

import json
import os
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from .entity_extractor import EntityExtractor
from .result_formatter import ResultFormatter
from ...utils.logger import get_logger
from ...utils.llm_api import invoke_model, _resolve_env

logger = get_logger(__name__)


class BaseLabelEnhancer(ABC):
    """标签扩展的基础类"""
    
    def __init__(self, settings: Dict[str, Any]):
        """
        初始化标签扩展器
        
        Args:
            settings: 全局配置字典
        """
        self.settings = settings
        self.extractor = EntityExtractor()
        self.formatter = ResultFormatter()
        
        # 从配置中获取L3设置
        self.l3_config = settings.get("l3_context_interpretation", {})
        
        logger.info(f"{self.__class__.__name__} 初始化完成")
    
    def enhance_label(self, original_label: str, entity_type: str, metadata: Dict[str, Any]) -> Optional[str]:
        """
        使用大模型增强label
        
        Args:
            original_label: 原始实体标签
            entity_type: 实体类型
            metadata: 元数据
            
        Returns:
            Optional[str]: 增强后的label，失败时返回None
        """
        try:
            # 获取实体类型配置
            entity_config = self._get_entity_config(entity_type)
            
            # 获取任务名
            task_name = entity_config.get("task_name", "")
            
            if not task_name:
                logger.error(f"实体类型{entity_type}的task_name未配置")
                return None
            
            # 构建用户提示词
            user_content = self._build_user_prompt(original_label, entity_type, metadata)
            
            messages = [
                {"role": "user", "content": user_content}
            ]
            
            # 直接使用invoke_model，由它自动从 tasks 配置中读取系统提示词
            output = invoke_model(task_name, messages, self.settings)
            
            # 简单清理输出
            enhanced_label = output.strip().replace('\n', ' ').replace('\r', ' ')
            # 移除可能的引号
            enhanced_label = enhanced_label.strip('"\'`')
            
            return enhanced_label if enhanced_label else None
            
        except Exception as e:
            logger.error(f"大模型标签增强失败 original_label={original_label} error={e}")
            return None
    
    def should_skip_entity(self, entity: Dict[str, Any], task_name: str) -> bool:
        """
        检查实体是否已执行过指定的任务
        
        兼容L2阶段的异常处理模式：
        - 检查实体字段是否有成功结果
        - 检查metadata中是否有异常状态记录
        
        Args:
            entity: 实体节点数据
            task_name: 任务名称
            
        Returns:
            bool: True 表示应跳过，False 表示需要执行
        """
        # 构建任务字段名，增强RAG任务使用l3_rag_前缀，增强Web检索使用l3_前缀
        if "web" in task_name.lower():
            result_field = f"l3_{task_name}"
        else:
            result_field = f"l3_rag_{task_name}"
        
        # 检查实体字段是否存在且有成功结果
        if result_field in entity and entity[result_field] is not None:
            # 检查是否有执行时间戳（表示已完成）
            executed_meta = entity[result_field].get("meta", {})
            executed_at = executed_meta.get("executed_at")
            
            if executed_at:
                entity_label = entity.get("label", "")
                logger.info(f"实体已执行过任务，跳过处理 entity={entity_label} task={task_name} executed_at={executed_at}")
                return True
        
        # 检查metadata中是否有异常状态记录
        metadata = entity.get("metadata", {})
        if result_field in metadata:
            executed_at = metadata[result_field].get("executed_at")
            status = metadata[result_field].get("status")
            
            if executed_at and status:
                entity_label = entity.get("label", "")
                logger.info(f"实体已执行过任务（metadata记录），跳过处理 entity={entity_label} task={task_name} status={status} executed_at={executed_at}")
                return True
        
        return False
    
    @abstractmethod
    def _get_entity_config(self, entity_type: str) -> Dict[str, Any]:
        """
        获取实体类型配置（由子类实现）
        
        Args:
            entity_type: 实体类型
            
        Returns:
            Dict[str, Any]: 实体类型配置
        """
        pass
    
    @abstractmethod
    def _build_user_prompt(self, original_label: str, entity_type: str, metadata: Dict[str, Any]) -> str:
        """
        构建用户提示词（由子类实现）
        
        Args:
            original_label: 原始实体标签
            entity_type: 实体类型
            metadata: 元数据
            
        Returns:
            str: 构建的用户提示词
        """
        pass