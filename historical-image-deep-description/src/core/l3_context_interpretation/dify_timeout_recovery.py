#!/usr/bin/env python3
"""
Dify 超时恢复模块

当blocking模式因Cloudflare 100秒限制而超时时，通过获取会话历史消息来恢复实际的回答结果。
基于时间窗口、用户ID等维度匹配正确的响应消息。
"""

import requests
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone

from ...utils.logger import get_logger

logger = get_logger(__name__)

@dataclass 
class RecoveryConfig:
    """超时恢复配置"""
    enabled: bool = True
    max_attempts: int = 3
    delay_seconds: int = 10
    match_time_window: int = 120  # 消息匹配时间窗口（秒）

@dataclass
class ConversationMessage:
    """会话消息数据结构"""
    id: str
    conversation_id: str
    query: str
    answer: str
    created_at: int
    message_files: List[Dict[str, Any]]
    retriever_resources: List[Dict[str, Any]]

class DifyTimeoutRecovery:
    """Dify 超时恢复处理器"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.dify.ai/v1"):
        """
        初始化超时恢复处理器
        
        Args:
            api_key: Dify API 密钥
            base_url: API 基础URL
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        
        logger.info(f"Dify超时恢复处理器初始化 base_url={self.base_url}")
    
    def attempt_recovery(self, 
                        user_id: str,
                        original_query: str,
                        conversation_id: str,
                        config: RecoveryConfig,
                        request_start_time: float) -> Optional[Dict[str, Any]]:
        """
        尝试通过会话历史恢复超时的响应
        
        Args:
            user_id: 发起请求的用户ID
            original_query: 原始查询内容
            conversation_id: 会话ID
            config: 恢复配置
            request_start_time: 原始请求开始时间（时间戳）
            
        Returns:
            Optional[Dict[str, Any]]: 恢复的响应数据，如果失败返回None
        """
        if not config.enabled:
            logger.info("超时恢复功能已禁用")
            return None
            
        logger.warning(f"🔄 开始超时恢复流程 user_id={user_id} conversation_id={conversation_id}")
        
        for attempt in range(1, config.max_attempts + 1):
            try:
                logger.info(f"⏳ 第{attempt}次恢复尝试，等待{config.delay_seconds}秒...")
                
                # 醒目的控制台提示
                print(f"\n🚨 【Dify超时恢复】第{attempt}次尝试，等待{config.delay_seconds}秒后查询结果...")
                time.sleep(config.delay_seconds)
                
                # 步骤1：获取用户的会话列表
                conversations = self._get_user_conversations(user_id)
                if not conversations:
                    logger.warning(f"第{attempt}次尝试：未获取到用户会话列表")
                    continue
                
                # 步骤2：查找匹配的会话（基于时间窗口）
                target_conversation = self._find_matching_conversation(
                    conversations, request_start_time, config.match_time_window
                )
                
                if not target_conversation:
                    logger.warning(f"第{attempt}次尝试：未找到匹配的会话")
                    continue
                
                # 步骤3：获取该会话的消息历史
                messages = self._get_conversation_messages(target_conversation["id"], user_id)
                if not messages:
                    logger.warning(f"第{attempt}次尝试：未获取到会话历史消息")
                    continue
                
                # 步骤4：查找匹配的响应消息
                matched_message = self._find_matching_response(
                    messages, original_query, request_start_time, config.match_time_window
                )
                
                if matched_message:
                    # 验证响应内容有效性
                    if self._validate_response_content(matched_message.answer):
                        logger.info(f"✅ 超时恢复成功 attempt={attempt} conversation_id={target_conversation['id']} message_id={matched_message.id}")
                        print(f"✅ 【Dify超时恢复】成功获取到响应结果！")
                        
                        # 构建标准响应格式
                        return self._build_recovered_response(matched_message)
                    else:
                        logger.warning(f"第{attempt}次尝试：响应内容无效")
                else:
                    logger.warning(f"第{attempt}次尝试：未找到匹配的响应消息")
                    
            except Exception as e:
                logger.error(f"第{attempt}次恢复尝试失败 error={str(e)}")
                
        logger.error(f"❌ 超时恢复失败，已尝试{config.max_attempts}次")
        print(f"❌ 【Dify超时恢复】尝试{config.max_attempts}次后仍未成功，放弃恢复")
        return None
    
    def _get_user_conversations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户的会话列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Dict[str, Any]]: 会话列表
        """
        try:
            url = f"{self.base_url}/conversations"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            params = {
                "user": user_id,
                "limit": 20,  # 获取最近20个会话
                "sort_by": "-updated_at"  # 按更新时间倒序
            }
            
            logger.debug(f"获取用户会话列表 user_id={user_id}")
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                conversations = data.get("data", [])
                logger.debug(f"获取到{len(conversations)}个会话")
                return conversations
            else:
                logger.error(f"获取会话列表失败 status_code={response.status_code} response={response.text[:200]}")
                return []
                
        except Exception as e:
            logger.error(f"获取会话列表异常 error={str(e)}")
            return []
    
    def _find_matching_conversation(self, 
                                   conversations: List[Dict[str, Any]],
                                   request_start_time: float,
                                   time_window: int) -> Optional[Dict[str, Any]]:
        """
        查找匹配的会话（基于时间窗口）
        
        Args:
            conversations: 会话列表
            request_start_time: 原始请求开始时间（时间戳）
            time_window: 时间窗口（秒）
            
        Returns:
            Optional[Dict[str, Any]]: 匹配的会话，未找到返回None
        """
        # 计算时间窗口范围
        window_start = request_start_time - 60  # 允许1分钟的时间偏差
        window_end = request_start_time + time_window
        
        logger.debug(f"查找匹配会话 time_window=({window_start}, {window_end})")
        
        # 按更新时间倒序查找（最新的优先）
        sorted_conversations = sorted(conversations, key=lambda c: c.get("updated_at", 0), reverse=True)
        
        for conversation in sorted_conversations:
            created_at = conversation.get("created_at", 0)
            updated_at = conversation.get("updated_at", 0)
            
            # 检查创建时间或更新时间是否在窗口内
            if (window_start <= created_at <= window_end) or (window_start <= updated_at <= window_end):
                logger.debug(f"找到匹配会话 conversation_id={conversation.get('id')} created_at={created_at} updated_at={updated_at}")
                return conversation
        
        return None
    
    def _get_conversation_messages(self, conversation_id: str, user_id: str) -> List[ConversationMessage]:
        """
        获取会话历史消息
        
        Args:
            conversation_id: 会话ID
            user_id: 用户ID
            
        Returns:
            List[ConversationMessage]: 消息列表
        """
        try:
            url = f"{self.base_url}/messages"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            params = {
                "conversation_id": conversation_id,
                "user": user_id,
                "limit": 20  # 获取最近20条消息
            }
            
            logger.debug(f"获取会话历史消息 conversation_id={conversation_id} user={user_id}")
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                messages = []
                
                for msg_data in data.get("data", []):
                    message = ConversationMessage(
                        id=msg_data.get("id", ""),
                        conversation_id=msg_data.get("conversation_id", ""),
                        query=msg_data.get("query", ""),
                        answer=msg_data.get("answer", ""),
                        created_at=msg_data.get("created_at", 0),
                        message_files=msg_data.get("message_files", []),
                        retriever_resources=msg_data.get("retriever_resources", [])
                    )
                    messages.append(message)
                
                logger.debug(f"获取到{len(messages)}条历史消息")
                return messages
            else:
                logger.error(f"获取会话历史失败 status_code={response.status_code} response={response.text[:200]}")
                return []
                
        except Exception as e:
            logger.error(f"获取会话历史异常 error={str(e)}")
            return []
    
    def _find_matching_response(self, 
                               messages: List[ConversationMessage],
                               original_query: str,
                               request_start_time: float,
                               time_window: int) -> Optional[ConversationMessage]:
        """
        查找匹配的响应消息
        
        Args:
            messages: 历史消息列表
            original_query: 原始查询内容
            request_start_time: 原始请求开始时间（时间戳）
            time_window: 时间窗口（秒）
            
        Returns:
            Optional[ConversationMessage]: 匹配的消息，未找到返回None
        """
        # 计算时间窗口范围
        window_start = request_start_time - 60  # 允许1分钟的时间偏差
        window_end = request_start_time + time_window
        
        logger.debug(f"查找匹配消息 time_window=({window_start}, {window_end}) query_len={len(original_query)}")
        
        # 按创建时间倒序查找（最新的优先）
        sorted_messages = sorted(messages, key=lambda m: m.created_at, reverse=True)
        
        for message in sorted_messages:
            # 时间窗口过滤
            if not (window_start <= message.created_at <= window_end):
                continue
                
            # 查询内容相似性匹配
            if self._is_query_similar(message.query, original_query):
                logger.debug(f"找到匹配消息 message_id={message.id} created_at={message.created_at}")
                return message
        
        return None
    
    def _is_query_similar(self, msg_query: str, original_query: str) -> bool:
        """
        判断查询内容是否相似
        
        Args:
            msg_query: 消息中的查询内容
            original_query: 原始查询内容
            
        Returns:
            bool: 是否相似
        """
        if not msg_query or not original_query:
            return False
            
        # 提取关键信息进行匹配
        # L3的查询格式：label: xxx\ntype: xxx\ncontext_hint: xxx
        
        def extract_label_from_query(query: str) -> str:
            """从查询中提取label字段"""
            lines = query.split('\n')
            for line in lines:
                if line.strip().startswith('label:'):
                    return line.split(':', 1)[1].strip()
            return ""
        
        msg_label = extract_label_from_query(msg_query)
        original_label = extract_label_from_query(original_query)
        
        # 基于label进行匹配（这是最关键的标识符）
        if not msg_label or not original_label:
            return False
        return msg_label == original_label
    
    def _validate_response_content(self, answer: str) -> bool:
        """
        验证响应内容的有效性
        
        Args:
            answer: 响应内容
            
        Returns:
            bool: 内容是否有效
        """
        if not answer or not answer.strip():
            return False
            
        # 检查是否为错误响应
        error_indicators = [
            "请求失败", "系统错误", "服务不可用", "超时", "网络错误",
            "request failed", "system error", "service unavailable"
        ]
        
        answer_lower = answer.lower()
        for indicator in error_indicators:
            if indicator in answer_lower:
                return False
        
        # 检查最小长度要求
        return len(answer.strip()) >= 10
    
    def _build_recovered_response(self, message: ConversationMessage) -> Dict[str, Any]:
        """
        构建恢复的响应数据
        
        Args:
            message: 匹配的消息
            
        Returns:
            Dict[str, Any]: 标准响应格式
        """
        return {
            "event": "message",
            "id": message.id,
            "message_id": message.id,
            "conversation_id": message.conversation_id,
            "answer": message.answer,
            "metadata": {
                "retriever_resources": message.retriever_resources
            },
            "created_at": message.created_at,
            "_recovery_info": {
                "recovered": True,
                "recovery_time": int(time.time()),
                "method": "conversation_history"
            }
        }