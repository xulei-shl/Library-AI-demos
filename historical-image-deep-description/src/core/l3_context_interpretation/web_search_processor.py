"""
Web搜索处理器

L3阶段Web搜索功能的主协调器，整合搜索和分析的完整流程。
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ...utils.logger import get_logger
from .entity_extractor import EntityExtractor
from .result_formatter import ResultFormatter
from .zhipu_client import ZhipuClient
from .web_result_analyzer import WebResultAnalyzer

logger = get_logger(__name__)


class WebSearchProcessor:
    """
    Web搜索主处理器
    
    协调智谱AI搜索、LLM分析和结果存储的完整流程。
    """
    
    def __init__(self, settings: Dict[str, Any]):
        """
        初始化处理器
        
        Args:
            settings: 全局配置字典
        """
        self.settings = settings
        self.web_config = self._get_web_search_config()
        
        # 初始化组件
        self.entity_extractor = EntityExtractor()  # EntityExtractor不需要参数
        self.result_formatter = ResultFormatter()
        
        # 初始化智谱AI客户端
        zhipu_config = self.web_config.get("zhipu_ai", {})
        api_key = self._get_api_key(zhipu_config.get("api_key", ""))
        self.zhipu_client = ZhipuClient(api_key, zhipu_config)
        
        # 初始化结果分析器
        self.analyzer = WebResultAnalyzer(settings)
        
        logger.info("Web搜索处理器初始化完成")
    
    def _get_web_search_config(self) -> Dict[str, Any]:
        """获取Web搜索配置"""
        return self.settings.get("l3_context_interpretation", {}).get("web_search", {})
    
    def _get_api_key(self, key_config: str) -> str:
        """获取API密钥"""
        if key_config.startswith("env:"):
            import os
            env_var = key_config[4:]  # 移除 "env:" 前缀
            api_key = os.getenv(env_var)
            if not api_key:
                raise ValueError(f"环境变量 {env_var} 未设置")
            return api_key
        else:
            return key_config
    
    def process_entity_web_search(self, entity: Dict[str, Any], row_id: str) -> bool:
        """
        处理单个实体的Web搜索
        
        Args:
            entity: 实体信息字典
            row_id: 行ID
            
        Returns:
            bool: 处理是否成功
        """
        label = entity.get("label", "")
        entity_type = entity.get("type", "")
        
        try:
            # 检查是否为该实体类型启用Web搜索
            if not self.is_enabled_for_entity_type(entity_type):
                logger.info(f"Web搜索未对实体类型启用，跳过处理 type={entity_type} label='{label}' row_id={row_id}")
                return True
            
            # 检查是否应该跳过
            if self.should_skip_entity(entity):
                logger.info(f"跳过已处理的实体 label='{label}' row_id={row_id}")
                return True
            
            logger.info(f"开始Web搜索处理 label='{label}' type={entity_type} row_id={row_id}")
            
            # 执行智谱AI搜索
            search_response = self.zhipu_client.search_entity(label)
            
            if not search_response.success:
                # 搜索失败，写入错误信息
                error_msg = search_response.error or "搜索请求失败"
                self._write_failure_result(entity, error_msg, label)
                return True
            
            if search_response.total_count == 0:
                # 无搜索结果
                self._write_no_results(entity, label)
                return True
            
            # 调用LLM分析搜索结果
            analysis_result = self.analyzer.analyze_search_results(entity, search_response)
            
            if analysis_result.success:
                # 分析成功，写入结果
                self._write_success_result(
                    entity, 
                    analysis_result.content, 
                    label,
                    search_response.total_count,
                    analysis_result.model_name
                )
                logger.info(f"Web搜索处理成功 label='{label}' content_len={len(analysis_result.content)}")
            else:
                # 分析失败
                error_msg = analysis_result.error or "结果分析失败"
                self._write_failure_result(entity, error_msg, label)
            
            return True
            
        except Exception as e:
            error_msg = f"Web搜索处理异常: {str(e)}"
            logger.error(f"Web搜索处理失败 label='{label}' row_id={row_id} error={error_msg}")
            self._write_failure_result(entity, error_msg, label)
            return True
    
    def is_enabled_for_entity_type(self, entity_type: str) -> bool:
        """
        检查是否为指定实体类型启用Web搜索
        
        实现三层检查机制：
        1. 全局启用检查：l3_context_interpretation.enabled
        2. 功能启用检查：web_search.enabled  
        3. 实体类型启用检查：web_search.entity_types.{type}.enabled
        
        Args:
            entity_type: 实体类型（person, organization, event等）
            
        Returns:
            bool: 是否启用
        """
        # 1. 全局启用检查
        l3_config = self.settings.get("l3_context_interpretation", {})
        if not l3_config.get("enabled", False):
            return False
        
        # 2. 功能启用检查
        if not self.web_config.get("enabled", False):
            return False
        
        # 3. 实体类型启用检查
        entity_types_config = self.web_config.get("entity_types", {})
        
        # 如果没有entity_types配置，默认启用（向后兼容）
        if not entity_types_config:
            return True
        
        # 检查特定实体类型的配置
        type_config = entity_types_config.get(entity_type, {})
        return type_config.get("enabled", False)

    def should_skip_entity(self, entity: Dict[str, Any]) -> bool:
        """
        检查是否应该跳过实体处理
        
        检查l3_web_search字段是否已存在并有执行记录。
        
        Args:
            entity: 实体信息字典
            
        Returns:
            bool: 是否应该跳过
        """
        field_name = "l3_web_search"
        
        # 检查实体字段是否存在且有成功结果
        if field_name in entity and entity[field_name] is not None:
            # 检查是否有执行时间戳（表示已完成）
            executed_meta = entity[field_name].get("meta", {})
            executed_at = executed_meta.get("executed_at")
            
            if executed_at:
                entity_label = entity.get("label", "")
                logger.info(f"实体已执行过Web搜索，跳过处理 entity={entity_label} executed_at={executed_at}")
                return True
        
        # 检查metadata中是否有异常状态记录
        metadata = entity.get("metadata", {})
        if field_name in metadata:
            executed_at = metadata[field_name].get("executed_at")
            status = metadata[field_name].get("status")
            
            if executed_at and status:
                entity_label = entity.get("label", "")
                logger.info(f"实体已执行过Web搜索（metadata记录），跳过处理 entity={entity_label} status={status} executed_at={executed_at}")
                return True
        
        return False
    
    def _write_success_result(
        self, 
        entity: Dict[str, Any], 
        content: str, 
        query: str,
        results_count: int,
        model_name: str
    ):
        """写入成功结果"""
        now = datetime.now(timezone.utc).astimezone()
        
        result = {
            "content": content,
            "meta": {
                "status": "success",
                "executed_at": now.isoformat(),
                "task_type": "web_search", 
                "search_query": query,
                "search_results_count": results_count,
                "llm_model": model_name,
                "error": None
            }
        }
        
        # 写入实体字段
        entity["l3_web_search"] = result
        
        logger.debug(f"写入Web搜索成功结果 query='{query}' content_len={len(content)}")
    
    def _write_no_results(self, entity: Dict[str, Any], query: str):
        """写入无结果情况"""
        now = datetime.now(timezone.utc).astimezone()
        
        # 根据存储规范，失败时设置主字段为null，状态信息写入metadata
        entity["l3_web_search"] = None
        
        if "metadata" not in entity:
            entity["metadata"] = {}
        
        entity["metadata"]["l3_web_search"] = {
            "status": "no_results",
            "executed_at": now.isoformat(),
            "task_type": "web_search",
            "search_query": query,
            "search_results_count": 0,
            "error": "搜索未返回相关结果"
        }
        
        logger.debug(f"写入Web搜索无结果 query='{query}'")
    
    def _write_failure_result(self, entity: Dict[str, Any], error: str, query: str):
        """写入失败结果"""
        now = datetime.now(timezone.utc).astimezone()
        
        # 根据存储规范，失败时设置主字段为null，状态信息写入metadata
        entity["l3_web_search"] = None
        
        if "metadata" not in entity:
            entity["metadata"] = {}
        
        entity["metadata"]["l3_web_search"] = {
            "status": "error",
            "executed_at": now.isoformat(),
            "task_type": "web_search",
            "search_query": query,
            "error": error
        }
        
        logger.debug(f"写入Web搜索失败结果 query='{query}' error={error}")