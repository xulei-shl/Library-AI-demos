"""
增强Web检索模块

该模块为实体提供扩展的Web检索功能：
1. 使用大模型从原始label提取优化的搜索关键词
2. 用优化的关键词替换原始label进行Web搜索
3. 结果写入独立的JSON节点，保留搜索关键词信息

设计原则：
- 独立的增强Web检索处理器，不继承RAG处理器
- 复用统一的标签扩展逻辑
- 与现有Web搜索流程保持一致
- 配置驱动，支持按需启用
"""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

# 修改导入，不再继承BaseEnhancedRAGProcessor
from .base_label_enhancer import BaseLabelEnhancer
from ...utils.logger import get_logger
from .web_search_processor import WebSearchProcessor
from .zhipu_client import ZhipuClient
from .web_result_analyzer import WebResultAnalyzer

logger = get_logger(__name__)


# 修改类定义，不再继承BaseEnhancedRAGProcessor
class EnhancedWebRetrieval(BaseLabelEnhancer):
    """增强Web检索处理器（独立处理器）"""
    
    def __init__(self, settings: Dict[str, Any]):
        """
        初始化增强Web检索处理器
        
        Args:
            settings: 全局配置字典
        """
        # 调用父类初始化
        super().__init__(settings)
        
        # 初始化Web搜索相关组件
        self.web_config = self._get_web_search_config()
        self.zhipu_client = self._create_zhipu_client()
        self.analyzer = WebResultAnalyzer(settings)
        
        # 从配置中获取增强Web搜索设置
        self.enhanced_web_config = self.l3_config.get("enhanced_web_retrieval", {})
        
        logger.info("增强Web检索处理器初始化完成")
    
    def _get_web_search_config(self) -> Dict[str, Any]:
        """获取Web搜索配置"""
        return self.settings.get("l3_context_interpretation", {}).get("web_search", {})
    
    def _create_zhipu_client(self) -> Optional[ZhipuClient]:
        """
        创建智谱AI客户端
        
        Returns:
            Optional[ZhipuClient]: 智谱AI客户端实例，失败时返回None
        """
        try:
            zhipu_config = self.web_config.get("zhipu_ai", {})
            api_key = self._get_api_key(zhipu_config.get("api_key", ""))
            return ZhipuClient(api_key, zhipu_config)
        except Exception as e:
            logger.error(f"创建智谱AI客户端失败 error={str(e)}")
            return None
    
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
    
    # 新增方法：获取任务名称
    def get_task_name(self) -> str:
        """
        获取任务名称
        
        Returns:
            str: 任务名称
        """
        return "enhanced_web_retrieval"
    
    # 新增方法：检查是否启用
    def is_enabled_for_entity(self, entity_type: str) -> bool:
        """
        检查增强Web检索是否对指定实体类型启用
        
        Args:
            entity_type: 实体类型
            
        Returns:
            bool: 是否启用
        """
        # 第一层：全局启用检查
        if not self.l3_config.get("enabled", False):
            return False
        
        # 第二层：增强Web检索全局启用检查
        if not self.enhanced_web_config.get("enabled", False):
            return False
        
        # 第三层：实体类型特定检查
        entity_types_config = self.enhanced_web_config.get("entity_types", {})
        entity_config = entity_types_config.get(entity_type, {})
        
        return entity_config.get("enabled", False)
    
    def _build_user_prompt(self, original_label: str, entity_type: str, metadata: Dict[str, Any]) -> str:
        """
        构建Web搜索的用户提示词
        
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
        
        user_content = f"""请为以下实体提取1-2个核心关键词用于Web搜索：

实体标签：{original_label}
实体类型：{entity_type}
{context_info}

