#!/usr/bin/env python3
"""
Dify 增强客户端

使用装饰器模式包装原始DifyClient，增加超时恢复功能。
当blocking模式遇到超时时，自动尝试通过会话历史恢复响应。
"""

import time
import requests
from typing import Dict, Any, Optional

from .dify_client import DifyClient, DifyResponse
from .dify_timeout_recovery import DifyTimeoutRecovery, RecoveryConfig
from ...utils.logger import get_logger

logger = get_logger(__name__)

class DifyEnhancedClient:
    """Dify 增强客户端，支持超时恢复机制"""
    
    def __init__(self, 
                 api_key: str, 
                 base_url: str = "https://api.dify.ai/v1", 
                 rate_limit_ms: int = 1000, 
                 timeout_seconds: int = 90,
                 recovery_config: Optional[RecoveryConfig] = None):
        """
        初始化增强客户端
        
        Args:
            api_key: Dify API 密钥
            base_url: API 基础URL
            rate_limit_ms: 请求间隔限制（毫秒）
            timeout_seconds: 请求超时时间（秒）
            recovery_config: 超时恢复配置
        """
        # 创建原始客户端
        self._original_client = DifyClient(api_key, base_url, rate_limit_ms, timeout_seconds)
        
        # 创建恢复处理器
        self._recovery_handler = DifyTimeoutRecovery(api_key, base_url)
        
        # 设置恢复配置
        self._recovery_config = recovery_config or RecoveryConfig()
        
        logger.info(f"Dify增强客户端初始化 recovery_enabled={self._recovery_config.enabled} " +
                   f"max_attempts={self._recovery_config.max_attempts} " +
                   f"delay_seconds={self._recovery_config.delay_seconds}")
    
    def query_knowledge_base(self, 
                           label: str, 
                           entity_type: str, 
                           context_hint: str,
                           conversation_id: str = "",
                           user_id: Optional[str] = None) -> DifyResponse:
        """
        查询 Dify 知识库（增强版）
        
        Args:
            label: 实体标签
            entity_type: 实体类型  
            context_hint: 上下文提示
            conversation_id: 对话ID（可选）
            user_id: 用户ID（可选，未提供时自动生成唯一ID）
            
        Returns:
            DifyResponse: 封装的响应对象
        """
        # 生成唯一用户ID（基于时间戳）
        if user_id is None:
            user_id = f"l3_rag_user_{int(time.time() * 1000)}"
            
        logger.info(f"增强客户端查询开始 label={label} type={entity_type} user_id={user_id}")
        
        # 记录请求开始时间
        request_start_time = time.time()
        
        try:
            # 调用原始客户端
            response = self._original_client.query_knowledge_base(
                label=label,
                entity_type=entity_type,
                context_hint=context_hint,
                conversation_id=conversation_id,
                user_id=user_id
            )
            
            # 正常情况直接返回
            if response.status != "error":
                logger.info(f"查询正常完成 status={response.status} user_id={user_id}")
                return response
                
            # 检查是否为超时错误
            if self._is_timeout_error(response.error):
                logger.warning(f"检测到超时错误，尝试恢复 user_id={user_id} error={response.error}")
                
                # 尝试超时恢复
                recovered_response = self._attempt_timeout_recovery(
                    user_id=user_id,
                    label=label,
                    entity_type=entity_type,
                    context_hint=context_hint,
                    conversation_id=response.conversation_id or conversation_id,
                    request_start_time=request_start_time
                )
                
                if recovered_response:
                    return recovered_response
                else:
                    # 恢复失败，返回特殊状态
                    return DifyResponse(
                        status="timeout_failed",
                        error=f"超时且恢复失败: {response.error}",
                        conversation_id=response.conversation_id,
                        raw_response=response.raw_response
                    )
            else:
                # 非超时错误，直接返回原始错误
                return response
                
        except Exception as e:
            error_msg = f"增强客户端异常: {str(e)}"
            logger.error(f"增强客户端查询异常 label={label} user_id={user_id} error={error_msg}")
            return DifyResponse(status="error", error=error_msg)
    
    def _is_timeout_error(self, error_msg: str) -> bool:
        """
        判断是否为超时错误
        
        Args:
            error_msg: 错误消息
            
        Returns:
            bool: 是否为超时错误
        """
        if not error_msg:
            return False
            
        timeout_indicators = [
            "请求超时", "timeout", "超时", "timed out", 
            "connection timeout", "read timeout"
        ]
        
        error_lower = error_msg.lower()
        return any(indicator in error_lower for indicator in timeout_indicators)
    
    def _attempt_timeout_recovery(self,
                                 user_id: str,
                                 label: str,
                                 entity_type: str,
                                 context_hint: str,
                                 conversation_id: str,
                                 request_start_time: float) -> Optional[DifyResponse]:
        """
        尝试超时恢复
        
        Args:
            user_id: 用户ID
            label: 实体标签
            entity_type: 实体类型
            context_hint: 上下文提示
            conversation_id: 会话ID
            request_start_time: 请求开始时间
            
        Returns:
            Optional[DifyResponse]: 恢复的响应，失败时返回None
        """
        try:
            # 构建原始查询内容用于匹配
            original_query = f"label: {label}\ntype: {entity_type}\ncontext_hint: {context_hint}"
            
            # 调用恢复处理器
            recovered_data = self._recovery_handler.attempt_recovery(
                user_id=user_id,
                original_query=original_query,
                conversation_id=conversation_id,
                config=self._recovery_config,
                request_start_time=request_start_time
            )
            
            if recovered_data:
                # 解析恢复的数据为DifyResponse
                parsed_response = self._original_client._parse_response(recovered_data)
                
                # 修改状态为恢复成功
                parsed_response.status = "timeout_recovered"
                
                logger.info(f"超时恢复成功 label={label} user_id={user_id} " +
                          f"content_len={len(parsed_response.content)}")
                
                return parsed_response
            else:
                logger.warning(f"超时恢复失败 label={label} user_id={user_id}")
                return None
                
        except Exception as e:
            logger.error(f"超时恢复异常 label={label} user_id={user_id} error={str(e)}")
            return None
    
    # 代理其他方法到原始客户端
    def _apply_rate_limit(self):
        """应用速率限制"""
        return self._original_client._apply_rate_limit()
    
    @property
    def api_key(self):
        """API密钥"""
        return self._original_client.api_key
    
    @property 
    def base_url(self):
        """基础URL"""
        return self._original_client.base_url
    
    @property
    def timeout_seconds(self):
        """超时秒数"""
        return self._original_client.timeout_seconds