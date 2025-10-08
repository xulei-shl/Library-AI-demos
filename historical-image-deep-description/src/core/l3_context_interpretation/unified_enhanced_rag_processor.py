"""
统一增强RAG检索模块

该模块为所有实体类型提供统一的扩展检索功能：
1. 使用大模型从原始label提取优化的搜索关键词
2. 用优化的关键词替换原始label进行RAG检索
3. 结果写入独立的JSON节点，保留搜索关键词信息

设计原则：
- 继承通用增强RAG检索处理器
- 根据实体类型动态选择提示词策略
- 与现有RAG流程保持一致
- 配置驱动，支持按需启用
"""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .base_enhanced_rag_processor import BaseEnhancedRAGProcessor
from ...utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EnhancedRAGFields:
    """增强RAG检索的字段数据（保持向后兼容）"""
    original_label: str
    enhanced_label: str
    type: str
    context_hint: str
    row_id: str


class UnifiedEnhancedRAGProcessor(BaseEnhancedRAGProcessor):
    """统一增强RAG检索处理器（继承通用处理器）"""
    
    def __init__(self, settings: Dict[str, Any]):
        """
        初始化统一增强RAG检索处理器
        
        Args:
            settings: 全局配置字典
        """
        super().__init__(settings)
        logger.info("统一增强RAG检索处理器初始化完成")
    
    def get_task_name(self) -> str:
        """
        获取任务名称
        
        Returns:
            str: 任务名称
        """
        return "enhanced_rag_retrieval"
    
    def _build_user_prompt(self, original_label: str, entity_type: str, metadata: Dict[str, Any]) -> str:
        """
        构建用户提示词（根据实体类型动态选择策略）
        
        Args:
            original_label: 原始实体标签
            entity_type: 实体类型
            metadata: 元数据
            
        Returns:
            str: 构建的用户提示词
        """
        # 构建上下文信息
        context_info = ""
        if metadata:
            context_info = f"上下文：{str(metadata)[:200]}..."  # 限制长度避免token过多
        
        # 根据实体类型选择不同的提示词策略
        if entity_type == "event":
            return self._build_event_prompt(original_label, entity_type, metadata)
        elif entity_type == "work":
            return self._build_work_prompt(original_label, entity_type, metadata)
        elif entity_type == "architecture":
            return self._build_architecture_prompt(original_label, entity_type, metadata)
        else:
            # 默认提示词策略
            return self._build_default_prompt(original_label, entity_type, metadata)
    
    def _build_event_prompt(self, original_label: str, entity_type: str, metadata: Dict[str, Any]) -> str:
        """构建事件类型的用户提示词"""
        context_info = ""
        if metadata:
            context_info = f"上下文：{str(metadata)[:200]}..."  # 限制长度避免token过多
        
        return f"""请为以下实体提取1-2个核心关键词用于事件检索：

实体标签：{original_label}
实体类型：{entity_type}
{context_info}

请只输出关键词，用空格分隔。"""
    
    def _build_work_prompt(self, original_label: str, entity_type: str, metadata: Dict[str, Any]) -> str:
        """构建作品类型的用户提示词"""
        # 构建上下文信息，用于辅助识别创作者
        context_info = ""
        if metadata:
            # 提取可能包含创作者信息的字段
            relevant_fields = []
            for key, value in metadata.items():
                if any(keyword in str(key).lower() for keyword in ["创作", "作者", "导演", "编剧", "作曲", "词作"]):
                    relevant_fields.append(f"{key}: {value}")
            
            if relevant_fields:
                context_info = f"相关信息：{'; '.join(relevant_fields[:3])}"  # 限制字段数量
            else:
                context_info = f"上下文：{str(metadata)[:200]}..."  # 限制长度避免token过多
        
        return f"""请优化以下作品实体的标签，生成最佳的RAG检索关键词：

作品标签：{original_label}
实体类型：{entity_type}
{context_info}

请按照以下策略优化：
1. 如果能识别创作者，输出格式：创作者 作品名
2. 如果无法识别创作者，输出格式：作品 作品名
3. 去除书名号《》、引号等标点符号
4. 去除"话剧"、"电影"、"小说"等作品类型标识
5. 保持作品核心名称的完整性

示例：
- 话剧《雷雨》→ 曹禺 雷雨 （如果知道创作者是曹禺）
- 话剧《日出》→ 作品 日出 （如果不知道创作者）

请只输出优化后的关键词，用空格分隔。"""
    
    def _build_architecture_prompt(self, original_label: str, entity_type: str, metadata: Dict[str, Any]) -> str:
        """构建建筑类型的用户提示词"""
        context_info = ""
        if metadata:
            context_info = f"上下文：{str(metadata)[:200]}..."  # 限制长度避免token过多
        
        return f"""请为以下建筑实体提取1-2个核心关键词用于检索：

实体标签：{original_label}
实体类型：{entity_type}
{context_info}

请只输出关键词，用空格分隔。"""
    
    def _build_default_prompt(self, original_label: str, entity_type: str, metadata: Dict[str, Any]) -> str:
        """构建默认的用户提示词"""
        context_info = ""
        if metadata:
            context_info = f"上下文：{str(metadata)[:200]}..."  # 限制长度避免token过多
        
        return f"""请为以下实体提取1-2个核心关键词用于检索：

实体标签：{original_label}
实体类型：{entity_type}
{context_info}

请只输出关键词，用空格分隔。"""
    
    def should_skip_entity(self, entity: Dict[str, Any], task_name: str) -> bool:
        """
        检查实体是否应该跳过增强RAG检索
        
        对于统一增强RAG处理器，需要检查多种可能的已执行节点：
        1. 新的统一节点：l3_rag_enhanced_rag_retrieval
        2. 旧的统一处理器节点：l3_rag_unified_enhanced_rag_retrieval
        3. 各独立处理器的节点：l3_rag_enhanced_{entity_type}_retrieval
        4. metadata中的记录
        
        Args:
            entity: 实体节点数据
            task_name: 任务名称
            
        Returns:
            bool: 是否应该跳过
        """
        # 检查新的统一节点（当前应该使用的节点）
        unified_result_field = "l3_rag_enhanced_rag_retrieval"
        if unified_result_field in entity and entity[unified_result_field] is not None:
            executed_meta = entity[unified_result_field].get("meta", {})
            executed_at = executed_meta.get("executed_at")
            if executed_at:
                entity_label = entity.get("label", "")
                logger.info(f"实体已通过统一增强RAG处理器执行过，跳过处理 entity={entity_label} executed_at={executed_at}")
                return True
        
        # 检查metadata中是否有统一节点的异常状态记录
        metadata = entity.get("metadata", {})
        if unified_result_field in metadata:
            executed_at = metadata[unified_result_field].get("executed_at")
            status = metadata[unified_result_field].get("status")
            if executed_at and status:
                entity_label = entity.get("label", "")
                logger.info(f"实体已通过统一增强RAG处理器执行过（metadata记录），跳过处理 entity={entity_label} status={status} executed_at={executed_at}")
                return True
        
        # 检查旧的统一处理器节点（向后兼容）
        if super().should_skip_entity(entity, task_name):
            return True
        
        # 检查是否已通过独立的增强RAG处理器执行过（向后兼容）
        entity_type = entity.get("type", "")
        if entity_type:
            # 构建独立处理器的节点名
            independent_task_name = f"enhanced_{entity_type}_retrieval"
            independent_result_field = f"l3_rag_{independent_task_name}"
            
            # 检查实体字段是否存在且有成功结果
            if independent_result_field in entity and entity[independent_result_field] is not None:
                # 检查是否有执行时间戳（表示已完成）
                executed_meta = entity[independent_result_field].get("meta", {})
                executed_at = executed_meta.get("executed_at")
                
                if executed_at:
                    entity_label = entity.get("label", "")
                    logger.info(f"实体已通过独立增强RAG处理器执行过，跳过处理 entity={entity_label} task={independent_task_name} executed_at={executed_at}")
                    return True
            
            # 检查metadata中是否有独立处理器的异常状态记录
            if independent_result_field in metadata:
                executed_at = metadata[independent_result_field].get("executed_at")
                status = metadata[independent_result_field].get("status")
                
                if executed_at and status:
                    entity_label = entity.get("label", "")
                    logger.info(f"实体已通过独立增强RAG处理器执行过（metadata记录），跳过处理 entity={entity_label} task={independent_task_name} status={status} executed_at={executed_at}")
                    return True
        
        return False
