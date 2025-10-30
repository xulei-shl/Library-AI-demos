"""
统一LLM客户端

统一管理所有LLM调用功能，提供简洁易用的接口。
特性：
1. 统一配置管理
2. 智能重试机制
3. 多格式提示词支持
4. Langfuse监控集成
5. JSON智能修复
6. 流式调用支持
7. 批量调用支持
"""

import asyncio
from typing import Optional, Dict, Any, Union, List, AsyncGenerator
from pathlib import Path

from openai import OpenAI

try:
    from langfuse.openai import OpenAI as LangfuseOpenAI
    from langfuse.decorators import observe
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    observe = lambda **kwargs: lambda f: f  # 空装饰器

from core.config_loader import ConfigLoader
from core.retry_manager import RetryManager
from core.exceptions import ConfigurationError, LLMCallError, PromptError
from utils.logger import get_logger, log_function_call
from utils.json_handler import JSONHandler


class UnifiedLLMClient:
    """统一LLM客户端

    提供统一的LLM调用接口，支持多种功能和配置方式。

    使用示例:
        ```python
        client = UnifiedLLMClient()

        # 简单调用
        result = await client.call(
            task_name="fact_description",
            user_prompt="描述这张图片"
        )

        # 流式调用
        async for chunk in client.stream_call(
            task_name="fact_description",
            user_prompt="写一篇关于AI的文章"
        ):
            print(chunk, end="")

        # 批量调用
        results = await client.batch_call([
            {"task_name": "fact_description", "user_prompt": "图片1"},
            {"task_name": "fact_description", "user_prompt": "图片2"},
        ])
        ```
    """

    def __init__(self, config_path: str = "config/settings.yaml"):
        """初始化客户端

        Args:
            config_path: 配置文件路径
        """
        self.logger = get_logger(__name__)
        self.config_loader = ConfigLoader(config_path)
        self.settings = self.config_loader.load()
        self.retry_manager = RetryManager(self.settings)
        self.json_handler = JSONHandler()

        # 验证配置
        self._validate_config()

        self.logger.info("统一LLM客户端初始化成功")

    def _validate_config(self):
        """验证配置文件

        Raises:
            ConfigurationError: 配置验证失败
        """
        required_sections = ['api_providers', 'tasks']

        for section in required_sections:
            if section not in self.settings:
                raise ConfigurationError(f"配置缺少必需部分: {section}")

        # 验证任务配置
        for task_name, task_config in self.settings['tasks'].items():
            if 'provider_type' not in task_config:
                raise ConfigurationError(f"任务 {task_name} 缺少 provider_type 配置")

            if 'prompt' not in task_config:
                raise ConfigurationError(f"任务 {task_name} 缺少 prompt 配置")

            self.logger.debug(f"任务配置验证通过: {task_name}")

    @log_function_call
    async def call(
        self,
        task_name: str,
        user_prompt: Union[str, List[Dict[str, Any]]],
        **kwargs
    ) -> str:
        """统一调用接口

        Args:
            task_name: 任务名称（从配置中读取）
            user_prompt: 用户提示词（字符串或消息列表）
            **kwargs: 覆盖配置的参数

        Returns:
            LLM响应文本

        Raises:
            ConfigurationError: 任务未配置
            LLMCallError: 调用失败
        """
        self.logger.info(f"开始LLM调用 | 任务={task_name}")

        # 获取任务配置
        if task_name not in self.settings['tasks']:
            raise ConfigurationError(f"任务未配置: {task_name}")

        task_config = self.settings['tasks'][task_name].copy()

        # 合并覆盖参数
        task_config.update(kwargs)

        # 构建消息
        messages = self._build_messages(task_name, user_prompt, task_config)

        # 记录消息统计
        self.logger.info(
            f"构建消息完成 | 任务={task_name} | "
            f"消息条数={len(messages)}"
        )

        # 带重试的调用
        try:
            # 如果启用Langfuse，使用观察装饰器
            langfuse_config = task_config.get('langfuse', {})
            if langfuse_config.get('enabled', False) and LANGFUSE_AVAILABLE:
                result = await self._call_with_langfuse(task_name, messages, task_config)
            else:
                result = await self.retry_manager.call_with_retry(
                    task_name=task_name,
                    provider_type=task_config['provider_type'],
                    messages=messages
                )
        except Exception as e:
            self.logger.error(f"LLM调用失败 | 任务={task_name} | 错误={str(e)}")
            raise

        # JSON修复（如果启用）
        json_repair_config = task_config.get('json_repair', {})
        if json_repair_config.get('enabled', False):
            self.logger.info("启用JSON修复")
            parsed = self.json_handler.parse_response(
                result,
                enable_repair=True,
                strict_mode=json_repair_config.get('strict_mode', False)
            )

            if isinstance(parsed, dict):
                # 如果修复成功且是JSON对象，格式化输出
                output_format = json_repair_config.get('output_format', 'text')
                result = self.json_handler.format_output(parsed, output_format)

        self.logger.info(f"LLM调用完成 | 任务={task_name} | 响应长度={len(result)}")
        return result

    async def _call_with_langfuse(
        self,
        task_name: str,
        messages: List[Dict[str, Any]],
        task_config: Dict[str, Any]
    ) -> str:
        """使用Langfuse调用（带监控）

        Args:
            task_name: 任务名称
            messages: 消息列表
            task_config: 任务配置

        Returns:
            LLM响应文本
        """
        langfuse_config = task_config['langfuse']

        # 获取Provider信息
        provider_type = task_config['provider_type']
        provider_info = self.retry_manager._get_provider_info(provider_type, False)

        # 构建Langfuse客户端
        client = LangfuseOpenAI(
            api_key=provider_info['api_key'],
            base_url=provider_info['base_url']
        )

        # 构建额外参数
        langfuse_kwargs = {
            'temperature': task_config.get('temperature', 0.7),
            'top_p': task_config.get('top_p', 0.9),
        }

        # 添加Langfuse特有的参数
        if 'name' in langfuse_config:
            langfuse_kwargs['name'] = langfuse_config['name']
        if 'tags' in langfuse_config:
            langfuse_kwargs['tags'] = langfuse_config['tags']
        if 'metadata' in langfuse_config:
            langfuse_kwargs['metadata'] = langfuse_config['metadata']

        # 添加@observe装饰器
        @observe(name=langfuse_config.get('name', task_name))
        def _make_call():
            return client.chat.completions.create(
                model=provider_info['model'],
                messages=messages,
                **langfuse_kwargs
            )

        # 执行调用
        completion = await asyncio.to_thread(_make_call)
        return completion.choices[0].message.content

    @log_function_call
    async def stream_call(
        self,
        task_name: str,
        user_prompt: Union[str, List[Dict[str, Any]]],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式调用接口

        Args:
            task_name: 任务名称
            user_prompt: 用户提示词
            **kwargs: 覆盖参数

        Yields:
            流式响应片段

        Raises:
            ConfigurationError: 任务未配置
        """
        self.logger.info(f"开始流式调用 | 任务={task_name}")

        # 获取任务配置
        if task_name not in self.settings['tasks']:
            raise ConfigurationError(f"任务未配置: {task_name}")

        task_config = self.settings['tasks'][task_name].copy()
        task_config.update(kwargs)

        # 构建消息
        messages = self._build_messages(task_name, user_prompt, task_config)

        # 获取Provider信息
        provider_type = task_config['provider_type']
        provider_info = self.retry_manager._get_provider_info(provider_type, False)

        # 创建客户端
        client = OpenAI(
            api_key=provider_info['api_key'],
            base_url=provider_info['base_url'],
            timeout=provider_info['timeout_seconds']
        )

        # 执行流式调用
        try:
            stream = await asyncio.to_thread(
                client.chat.completions.create,
                model=provider_info['model'],
                messages=messages,
                temperature=task_config.get('temperature', 0.7),
                top_p=task_config.get('top_p', 0.9),
                stream=True
            )

            # 逐块输出
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

            self.logger.info(f"流式调用完成 | 任务={task_name}")
        except Exception as e:
            self.logger.error(f"流式调用失败 | 任务={task_name} | 错误={str(e)}")
            raise

    def _build_messages(
        self,
        task_name: str,
        user_prompt: Union[str, List[Dict[str, Any]]],
        task_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """构建消息数组

        Args:
            task_name: 任务名称
            user_prompt: 用户提示词
            task_config: 任务配置

        Returns:
            消息列表

        Raises:
            PromptError: 提示词加载失败
        """
        messages = []

        # 添加系统提示词
        try:
            system_prompt = self._load_prompt(task_config['prompt'])
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
        except Exception as e:
            raise PromptError(
                prompt_source=task_config['prompt'].get('source', task_name),
                prompt_type=task_config['prompt'].get('type', 'unknown'),
                error_message=str(e)
            )

        # 添加用户提示词
        if isinstance(user_prompt, str):
            messages.append({"role": "user", "content": user_prompt})
        elif isinstance(user_prompt, list):
            messages.extend(user_prompt)
        else:
            raise ValueError("user_prompt 必须是字符串或消息列表")

        return messages

    def _load_prompt(self, prompt_config: Dict[str, Any]) -> Optional[str]:
        """加载提示词（支持多种格式）

        Args:
            prompt_config: 提示词配置

        Returns:
            提示词内容

        Raises:
            PromptError: 提示词加载失败
        """
        prompt_type = prompt_config['type']

        if prompt_type == 'md':
            # 从.md文件加载
            prompt_path = Path(prompt_config['source'])
            if not prompt_path.exists():
                raise PromptError(
                    prompt_source=str(prompt_path),
                    prompt_type='md',
                    error_message="文件不存在"
                )

            try:
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                raise PromptError(
                    prompt_source=str(prompt_path),
                    prompt_type='md',
                    error_message=str(e)
                )

        elif prompt_type == 'langfuse':
            # 从Langfuse加载
            if not LANGFUSE_AVAILABLE:
                raise PromptError(
                    prompt_source="langfuse",
                    prompt_type='langfuse',
                    error_message="Langfuse未安装"
                )

            langfuse_name = prompt_config.get('langfuse_name')

            try:
                from langfuse import Langfuse
                langfuse = Langfuse()
                prompt = langfuse.get_prompt(langfuse_name)
                self.logger.info(f"从Langfuse加载提示词: {langfuse_name}")
                return prompt.compile()
            except Exception as e:
                raise PromptError(
                    prompt_source=langfuse_name or "unknown",
                    prompt_type='langfuse',
                    error_message=str(e)
                )

        elif prompt_type == 'dict':
            # 直接使用字典格式
            content = prompt_config.get('content', '')
            if isinstance(content, dict):
                return content.get('content', '')
            return content

        else:
            raise PromptError(
                prompt_source=str(prompt_config),
                prompt_type=prompt_type,
                error_message=f"未知的提示词类型: {prompt_type}"
            )

    def get_task_config(self, task_name: str) -> Dict[str, Any]:
        """获取任务配置

        Args:
            task_name: 任务名称

        Returns:
            任务配置（副本）

        Raises:
            ConfigurationError: 任务未配置
        """
        if task_name not in self.settings['tasks']:
            raise ConfigurationError(f"任务未配置: {task_name}")

        return self.settings['tasks'][task_name].copy()

    def list_tasks(self) -> List[str]:
        """列出所有任务名称"""
        return list(self.settings.get('tasks', {}).keys())

    def reload_config(self):
        """重新加载配置"""
        self.config_loader.reload()
        self.settings = self.config_loader.load()
        self.logger.info("配置重新加载完成")

    async def batch_call(
        self,
        requests: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[Optional[str]]:
        """批量调用

        Args:
            requests: 请求列表 [{'task_name': str, 'user_prompt': str}, ...]
            max_concurrent: 最大并发数

        Returns:
            响应列表
        """
        self.logger.info(f"开始批量调用 | 请求数={len(requests)} | 并发数={max_concurrent}")

        # 转换请求格式
        retry_requests = []
        for req in requests:
            retry_requests.append({
                'task_name': req['task_name'],
                'provider_type': self.settings['tasks'][req['task_name']]['provider_type'],
                'messages': self._build_messages(
                    req['task_name'],
                    req['user_prompt'],
                    self.settings['tasks'][req['task_name']]
                )
            })

        results = await self.retry_manager.batch_call_with_retry(
            retry_requests,
            max_concurrent=max_concurrent
        )

        # JSON修复
        repaired_results = []
        for i, result in enumerate(results):
            if result is None or isinstance(result, Exception):
                repaired_results.append(None)
                continue

            task_name = requests[i]['task_name']
            json_repair_config = self.settings['tasks'][task_name].get('json_repair', {})

            if json_repair_config.get('enabled', False):
                parsed = self.json_handler.parse_response(
                    result,
                    enable_repair=True,
                    strict_mode=json_repair_config.get('strict_mode', False)
                )

                if isinstance(parsed, dict):
                    output_format = json_repair_config.get('output_format', 'text')
                    repaired_results.append(
                        self.json_handler.format_output(parsed, output_format)
                    )
                else:
                    repaired_results.append(result)
            else:
                repaired_results.append(result)

        return repaired_results

    async def close(self):
        """关闭客户端（清理资源）"""
        # 目前OpenAI客户端不需要显式关闭
        # 保留此方法以便未来扩展
        pass