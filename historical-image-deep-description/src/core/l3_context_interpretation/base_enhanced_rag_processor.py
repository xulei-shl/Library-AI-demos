"""
通用增强RAG检索处理器

该模块提供增强RAG检索的通用基础架构，支持：
1. 可配置的实体类型和提示词策略
2. 统一的Dify客户端管理
3. 标准化的结果处理流程
4. 可扩展的label增强策略

设计原则：
- 抽象共享逻辑，支持多种实体类型的增强检索
- 配置驱动，便于扩展新的实体类型
- 保持与现有RAG系统的兼容性
- 复用统一的标签扩展逻辑
"""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

# 添加导入
from .base_label_enhancer import BaseLabelEnhancer
from .dify_client import DifyClient
from .dify_enhanced_client import DifyEnhancedClient
from .dify_timeout_recovery import RecoveryConfig
from .entity_extractor import EntityExtractor, EntityFields
from .result_formatter import ResultFormatter
from ...utils.logger import get_logger
from ...utils.llm_api import invoke_model, _resolve_env

logger = get_logger(__name__)


@dataclass
class EnhancedRAGFields:
    """增强RAG检索的字段数据"""
    original_label: str
    enhanced_label: str
    type: str
    context_hint: str
    row_id: str
    task_type: str  # 任务类型标识


