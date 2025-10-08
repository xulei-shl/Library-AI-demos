import requests
import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from ...utils.logger import get_logger
from ...utils.llm_api import _resolve_env

logger = get_logger(__name__)

@dataclass
class DifyResponse:
    """Dify API 响应封装"""
    status: str  # "success" | "not_found" | "not_relevant" | "error"
    content: str = ""
    error: str = ""
    response_id: str = ""
    message_id: str = ""
    conversation_id: str = ""
    task_id: str = ""
    usage_info: Optional[Dict[str, Any]] = None
    retriever_resources: Optional[list] = None
    raw_response: Optional[Dict[str, Any]] = None

class DifyClient:
    """Dify 知识库检索客户端，基于官方示例实现"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.dify.ai/v1", rate_limit_ms: int = 1000, timeout_seconds: int = 90):
        """
        初始化 Dify 客户端
        
        Args:
            api_key: Dify API 密钥
            base_url: API 基础URL
            rate_limit_ms: 请求间隔限制（毫秒）
            timeout_seconds: 请求超时时间（秒）
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.rate_limit_ms = rate_limit_ms
        self.timeout_seconds = timeout_seconds
        self._last_request_time = 0
        
        logger.info(f"Dify客户端初始化 base_url={self.base_url} rate_limit_ms={rate_limit_ms} timeout_seconds={timeout_seconds}")
    
    def query_knowledge_base(self, 
                           label: str, 
                           entity_type: str, 
                           context_hint: str,
                           conversation_id: str = "",
                           user_id: str = "l3_rag_user") -> DifyResponse:
        """
        查询 Dify 知识库
        
        Args:
            label: 实体标签
            entity_type: 实体类型  
            context_hint: 上下文提示
            conversation_id: 对话ID（可选）
            user_id: 用户ID
            
        Returns:
            DifyResponse: 封装的响应对象
        """
        try:
            # 速率限制
            self._apply_rate_limit()
            
            # 构建查询文本：将三个字段原样传递给 Dify
            # 根据需求文档，这三个字段要原样传给dify
            query_text = f"label: {label}\ntype: {entity_type}\ncontext_hint: {context_hint}"
            
            # 构建请求体，参考官方示例
            payload = {
                "inputs": {},
                "query": query_text,
                "response_mode": "blocking",
                "conversation_id": conversation_id,
                "user": user_id,
                "auto_generate_name": True
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 记录请求日志
            logger.info(f"Dify_API_调用开始 label={label} type={entity_type} query_len={len(query_text)}")
            
            # 发起HTTP请求
            response = requests.post(
                f"{self.base_url}/chat-messages",
                headers=headers,
                data=json.dumps(payload),
                timeout=self.timeout_seconds
            )
            
            # 检查HTTP状态码
            if response.status_code == 200:
                response_data = response.json()
                parsed_response = self._parse_response(response_data)
                
                logger.info(f"Dify_API_调用成功 label={label} status={parsed_response.status} " +
                          f"content_len={len(parsed_response.content)} response_id={parsed_response.response_id}")
                return parsed_response
            else:
                return self._handle_error_response(response, label)
                
        except requests.exceptions.Timeout:
            error_msg = f"请求超时（>{self.timeout_seconds}秒）"
            logger.error(f"Dify_API_超时 label={label} error={error_msg}")
            return DifyResponse(status="error", error=error_msg)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"网络错误: {str(e)}"
            logger.error(f"Dify_API_网络错误 label={label} error={error_msg}")
            return DifyResponse(status="error", error=error_msg)
            
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.error(f"Dify_API_未知错误 label={label} error={error_msg}")
            return DifyResponse(status="error", error=error_msg)
    
    def _handle_error_response(self, response: requests.Response, label: str) -> DifyResponse:
        """处理错误响应"""
        try:
            error_data = response.json()
            error_code = error_data.get('code', 'unknown_error')
            error_message = error_data.get('message', response.text[:200])
            
            # 根据官方文档的错误码进行分类
            if error_code in ['app_unavailable', 'provider_not_initialize', 'provider_quota_exceeded', 
                            'model_currently_not_support', 'workflow_not_found']:
                status = "error"
            elif response.status_code == 404:
                status = "not_found"
            else:
                status = "error"
            
            error_msg = f"HTTP错误 status_code={response.status_code} code={error_code} message={error_message}"
            logger.error(f"Dify_API_调用失败 label={label} {error_msg}")
            
            return DifyResponse(
                status=status,
                error=error_msg
            )
            
        except json.JSONDecodeError:
            error_msg = f"HTTP错误 status_code={response.status_code} response={response.text[:200]}"
            logger.error(f"Dify_API_调用失败 label={label} {error_msg}")
            return DifyResponse(
                status="error",
                error=error_msg
            )
    
    def _parse_response(self, response_data: Dict[str, Any]) -> DifyResponse:
        """
        解析 Dify 响应并判断状态
        
        根据需求文档，需要识别四种状态：
        1. 没有检索到相关信息 -> not_found
        2. 回答不相关 -> not_relevant  
        3. 正确返回结果 -> success
        4. 未返回等各种异常错误 -> error
        """
        try:
            answer = response_data.get("answer", "").strip()
            response_id = response_data.get("id", "")
            message_id = response_data.get("message_id", "")
            conversation_id = response_data.get("conversation_id", "")
            task_id = response_data.get("task_id", "")
            
            # 提取metadata信息
            metadata = response_data.get("metadata", {})
            usage_info = metadata.get("usage")
            retriever_resources = metadata.get("retriever_resources")
            
            if not answer:
                return DifyResponse(
                    status="not_found",
                    error="Dify 返回空响应",
                    response_id=response_id,
                    message_id=message_id,
                    conversation_id=conversation_id,
                    task_id=task_id,
                    usage_info=usage_info,
                    retriever_resources=retriever_resources,
                    raw_response=response_data
                )
            
            # 检查是否为"没有检索到相关信息"的标准回复
            no_info_keywords = ["没有检索到", "未找到相关", "知识库中没有", "无法找到", "没有相关信息"]
            if any(keyword in answer for keyword in no_info_keywords):
                return DifyResponse(
                    status="not_found",
                    content=answer,
                    response_id=response_id,
                    message_id=message_id,
                    conversation_id=conversation_id,
                    task_id=task_id,
                    usage_info=usage_info,
                    retriever_resources=retriever_resources,
                    raw_response=response_data
                )
            
            # 检查是否为"回答不相关"的判断
            irrelevant_keywords = ["不相关", "无关", "不匹配", "无法确定相关性", "回答不相关"]
            if any(keyword in answer for keyword in irrelevant_keywords):
                return DifyResponse(
                    status="not_relevant", 
                    content=answer,
                    response_id=response_id,
                    message_id=message_id,
                    conversation_id=conversation_id,
                    task_id=task_id,
                    usage_info=usage_info,
                    retriever_resources=retriever_resources,
                    raw_response=response_data
                )
            
            # 其他情况视为成功检索
            return DifyResponse(
                status="success",
                content=answer,
                response_id=response_id,
                message_id=message_id,
                conversation_id=conversation_id,
                task_id=task_id,
                usage_info=usage_info,
                retriever_resources=retriever_resources,
                raw_response=response_data
            )
            
        except Exception as e:
            return DifyResponse(
                status="error",
                error=f"响应解析失败: {str(e)}",
                raw_response=response_data
            )
    
    def _apply_rate_limit(self) -> None:
        """应用速率限制"""
        if self.rate_limit_ms <= 0:
            return
            
        current_time = time.time() * 1000  # 转换为毫秒
        elapsed = current_time - self._last_request_time
        
        if elapsed < self.rate_limit_ms:
            sleep_time = (self.rate_limit_ms - elapsed) / 1000.0
            time.sleep(sleep_time)
        
        self._last_request_time = time.time() * 1000