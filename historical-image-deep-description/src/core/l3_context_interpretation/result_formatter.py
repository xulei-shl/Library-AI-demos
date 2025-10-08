from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .dify_client import DifyResponse
from ...utils.logger import get_logger

logger = get_logger(__name__)

class ResultFormatter:
    """结果格式化器，将 Dify 响应转换为标准存储格式"""
    
    def __init__(self):
        logger.debug("ResultFormatter初始化完成")
    
    def format_rag_result(self, dify_response: DifyResponse, task_name: str) -> Dict[str, Any]:
        """
        将 Dify 响应格式化为存储结构
        
        参考 L2 阶段的存储格式，保持一致性
        
        Args:
            dify_response: Dify API响应对象
            task_name: 任务名称
            
        Returns:
            Dict[str, Any]: 格式化的结果字典
        """
        now = datetime.now(timezone.utc).astimezone()
        
        # 根据不同状态生成相应的存储结构
        if dify_response.status in ["success", "timeout_recovered"]:
            result = {
                "content": dify_response.content,
                "status": "success",
                "meta": {
                    "executed_at": now.isoformat(),
                    "task_type": task_name,
                    "dify_response_id": dify_response.response_id,
                    "error": None
                }
            }
            logger.debug(f"格式化成功结果 task={task_name} content_len={len(dify_response.content)}")
            
        elif dify_response.status == "not_found":
            result = {
                "content": None,
                "status": "not_found", 
                "meta": {
                    "executed_at": now.isoformat(),
                    "task_type": task_name,
                    "dify_response_id": dify_response.response_id,
                    "error": "知识库中没有检索到相关信息"
                }
            }
            logger.debug(f"格式化未找到结果 task={task_name}")
            
        elif dify_response.status == "not_relevant":
            result = {
                "content": dify_response.content,
                "status": "not_relevant",
                "meta": {
                    "executed_at": now.isoformat(), 
                    "task_type": task_name,
                    "dify_response_id": dify_response.response_id,
                    "error": "大模型判断回答与实体不相关"
                }
            }
            logger.debug(f"格式化不相关结果 task={task_name} content_len={len(dify_response.content)}")
            
        else:  # error
            result = {
                "content": None,
                "status": "error",
                "meta": {
                    "executed_at": now.isoformat(),
                    "task_type": task_name,
                    "dify_response_id": dify_response.response_id,
                    "error": dify_response.error
                }
            }
            logger.debug(f"格式化错误结果 task={task_name} error={dify_response.error}")
        
        return result
    
    def update_entity_with_rag_result(self, entity: Dict[str, Any], result: Dict[str, Any], task_name: str) -> None:
        """
        将 RAG 结果更新到实体节点
        
        遵循L2阶段的异常处理模式：
        - 成功时：写入 l3_rag_{task_name} 字段
        - 失败时：设置 l3_rag_{task_name} 为 null，异常信息写入 metadata.l3_rag_{task_name}
        
        Args:
            entity: 实体节点数据（会被直接修改）
            result: 格式化的结果数据
            task_name: 任务名称
        """
        field_name = f"l3_rag_{task_name}"
        status = result.get('status')
        
        if status == 'success':
            # 成功情况：写入实体字段
            entity[field_name] = {
                "content": result.get('content'),
                "meta": result.get('meta')
            }
            logger.debug(f"实体RAG结果写入成功 field_name={field_name} status={status}")
        else:
            # 失败情况：设置实体字段为null，异常信息写入metadata
            entity[field_name] = None
            
            # 确保metadata结构存在
            if "metadata" not in entity:
                entity["metadata"] = {}
            
            # 写入异常信息到metadata
            entity["metadata"][field_name] = {
                "executed_at": result.get('meta', {}).get('executed_at'),
                "status": status,
                "error": result.get('meta', {}).get('error'),
                "task_type": result.get('meta', {}).get('task_type'),
                "dify_response_id": result.get('meta', {}).get('dify_response_id')
            }
            
            logger.debug(f"实体RAG异常信息写入metadata field_name={field_name} status={status} error={result.get('meta', {}).get('error')}")
    
    def _generate_metadata(self, status: str, task_name: str, response_id: str = "", error: Optional[str] = None) -> Dict[str, Any]:
        """
        生成标准的元数据结构
        
        Args:
            status: 执行状态
            task_name: 任务名称
            response_id: Dify响应ID
            error: 错误信息（可选）
            
        Returns:
            Dict[str, Any]: 元数据字典
        """
        now = datetime.now(timezone.utc).astimezone()
        
        return {
            "executed_at": now.isoformat(),
            "task_type": task_name,
            "dify_response_id": response_id,
            "error": error
        }