# 修改类定义，继承BaseLabelEnhancer
class BaseEnhancedRAGProcessor(BaseLabelEnhancer):
    """增强RAG检索的基础处理器类"""
    
    def __init__(self, settings: Dict[str, Any]):
        """
        初始化增强RAG检索处理器
        
        Args:
            settings: 全局配置字典
        """
        # 调用父类初始化
        super().__init__(settings)
        self.extractor = EntityExtractor()
        self.formatter = ResultFormatter()
        
        # 从配置中获取L3设置
        self.l3_config = settings.get("l3_context_interpretation", {})
        self.enhanced_config = self.l3_config.get("enhanced_rag_retrieval", {})
        
        logger.info(f"{self.__class__.__name__} 初始化完成")
    
    def is_enabled_for_entity(self, entity_type: str) -> bool:
        """
        检查增强RAG检索是否对指定实体类型启用
        
        实现三层检查机制：
        1. 全局启用检查：l3_context_interpretation.enabled
        2. 功能启用检查：enhanced_rag_retrieval.enabled  
        3. 实体类型启用检查：enhanced_rag_retrieval.entity_types.{type}.enabled
        
        Args:
            entity_type: 实体类型（person, organization, event等）
            
        Returns:
            bool: 是否启用
        """
        # 1. 全局启用检查
        if not self.l3_config.get("enabled", False):
            return False
        
        # 2. 功能启用检查
        if not self.enhanced_config.get("enabled", False):
            return False
        
        # 3. 实体类型启用检查
        entity_types_config = self.enhanced_config.get("entity_types", {})
        
        # 如果没有entity_types配置，默认启用（向后兼容）
        if not entity_types_config:
            return True
        
        # 检查特定实体类型的配置
        type_config = entity_types_config.get(entity_type, {})
        return type_config.get("enabled", False)
    
    # 删除重复的should_skip_entity方法，使用父类方法
    
    def process_entity(self, entity: Dict[str, Any], row_id: str, metadata: Dict[str, Any]) -> bool:
        """
        处理单个实体的增强RAG检索
        
        Args:
            entity: 实体节点数据
            row_id: 行ID
            metadata: 元数据
            
        Returns:
            bool: 处理是否成功
        """
        entity_type = entity.get("type", "")
        original_label = entity.get("label", "")
        task_name = self.get_task_name()
        
        enhanced_label = None
        try:
            # 检查是否启用
            if not self.is_enabled_for_entity(entity_type):
                logger.debug(f"{task_name}未启用 entity_type={entity_type} label={original_label}")
                return False
            
            # 检查是否应该跳过
            if self.should_skip_entity(entity, task_name):
                logger.debug(f"实体已处理过{task_name}，跳过 label={original_label}")
                return False
            
            # Step 1: 使用大模型增强label（使用父类方法）
            enhanced_label = self.enhance_label(original_label, entity_type, metadata)
            
            if not enhanced_label or enhanced_label.strip() == "":
                logger.warning(f"标签增强失败，跳过增强检索 original_label={original_label}")
                # 写入失败信息
                self._write_failure_result(entity, "标签增强失败", original_label, task_name)
                return False
            
            enhanced_label = enhanced_label.strip()
            logger.info(f"标签增强成功 original={original_label} enhanced={enhanced_label}")
            
            # Step 2: 创建Dify客户端
            dify_client = self._create_dify_client()
            if not dify_client:
                logger.error("无法创建Dify客户端")
                self._write_failure_result(entity, "Dify客户端创建失败", original_label, task_name, enhanced_label)
                return False
            
            # Step 3: 构建增强字段数据
            # 直接从实体节点中获取现有的context_hint，与entity_extractor.py保持一致
            context_hint_str = entity.get("context_hint", "")
            enhanced_fields = EnhancedRAGFields(
                original_label=original_label,
                enhanced_label=enhanced_label,
                type=entity_type,
                context_hint=context_hint_str,
                row_id=row_id,
                task_type=task_name
            )
            
            # Step 4: 调用Dify API（使用增强的label）
            dify_response = dify_client.query_knowledge_base(
                enhanced_fields.enhanced_label,
                enhanced_fields.type,
                enhanced_fields.context_hint
            )
            
            # Step 5: 格式化并写入结果
            result = self._format_enhanced_result(dify_response, enhanced_fields)
            self._write_success_result(entity, result, task_name)
            
            logger.info(f"{task_name}完成 original_label={original_label} enhanced_label={enhanced_label} status={result['status']}")
            return True
            
        except Exception as e:
            logger.error(f"{task_name}失败 original_label={original_label} error={str(e)}")
            self._write_failure_result(entity, f"处理异常: {str(e)}", original_label, task_name, enhanced_label)
            return False
    
    # 删除重复的_enhance_label_with_llm方法，使用父类方法
    
    # 保留抽象方法
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
    
    @abstractmethod
    def get_task_name(self) -> str:
        """
        获取任务名称（由子类实现）
        
        Returns:
            str: 任务名称
        """
        pass
    
    # 新增方法：获取实体配置
    def _get_entity_config(self, entity_type: str) -> Dict[str, Any]:
        """
        获取实体类型配置
        
        Args:
            entity_type: 实体类型
            
        Returns:
            Dict[str, Any]: 实体类型配置
        """
        entity_types_config = self.enhanced_config.get("entity_types", {})
        return entity_types_config.get(entity_type, {})
    
    def _create_dify_client(self) -> Optional[DifyEnhancedClient]:
        """
        创建Dify增强客户端
        
        Returns:
            Optional[DifyEnhancedClient]: Dify增强客户端实例，失败时返回None
        """
        try:
            api_key = _resolve_env(self.enhanced_config.get("dify_key", ""))
            base_url = self.enhanced_config.get("dify_base_url", "https://api.dify.ai/v1")
            rate_limit_ms = self.enhanced_config.get("rate_limit_ms", 1000)
            timeout_seconds = self.enhanced_config.get("timeout_seconds", 90)
            
            if not api_key:
                logger.error("增强RAG检索的Dify API密钥未配置")
                return None
            
            # 构建超时恢复配置
            recovery_config_data = self.enhanced_config.get("timeout_recovery", {})
            recovery_config = RecoveryConfig(
                enabled=recovery_config_data.get("enabled", True),
                max_attempts=recovery_config_data.get("max_attempts", 3),
                delay_seconds=recovery_config_data.get("delay_seconds", 10),
                match_time_window=recovery_config_data.get("match_time_window", 120)
            )
            
            logger.info(f"创建增强RAG检索Dify客户端 recovery_enabled={recovery_config.enabled}")
            
            return DifyEnhancedClient(
                api_key=api_key,
                base_url=base_url,
                rate_limit_ms=rate_limit_ms,
                timeout_seconds=timeout_seconds,
                recovery_config=recovery_config
            )
            
        except Exception as e:
            logger.error(f"创建增强RAG检索Dify客户端失败 error={str(e)}")
            return None
    
    def _format_enhanced_result(self, dify_response, enhanced_fields: EnhancedRAGFields) -> Dict[str, Any]:
        """
        格式化增强RAG检索结果
        
        Args:
            dify_response: Dify响应
            enhanced_fields: 增强字段数据
            
        Returns:
            Dict[str, Any]: 格式化的结果
        """
        # 使用标准的结果格式化器
        base_result = self.formatter.format_rag_result(dify_response, enhanced_fields.task_type)
        
        # 在结果中添加增强检索的特有信息
        # 使用metadata字段存储额外信息，与标准格式兼容
        enhanced_metadata = {
            "original_label": enhanced_fields.original_label,
            "search_keyword": enhanced_fields.enhanced_label,
            "label_enhanced": "true",
            "task_type": enhanced_fields.task_type
        }
        
        # 将增强信息添加到结果中
        base_result["metadata"] = enhanced_metadata
        
        return base_result
    
    def _write_success_result(self, entity: Dict[str, Any], result: Dict[str, Any], task_name: str):
        """
        写入成功结果到实体节点
        
        使用标准的ResultFormatter方法，确保与L3 RAG系统一致
        
        Args:
            entity: 实体节点数据
            result: 格式化的结果
            task_name: 任务名称
        """
        # 使用标准的ResultFormatter方法写入结果
        self.formatter.update_entity_with_rag_result(entity, result, task_name)
        
        logger.debug(f"{task_name}结果写入成功")
    
    def _write_failure_result(self, entity: Dict[str, Any], error_msg: str, 
                             original_label: str, task_name: str, enhanced_label: Optional[str] = None):
        """
        写入失败结果到实体节点
        
        使用标准的ResultFormatter方法，然后添加增强信息
        
        Args:
            entity: 实体节点数据
            error_msg: 错误信息
            original_label: 原始标签
            task_name: 任务名称
            enhanced_label: 增强标签（可选）
        """
        result_field = f"l3_rag_{task_name}"
        
        # 构建标准的失败结果
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).astimezone()
        
        failure_result = {
            "content": None,
            "status": "error",
            "meta": {
                "executed_at": now.isoformat(),
                "task_type": task_name,
                "dify_response_id": "",
                "error": error_msg
            }
        }
        
        # 使用标准的ResultFormatter方法写入结果
        self.formatter.update_entity_with_rag_result(entity, failure_result, task_name)
        
        # 添加增强信息到metadata中
        if "metadata" not in entity:
            entity["metadata"] = {}
        
        if result_field in entity["metadata"]:
            # 在已有的metadata中添加增强信息
            entity["metadata"][result_field].update({
                "original_label": original_label,
                "search_keyword": enhanced_label if enhanced_label else "",
                "label_enhanced": "true" if enhanced_label else "false"
            })
        
        logger.debug(f"{task_name}失败信息写入 error={error_msg}")