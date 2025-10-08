import json
import os
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

from .dify_client import DifyClient, DifyResponse
from .dify_enhanced_client import DifyEnhancedClient
from .dify_timeout_recovery import RecoveryConfig
from .entity_extractor import EntityExtractor, EntityFields
from .result_formatter import ResultFormatter
from ...utils.logger import get_logger
from ...utils.llm_api import _resolve_env

logger = get_logger(__name__)

@dataclass
class ProcessingStats:
    """处理统计信息"""
    processed: int = 0
    skipped: int = 0
    failed: int = 0
    
    @property
    def total(self) -> int:
        return self.processed + self.skipped + self.failed

class RagProcessor:
    """RAG 检索处理器，协调整个检索流程"""
    
    def __init__(self, settings: Dict[str, Any]):
        """
        初始化RAG处理器
        
        Args:
            settings: 全局配置字典
        """
        self.settings = settings
        self.extractor = EntityExtractor()
        self.formatter = ResultFormatter()
        
        # 从配置中获取L3设置
        self.l3_config = settings.get("l3_context_interpretation", {})
        
        logger.info("RAG处理器初始化完成")
    
    def process_json_file(self, file_path: str, task_name: str, metadata: Dict[str, Any]) -> ProcessingStats:
        """
        处理单个 JSON 文件中的所有实体
        
        Args:
            file_path: JSON文件路径
            task_name: 任务名称（如"entity_label_retrieval"）
            metadata: 元数据信息
            
        Returns:
            ProcessingStats: 处理统计信息
        """
        stats = ProcessingStats()
        
        try:
            # 检查任务是否在全局和任务级别启用
            if not self._is_task_enabled(task_name):
                logger.warning(f"任务未在全局或任务级别启用，跳过处理 task={task_name} file={file_path}")
                return stats
            
            # 创建Dify客户端
            dify_client = self._create_dify_client(task_name)
            if not dify_client:
                logger.error(f"无法创建Dify客户端 task={task_name}")
                return stats
            
            # 读取 JSON 文件
            logger.info(f"开始处理JSON文件 file={file_path} task={task_name}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            row_id = data.get("row_id", "")
            entities = data.get("entities", [])
            
            logger.info(f"JSON文件读取完成 row_id={row_id} entities_count={len(entities)}")
            
            modified = False
            
            for entity in entities:
                try:
                    entity_type = entity.get("type", "")
                    entity_label = entity.get("label", "")
                    
                    # 检查实体类型特定的任务是否启用
                    if not self._is_task_enabled_for_entity(task_name, entity_type):
                        logger.debug(f"实体类型的任务未启用，跳过 entity_type={entity_type} task={task_name} label={entity_label}")
                        stats.skipped += 1
                        continue
                    
                    # 检查是否需要跳过（已执行过）
                    if self.extractor.should_skip_entity(entity, task_name):
                        stats.skipped += 1
                        continue
                    
                    # 处理单个实体
                    result = self._process_single_entity(entity, row_id, metadata, task_name, dify_client)
                    
                    if result:
                        # 更新实体节点
                        self.formatter.update_entity_with_rag_result(entity, result, task_name)
                        modified = True
                        stats.processed += 1
                        
                        # 记录成功日志
                        logger.info(f"实体处理完成 label={entity.get('label')} status={result['status']}")
                    else:
                        stats.failed += 1
                        
                except Exception as e:
                    # 记录错误但不中断整个流程
                    logger.error(f"实体处理失败 file={file_path} entity_label={entity.get('label')} error={str(e)}")
                    stats.failed += 1
                    continue
            
            # 如果有修改，写回文件
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"文件已更新 path={file_path}")
            
            logger.info(f"JSON文件处理完成 file={file_path} stats={stats}")
            return stats
            
        except Exception as e:
            logger.error(f"JSON文件处理失败 file={file_path} error={str(e)}")
            return stats
    
    def _process_single_entity(self, 
                             entity: Dict[str, Any], 
                             row_id: str, 
                             metadata: Dict[str, Any], 
                             task_name: str, 
                             dify_client: Union[DifyClient, DifyEnhancedClient]) -> Optional[Dict[str, Any]]:
        """
        处理单个实体的RAG检索
        
        Args:
            entity: 实体节点数据
            row_id: 行ID
            metadata: 元数据
            task_name: 任务名称
            dify_client: Dify客户端
            
        Returns:
            Optional[Dict[str, Any]]: 格式化的结果，失败时返回None
        """
        try:
            # 提取实体字段
            fields = self.extractor.extract_entity_fields(entity, row_id, metadata)
            
            logger.debug(f"实体字段提取完成 label={fields.label} type={fields.type}")
            
            # 调用 Dify API
            dify_response = dify_client.query_knowledge_base(
                fields.label, 
                fields.type, 
                fields.context_hint
            )
            
            # 格式化结果
            result = self.formatter.format_rag_result(dify_response, task_name)
            
            return result
            
        except Exception as e:
            logger.error(f"单个实体处理失败 label={entity.get('label')} error={str(e)}")
            return None
    
    def _create_dify_client(self, task_name: str) -> Optional[DifyEnhancedClient]:
        """
        创建Dify增强客户端（支持超时恢复）
        
        Args:
            task_name: 任务名称
            
        Returns:
            Optional[DifyEnhancedClient]: Dify增强客户端实例，失败时返回None
        """
        try:
            task_config = self._get_task_config(task_name)
            
            api_key = _resolve_env(task_config.get("dify_key", ""))
            base_url = task_config.get("dify_base_url", "https://api.dify.ai/v1")
            rate_limit_ms = task_config.get("rate_limit_ms", 1000)
            timeout_seconds = task_config.get("timeout_seconds", 90)
            
            if not api_key:
                logger.error(f"Dify API密钥未配置 task={task_name}")
                return None
            
            # 构建超时恢复配置
            recovery_config_data = task_config.get("timeout_recovery", {})
            recovery_config = RecoveryConfig(
                enabled=recovery_config_data.get("enabled", True),
                max_attempts=recovery_config_data.get("max_attempts", 3),
                delay_seconds=recovery_config_data.get("delay_seconds", 10),
                match_time_window=recovery_config_data.get("match_time_window", 120)
            )
            
            logger.info(f"创建Dify增强客户端 task={task_name} recovery_enabled={recovery_config.enabled}")
            
            return DifyEnhancedClient(
                api_key=api_key,
                base_url=base_url, 
                rate_limit_ms=rate_limit_ms,
                timeout_seconds=timeout_seconds,
                recovery_config=recovery_config
            )
            
        except Exception as e:
            logger.error(f"创建Dify增强客户端失败 task={task_name} error={str(e)}")
            return None
    
    def _is_task_enabled(self, task_name: str) -> bool:
        """检查指定任务是否在全局和任务级别启用"""
        if not self.l3_config.get("enabled", False):
            return False
        
        task_config = self._get_task_config(task_name)
        return task_config.get("enabled", False)
    
    def _is_task_enabled_for_entity(self, task_name: str, entity_type: str) -> bool:
        """
        检查指定任务对指定实体类型是否启用
        实现三层检查机制：全局→任务→实体类型
        
        Args:
            task_name: 任务名称（如"entity_label_retrieval"）
            entity_type: 实体类型（如"person"）
            
        Returns:
            bool: 是否启用
        """
        # 第一层：全局启用检查
        if not self.l3_config.get("enabled", False):
            return False
        
        # 第二层：任务全局启用检查
        rag_tasks = self.l3_config.get("rag_tasks", {})
        task_config = rag_tasks.get(task_name, {})
        if not task_config.get("enabled", False):
            return False
        
        # 第三层：实体类型特定任务启用检查
        entity_types = self.l3_config.get("entity_types", {})
        entity_config = entity_types.get(entity_type, {})
        entity_task_config = entity_config.get(task_name, {})
        
        return entity_task_config.get("enabled", False)
    
    def _get_task_config(self, task_name: str) -> Dict[str, Any]:
        """获取指定任务的配置"""
        rag_tasks = self.l3_config.get("rag_tasks", {})
        return rag_tasks.get(task_name, {})