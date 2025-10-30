"""
智能重试管理器

提供三层重试策略：
1. 同Provider内重试：指数退避 + 随机抖动
2. 切换备用Provider：指数退避重试
3. 最终失败：记录详细日志并抛出异常

错误处理策略：
- Langfuse平台故障：直接切换Provider
- API调用失败：先重试，再切换
- 网络超时：指数退避重试
- 速率限制：等待后重试
"""

import asyncio
import time
import random
from typing import Optional, Dict, Any, Tuple
from enum import Enum
from openai import OpenAI

from core.exceptions import (
    LLMCallError,
    ProviderError,
    NetworkError,
    RateLimitError,
    AuthenticationError,
    ModelError,
    TimeoutError
)
from utils.logger import get_logger


class ErrorType(Enum):
    """错误类型枚举"""
    NETWORK = "network"           # 网络错误
    TIMEOUT = "timeout"           # 超时错误
    API_ERROR = "api_error"       # API返回错误
    RATE_LIMIT = "rate_limit"     # 速率限制
    PROVIDER_DOWN = "provider_down"  # Provider服务不可用
    AUTH_ERROR = "auth_error"     # 认证错误
    MODEL_ERROR = "model_error"   # 模型错误
    UNKNOWN = "unknown"           # 未知错误


class RetryManager:
    """智能重试管理器

    负责管理LLM调用的重试逻辑，包括：
    1. 指数退避算法
    2. 随机抖动
    3. Provider切换
    4. 错误分类和策略选择
    """

    def __init__(self, settings: Dict[str, Any]):
        """初始化重试管理器

        Args:
            settings: 完整配置字典
        """
        self.settings = settings
        self.logger = get_logger(__name__)
        self.retry_policy = settings.get("retry_policy", {})

    async def call_with_retry(
        self,
        task_name: str,
        provider_type: str,
        messages: list,
        **kwargs
    ) -> str:
        """带重试的LLM调用

        Args:
            task_name: 任务名称
            provider_type: Provider类型（text/vision）
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            LLM响应文本

        Raises:
            LLMCallError: 所有重试都失败
        """
        task_config = self.settings['tasks'][task_name]
        retry_config = task_config.get('retry', {})

        # 重试参数
        max_retries = retry_config.get('max_retries', 3)
        base_delay = retry_config.get('base_delay', 1)
        max_delay = retry_config.get('max_delay', 60)
        enable_provider_switch = retry_config.get('enable_provider_switch', True)
        jitter = self.retry_policy.get('jitter', True)

        last_error = None
        error_history = []  # 错误历史

        # 遍历主备Provider
        for use_secondary in [False, True]:
            if use_secondary and not enable_provider_switch:
                break

            provider_info = self._get_provider_info(provider_type, use_secondary)
            provider_name = provider_info['name']

            self.logger.info(
                f"开始调用Provider | 任务={task_name} | "
                f"Provider={provider_name} | "
                f"类型={'备用' if use_secondary else '主'}"
            )

            # Provider内重试
            for attempt in range(1, max_retries + 1):
                try:
                    # 记录重试信息
                    self.logger.info(
                        f"尝试调用 | 任务={task_name} | "
                        f"Provider={provider_name} | "
                        f"尝试={attempt}/{max_retries}"
                    )

                    # 执行调用
                    result = await self._call_provider(
                        provider_info,
                        messages,
                        task_config,
                        **kwargs
                    )

                    # 成功记录
                    self.logger.info(
                        f"调用成功 | 任务={task_name} | "
                        f"Provider={provider_name} | "
                        f"尝试={attempt}/{max_retries} | "
                        f"响应长度={len(result)}"
                    )
                    return result

                except Exception as e:
                    last_error = e
                    error_type = self._classify_error(e)
                    error_history.append({
                        'attempt': attempt,
                        'provider': provider_name,
                        'error_type': error_type.value,
                        'error_msg': str(e)
                    })

                    # 记录错误信息
                    self.logger.warning(
                        f"调用失败 | 任务={task_name} | "
                        f"Provider={provider_name} | "
                        f"尝试={attempt}/{max_retries} | "
                        f"错误类型={error_type.value} | "
                        f"错误信息={str(e)[:200]}"
                    )

                    # 判断是否需要切换Provider
                    if use_secondary == False and enable_provider_switch and attempt == max_retries:
                        self.logger.info(
                            f"主Provider失败，切换到备用Provider | 任务={task_name}"
                        )
                        break  # 切换到备用Provider

                    # 计算指数退避延迟
                    if attempt < max_retries:
                        delay = self._calculate_delay(attempt, base_delay, max_delay, jitter)
                        self.logger.info(
                            f"等待{delay:.1f}秒后进行第{attempt + 1}次重试 | "
                            f"任务={task_name}"
                        )
                        await asyncio.sleep(delay)

        # 所有尝试都失败
        error_summary = self._format_error_history(error_history)
        self.logger.error(
            f"所有重试失败 | 任务={task_name} | "
            f"错误历史={error_summary}"
        )
        raise LLMCallError(
            task_name=task_name,
            error_history=error_history,
            last_error=str(last_error),
            provider_type=provider_type,
            use_secondary=True  # 最后一次尝试使用了备用Provider
        )

    def _get_provider_info(self, provider_type: str, use_secondary: bool) -> Dict[str, Any]:
        """获取Provider信息

        Args:
            provider_type: Provider类型（text/vision）
            use_secondary: 是否使用备用Provider

        Returns:
            Provider配置信息
        """
        provider_key = "secondary" if use_secondary else "primary"
        provider_config = self.settings['api_providers'][provider_type][provider_key]

        return {
            'name': provider_config.get('name', f'{provider_type}_{provider_key}'),
            'base_url': provider_config['base_url'],
            'api_key': provider_config['api_key'],
            'model': provider_config['model'],
            'timeout_seconds': provider_config.get('timeout_seconds', 60),
        }

    async def _call_provider(
        self,
        provider_info: Dict[str, Any],
        messages: list,
        task_config: Dict[str, Any],
        **kwargs
    ) -> str:
        """调用Provider

        Args:
            provider_info: Provider信息
            messages: 消息列表
            task_config: 任务配置
            **kwargs: 额外参数

        Returns:
            LLM响应文本

        Raises:
            ProviderError: Provider返回错误
            NetworkError: 网络错误
            AuthenticationError: 认证错误
            RateLimitError: 速率限制
            TimeoutError: 超时错误
        """
        # 创建客户端
        client = OpenAI(
            api_key=provider_info['api_key'],
            base_url=provider_info['base_url'],
            timeout=provider_info['timeout_seconds'],
            max_retries=0  # 重试由RetryManager处理
        )

        # 构建请求参数
        request_params = {
            'model': provider_info['model'],
            'messages': messages,
            'temperature': task_config.get('temperature', 0.7),
            'top_p': task_config.get('top_p', 0.9),
        }

        # 合并额外参数
        request_params.update(kwargs)

        # 执行调用
        try:
            response = await asyncio.to_thread(
                client.chat.completions.create,
                **request_params
            )
            return response.choices[0].message.content
        except Exception as e:
            # 根据异常类型转换为自定义异常
            error_type = self._classify_error(e)

            if error_type == ErrorType.AUTH_ERROR:
                raise AuthenticationError(
                    provider_name=provider_info['name'],
                    error_message=str(e)
                )
            elif error_type == ErrorType.RATE_LIMIT:
                raise RateLimitError(
                    provider_name=provider_info['name'],
                    error_message=str(e)
                )
            elif error_type == ErrorType.TIMEOUT:
                raise TimeoutError(
                    timeout_seconds=provider_info['timeout_seconds'],
                    operation="LLM API调用",
                    error_message=str(e)
                )
            elif error_type in (ErrorType.NETWORK, ErrorType.PROVIDER_DOWN):
                raise NetworkError(
                    host=provider_info['base_url'],
                    error_type=error_type.value,
                    error_message=str(e)
                )
            elif error_type == ErrorType.MODEL_ERROR:
                raise ModelError(
                    model_name=provider_info['model'],
                    error_message=str(e)
                )
            else:
                # 其他API错误
                raise ProviderError(
                    provider_name=provider_info['name'],
                    status_code=getattr(e, 'status_code', None),
                    error_message=str(e)
                )

    def _classify_error(self, error: Exception) -> ErrorType:
        """分类错误类型

        根据错误信息、类型和异常类型进行智能分类。

        Args:
            error: 异常对象

        Returns:
            错误类型
        """
        error_msg = str(error).lower()
        error_type = type(error).__name__

        # 认证错误
        if isinstance(error, (ValueError, Exception)) and (
            "401" in error_msg or "403" in error_msg or
            "invalid api key" in error_msg or
            "authentication" in error_msg
        ):
            return ErrorType.AUTH_ERROR

        # 速率限制
        if isinstance(error, (ValueError, Exception)) and (
            "rate limit" in error_msg or "429" in error_msg or
            "too many requests" in error_msg
        ):
            return ErrorType.RATE_LIMIT

        # 网络错误
        if isinstance(error, (ConnectionError, OSError, Exception)) and (
            "connection" in error_msg or
            "network" in error_msg or
            "dns" in error_msg or
            "unreachable" in error_msg
        ):
            return ErrorType.NETWORK

        # 超时错误
        if isinstance(error, (TimeoutError, Exception)) and (
            "timeout" in error_msg or "timed out" in error_msg
        ):
            return ErrorType.TIMEOUT

        # Provider服务不可用
        if isinstance(error, (ValueError, Exception)) and (
            "503" in error_msg or "502" in error_msg or
            "bad gateway" in error_msg or
            "service unavailable" in error_msg or
            "unavailable" in error_msg
        ):
            return ErrorType.PROVIDER_DOWN

        # 模型错误
        if isinstance(error, (ValueError, Exception)) and (
            "model not found" in error_msg or
            "invalid model" in error_msg or
            "model does not exist" in error_msg
        ):
            return ErrorType.MODEL_ERROR

        # API错误
        if isinstance(error, (ValueError, Exception)) and (
            "error" in error_msg and
            any(code in error_msg for code in ["400", "401", "403", "404", "500", "502", "503"])
        ):
            return ErrorType.API_ERROR

        # 未知错误
        return ErrorType.UNKNOWN

    def _calculate_delay(
        self,
        attempt: int,
        base_delay: float,
        max_delay: float,
        jitter: bool
    ) -> float:
        """计算延迟时间（指数退避）

        Args:
            attempt: 当前尝试次数（从1开始）
            base_delay: 基数延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            jitter: 是否启用随机抖动

        Returns:
            延迟时间（秒）
        """
        # 指数退避：1, 2, 4, 8, ...
        delay = base_delay * (2 ** (attempt - 1))
        delay = min(delay, max_delay)

        # 添加随机抖动（±10%）
        if jitter:
            jitter_range = delay * 0.1
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)

    def _format_error_history(self, error_history: list) -> str:
        """格式化错误历史

        Args:
            error_history: 错误历史列表

        Returns:
            格式化的错误历史字符串
        """
        if not error_history:
            return "无错误历史"

        summary = []
        for item in error_history:
            summary.append(
                f"{item['provider']}/尝试{item['attempt']}: "
                f"{item['error_type']} - {item['error_msg'][:100]}"
            )

        return "; ".join(summary)

    async def batch_call_with_retry(
        self,
        requests: list,
        max_concurrent: int = 5
    ) -> list:
        """批量调用带重试

        Args:
            requests: 请求列表 [{'task_name': str, 'user_prompt': str, 'messages': list}, ...]
            max_concurrent: 最大并发数

        Returns:
            响应列表，失败项为None
        """
        self.logger.info(f"开始批量调用 | 请求数={len(requests)} | 并发数={max_concurrent}")

        semaphore = asyncio.Semaphore(max_concurrent)

        async def single_call(request):
            async with semaphore:
                try:
                    return await self.call_with_retry(**request)
                except Exception as e:
                    self.logger.error(
                        f"批量调用单项失败 | 任务={request.get('task_name')} | "
                        f"错误={str(e)[:200]}"
                    )
                    return None

        tasks = [single_call(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if r is not None and not isinstance(r, Exception))
        self.logger.info(
            f"批量调用完成 | 总数={len(requests)} | 成功={success_count} | "
            f"失败={len(requests) - success_count}"
        )

        return results