请只输出关键词，用空格分隔。"""
        
        return user_content
    
    # 新增方法：获取实体配置
    def _get_entity_config(self, entity_type: str) -> Dict[str, Any]:
        """
        获取实体类型配置
        
        Args:
            entity_type: 实体类型
            
        Returns:
            Dict[str, Any]: 实体类型配置
        """
        entity_types_config = self.enhanced_web_config.get("entity_types", {})
        return entity_types_config.get(entity_type, {})
    
    def process_entity(self, entity: Dict[str, Any], row_id: str, metadata: Dict[str, Any]) -> bool:
        """
        处理单个实体的增强Web检索
        
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
            
            # Step 2: 执行Web搜索
            if not self.zhipu_client:
                logger.error("无法创建智谱AI客户端")
                self._write_failure_result(entity, "智谱AI客户端创建失败", original_label, task_name, enhanced_label)
                return False
            
            # 执行智谱AI搜索
            search_response = self.zhipu_client.search_entity(enhanced_label)
            
            if not search_response.success:
                # 搜索失败，写入错误信息
                error_msg = search_response.error or "搜索请求失败"
                self._write_failure_result(entity, error_msg, original_label, task_name, enhanced_label)
                return True
            
            if search_response.total_count == 0:
                # 无搜索结果
                self._write_no_results(entity, original_label, enhanced_label, task_name)
                return True
            
            # 调用LLM分析搜索结果
            analysis_result = self.analyzer.analyze_search_results(entity, search_response)
            
            if analysis_result.success:
                # 分析成功，写入结果
                self._write_success_result_web(
                    entity, 
                    analysis_result.content, 
                    original_label,
                    enhanced_label,
                    search_response.total_count,
                    analysis_result.model_name,
                    task_name
                )
                logger.info(f"增强Web搜索处理成功 original_label={original_label} enhanced_label={enhanced_label} content_len={len(analysis_result.content)}")
            else:
                # 分析失败
                error_msg = analysis_result.error or "结果分析失败"
                self._write_failure_result(entity, error_msg, original_label, task_name, enhanced_label)
            
            return True
            
        except Exception as e:
            logger.error(f"{task_name}失败 original_label={original_label} error={str(e)}")
            self._write_failure_result(entity, f"处理异常: {str(e)}", original_label, task_name, enhanced_label)
            return False
    
    def _write_success_result_web(
        self, 
        entity: Dict[str, Any], 
        content: str, 
        original_label: str,
        enhanced_label: str,
        results_count: int,
        model_name: str,
        task_name: str
    ):
        """写入成功结果（Web搜索专用）"""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).astimezone()
        
        result_field = f"l3_{task_name}"
        
        result = {
            "content": content,
            "meta": {
                "status": "success",
                "executed_at": now.isoformat(),
                "task_type": task_name, 
                "original_label": original_label,
                "search_keyword": enhanced_label,
                "search_results_count": results_count,
                "llm_model": model_name,
                "error": None
            }
        }
        
        # 写入实体字段
        entity[result_field] = result
        
        logger.debug(f"写入增强Web搜索成功结果 original_label={original_label} enhanced_label={enhanced_label} content_len={len(content)}")
    
    def _write_no_results(self, entity: Dict[str, Any], original_label: str, enhanced_label: str, task_name: str):
        """写入无结果情况"""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).astimezone()
        
        result_field = f"l3_{task_name}"
        
        # 根据存储规范，失败时设置主字段为null，状态信息写入metadata
        entity[result_field] = None
        
        if "metadata" not in entity:
            entity["metadata"] = {}
        
        entity["metadata"][result_field] = {
            "status": "no_results",
            "executed_at": now.isoformat(),
            "task_type": task_name,
            "original_label": original_label,
            "search_keyword": enhanced_label,
            "search_results_count": 0,
            "error": "搜索未返回相关结果"
        }
        
        logger.debug(f"写入增强Web搜索无结果 original_label={original_label} enhanced_label={enhanced_label}")
    
    def _write_failure_result(self, entity: Dict[str, Any], error_msg: str, 
                             original_label: str, task_name: str, enhanced_label: Optional[str] = None):
        """
        写入失败结果到实体节点
        
        Args:
            entity: 实体节点数据
            error_msg: 错误信息
            original_label: 原始标签
            task_name: 任务名称
            enhanced_label: 增强标签（可选）
        """
        result_field = f"l3_{task_name}"
        
        # 根据存储规范，失败时设置主字段为null，状态信息写入metadata
        entity[result_field] = None
        
        if "metadata" not in entity:
            entity["metadata"] = {}
        
        entity["metadata"][result_field] = {
            "status": "error",
            "executed_at": self._get_current_time_iso(),
            "task_type": task_name,
            "original_label": original_label,
            "search_keyword": enhanced_label if enhanced_label else "",
            "error": error_msg
        }
        
        logger.debug(f"写入增强Web搜索失败结果 original_label={original_label} enhanced_label={enhanced_label} error={error_msg}")
    
    def _get_current_time_iso(self) -> str:
        """获取当前时间的ISO格式字符串"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).astimezone().isoformat()
    
    def should_skip_entity(self, entity: Dict[str, Any], task_name: str) -> bool:
        """
        检查实体是否应该跳过增强Web检索
        
        Args:
            entity: 实体节点数据
            task_name: 任务名称
            
        Returns:
            bool: 是否应该跳过
        """
        result_field = f"l3_{task_name}"
        
        # 检查实体字段是否存在且有成功结果
        if result_field in entity and entity[result_field] is not None:
            # 检查是否有执行时间戳（表示已完成）
            executed_meta = entity[result_field].get("meta", {})
            executed_at = executed_meta.get("executed_at")
            
            if executed_at:
                entity_label = entity.get("label", "")
                logger.info(f"实体已执行过{task_name}，跳过处理 entity={entity_label} executed_at={executed_at}")
                return True
        
        # 检查metadata中是否有异常状态记录
        metadata = entity.get("metadata", {})
        if result_field in metadata:
            executed_at = metadata[result_field].get("executed_at")
            status = metadata[result_field].get("status")
            
            if executed_at and status:
                entity_label = entity.get("label", "")
                logger.info(f"实体已执行过{task_name}（metadata记录），跳过处理 entity={entity_label} status={status} executed_at={executed_at}")
                return True
        
        return False