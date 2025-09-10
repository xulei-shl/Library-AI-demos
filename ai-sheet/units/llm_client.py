#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大模型API调用客户端
提供统一的AI接口调用功能，支持多种模型配置
"""

import json
from typing import Dict, Any, List, Optional
import time
import logging
from datetime import datetime
from openai import OpenAI
import os

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMClient:
    """大模型API调用客户端"""
    
    def __init__(self, config_manager=None, enable_param_logging=True, log_file_path=None):
        """
        初始化LLM客户端
        
        Args:
            config_manager: 配置管理器实例
            enable_param_logging: 是否启用参数日志记录到文件
            log_file_path: 日志文件路径，默认为 logs/llm_params.log
        """
        self.config_manager = config_manager
        self.default_timeout = 30
        self.max_retries = 3
        self._client_cache = {}  # 缓存OpenAI客户端实例
        self.enable_param_logging = enable_param_logging
        
        # 设置参数日志文件路径
        if log_file_path is None:
            log_file_path = os.path.join("logs", "llm_params.log")
        self.log_file_path = log_file_path
        
        # 确保日志目录存在
        if self.enable_param_logging:
            os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
    
    def _get_openai_client(self, model_config: Dict[str, str]) -> OpenAI:
        """
        获取或创建OpenAI客户端实例
        
        Args:
            model_config: 模型配置
            
        Returns:
            OpenAI: OpenAI客户端实例
        """
        api_key = model_config.get("api_key", "").strip()
        base_url = model_config.get("base_url", "").strip()
        
        # 使用API key和base_url作为缓存键
        cache_key = f"{api_key}:{base_url}"
        
        if cache_key not in self._client_cache:
            self._client_cache[cache_key] = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=self.default_timeout
            )
        
        return self._client_cache[cache_key]
    
    def _log_params_to_file(self, params_info: Dict[str, Any]):
        """
        将参数信息记录到日志文件
        
        Args:
            params_info: 参数信息字典
        """
        if not self.enable_param_logging:
            return
            
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                separator = "=" * 80
                f.write(f"\n{separator}\n")
                f.write(f"时间: {timestamp}\n")
                f.write(f"API地址: {params_info.get('base_url', 'N/A')}\n")
                f.write(f"模型名称: {params_info.get('model', 'N/A')}\n")
                f.write(f"Temperature: {params_info.get('temperature', 'N/A')}\n")
                f.write(f"Top_p: {params_info.get('top_p', 'N/A')}\n")
                f.write(f"Max_tokens: {params_info.get('max_tokens', 'N/A')}\n")
                f.write(f"消息数量: {params_info.get('message_count', 'N/A')}\n")
                
                # 记录消息内容
                messages = params_info.get('messages', [])
                for i, msg in enumerate(messages):
                    role = msg.get('role', '未知')
                    content = msg.get('content', '')
                    
                    if role == 'system':
                        f.write(f"系统提示词:\n{content}\n")
                    elif role == 'user':
                        f.write(f"用户提示词 #{i+1}:\n{content}\n")
                    elif role == 'assistant':
                        f.write(f"助手消息 #{i+1}:\n{content}\n")
                
                f.write(f"{separator}\n")
                
        except Exception as e:
            logger.warning(f"写入参数日志文件失败: {str(e)}")
        
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       model: Optional[str] = None,
                       temperature: float = 0.7,
                       top_p: Optional[float] = None,
                       max_tokens: Optional[int] = None,
                       timeout: Optional[int] = None,
                       model_config: Optional[Dict[str, str]] = None) -> str:
        """
        调用聊天完成API
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            model: 模型名称，如果不指定则使用默认模型
            temperature: 温度参数，控制随机性
            top_p: top_p参数，控制核采样
            max_tokens: 最大token数
            timeout: 请求超时时间
            model_config: 指定的模型配置，如果不提供则使用默认配置
            
        Returns:
            str: AI响应内容
            
        Raises:
            Exception: 当API调用失败时抛出异常
        """
        try:
            # 获取模型配置
            if model_config is None:
                if self.config_manager is None:
                    raise Exception("未提供配置管理器或模型配置")
                model_config = self.config_manager.get_default_model()
                if model_config is None:
                    raise Exception("未找到可用的模型配置")
            
            # 验证模型配置
            api_key = model_config.get("api_key", "").strip()
            base_url = model_config.get("base_url", "").strip()
            model_id = model_config.get("model_id", "").strip()
            
            if not api_key or not base_url or not model_id:
                raise Exception("模型配置不完整，缺少必要的API信息")
            
            # 获取OpenAI客户端
            client = self._get_openai_client(model_config)
            
            # 构建请求参数
            completion_params = {
                "model": model or model_id,
                "messages": messages,
                "temperature": temperature
            }
            
            if top_p is not None:
                completion_params["top_p"] = top_p
            
            if max_tokens is not None:
                completion_params["max_tokens"] = max_tokens
            
            # 记录详细的请求参数日志
            logger.info(f"发送API请求到: {base_url}")
            logger.info(f"使用模型: {completion_params['model']}")
            
            # 详细参数日志
            logger.info("=" * 60)
            logger.info("🔍 LLM调用详细参数:")
            logger.info(f"  📡 API地址: {base_url}")
            logger.info(f"  🤖 模型名称: {completion_params['model']}")
            logger.info(f"  🌡️  Temperature: {temperature}")
            logger.info(f"  🎯 Top_p: {top_p if top_p is not None else '未设置'}")
            logger.info(f"  📝 Max_tokens: {max_tokens if max_tokens is not None else '未设置'}")
            logger.info(f"  💬 消息数量: {len(messages)}")
            
            # 显示系统提示词和用户提示词
            for i, msg in enumerate(messages):
                role = msg.get('role', '未知')
                content = msg.get('content', '')
                content_preview = content[:100] + "..." if len(content) > 100 else content
                
                if role == 'system':
                    logger.info(f"  🔧 系统提示词: {content_preview}")
                elif role == 'user':
                    logger.info(f"  👤 用户提示词 #{i+1}: {content_preview}")
                elif role == 'assistant':
                    logger.info(f"  🤖 助手消息 #{i+1}: {content_preview}")
            
            logger.info("=" * 60)
            
            # 记录参数到日志文件
            params_info = {
                'base_url': base_url,
                'model': completion_params['model'],
                'temperature': temperature,
                'top_p': top_p,
                'max_tokens': max_tokens,
                'message_count': len(messages),
                'messages': messages
            }
            self._log_params_to_file(params_info)
            
            # 调用OpenAI API（带重试机制）
            response = self._make_openai_request_with_retry(client, completion_params)
            
            # 解析响应
            content = response.choices[0].message.content
            if content is None:
                raise Exception("AI返回了空内容")
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"LLM API调用失败: {str(e)}")
            raise Exception(f"AI调用失败: {str(e)}")
    
    def _make_openai_request_with_retry(self, client: OpenAI, completion_params: Dict[str, Any]):
        """
        带重试机制的OpenAI请求发送
        
        Args:
            client: OpenAI客户端实例
            completion_params: 请求参数
            
        Returns:
            OpenAI响应对象
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                response = client.chat.completions.create(**completion_params)
                return response
                    
            except Exception as e:
                error_str = str(e)
                last_exception = e
                
                # 检查是否是速率限制错误
                if "rate limit" in error_str.lower() or "429" in error_str:
                    wait_time = 2 ** attempt  # 指数退避
                    logger.warning(f"遇到速率限制，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                
                # 检查是否是网络相关错误
                if any(keyword in error_str.lower() for keyword in ["timeout", "connection", "network"]):
                    if attempt < self.max_retries - 1:
                        logger.warning(f"网络错误，正在重试... (第{attempt + 1}次): {error_str}")
                        time.sleep(2)
                        continue
                
                # 其他错误，如果还有重试机会就继续
                if attempt < self.max_retries - 1:
                    logger.warning(f"请求失败，正在重试... (第{attempt + 1}次): {error_str}")
                    time.sleep(1)
                    continue
                    
        # 所有重试都失败了
        if last_exception:
            raise last_exception
        else:
            raise Exception("请求失败，已达到最大重试次数")
    
    def test_connection(self, model_config: Optional[Dict[str, str]] = None) -> tuple[bool, str]:
        """
        测试API连接
        
        Args:
            model_config: 模型配置，如果不提供则使用默认配置
            
        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        try:
            # 获取模型配置
            if model_config is None:
                if self.config_manager is None:
                    return False, "未提供配置管理器或模型配置"
                model_config = self.config_manager.get_default_model()
                if model_config is None:
                    return False, "未找到可用的模型配置"
            
            # 验证模型配置
            api_key = model_config.get("api_key", "").strip()
            base_url = model_config.get("base_url", "").strip()
            model_id = model_config.get("model_id", "").strip()
            
            if not api_key or not base_url or not model_id:
                return False, "模型配置不完整，缺少必要的API信息"
            
            # 获取OpenAI客户端
            client = self._get_openai_client(model_config)
            
            # 构建测试消息
            test_messages = [
                {"role": "user", "content": "Hello, this is a connection test."}
            ]
            
            # 发送测试请求
            completion_params = {
                "model": model_id,
                "messages": test_messages,
                "temperature": 0.1,
                "max_tokens": 50
            }
            
            response = client.chat.completions.create(**completion_params)
            
            if response and response.choices and response.choices[0].message.content:
                return True, "连接测试成功"
            else:
                return False, "连接测试失败：收到空响应"
                
        except Exception as e:
            return False, f"连接测试失败: {str(e)}"
    
    def get_model_info(self, model_config: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        获取模型信息
        
        Args:
            model_config: 模型配置
            
        Returns:
            Dict[str, Any]: 模型信息
        """
        try:
            if model_config is None:
                if self.config_manager is None:
                    return {"error": "未提供配置管理器或模型配置"}
                model_config = self.config_manager.get_default_model()
                if model_config is None:
                    return {"error": "未找到可用的模型配置"}
            
            # 测试连接
            is_connected, message = self.test_connection(model_config)
            
            return {
                "name": model_config.get("name", "未知"),
                "model_id": model_config.get("model_id", "未知"),
                "base_url": model_config.get("base_url", "未知"),
                "is_connected": is_connected,
                "connection_message": message,
                "last_test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            return {
                "error": f"获取模型信息失败: {str(e)}"
            }
    
    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量（粗略估算）
        
        Args:
            text: 输入文本
            
        Returns:
            int: 估算的token数量
        """
        # 简单的token估算：中文字符按1个token计算，英文单词按平均4个字符1个token计算
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        other_chars = len(text) - chinese_chars
        
        # 中文字符 + 其他字符/4
        estimated_tokens = chinese_chars + (other_chars // 4)
        
        return max(1, estimated_tokens)
    
    def validate_messages(self, messages: List[Dict[str, str]]) -> tuple[bool, str]:
        """
        验证消息格式
        
        Args:
            messages: 消息列表
            
        Returns:
            tuple[bool, str]: (是否有效, 错误信息)
        """
        try:
            if not messages:
                return False, "消息列表不能为空"
            
            for i, message in enumerate(messages):
                if not isinstance(message, dict):
                    return False, f"消息 {i} 不是字典格式"
                
                if "role" not in message:
                    return False, f"消息 {i} 缺少role字段"
                
                if "content" not in message:
                    return False, f"消息 {i} 缺少content字段"
                
                role = message["role"]
                if role not in ["system", "user", "assistant"]:
                    return False, f"消息 {i} 的role字段无效: {role}"
                
                content = message["content"]
                if not isinstance(content, str):
                    return False, f"消息 {i} 的content字段必须是字符串"
                
                if not content.strip():
                    return False, f"消息 {i} 的content字段不能为空"
            
            return True, "消息格式验证通过"
            
        except Exception as e:
            return False, f"验证消息格式时出错: {str(e)}"