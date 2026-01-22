"""LLM 客户端。"""

from __future__ import annotations

import copy
import os
import re
from contextlib import contextmanager, nullcontext
from typing import Any, Callable, Dict, List, Union

from src.utils.logger import get_logger

from .config_loader import ConfigLoader
from .exceptions import ConfigurationError
from .json_utils import JSONHandler
from .prompt_loader import PromptLoader
from .retry import RetryManager

try:
    from openai import OpenAI
except Exception as exc:  # pragma: no cover - 运行环境问题
    OpenAI = None  # type: ignore
    _OPENAI_IMPORT_ERROR = exc
else:  # pragma: no cover - import 成功即可跳过
    _OPENAI_IMPORT_ERROR = None

# Langfuse 相关依赖是可选的，容错处理
LANGFUSE_IMPORT_ERRORS: Dict[str, Exception] = {}

try:
    from langfuse.openai import OpenAI as LangfuseOpenAI
except Exception as exc:  # pragma: no cover - 可选依赖
    LangfuseOpenAI = None  # type: ignore
    LANGFUSE_IMPORT_ERRORS["openai"] = exc


def _import_observe():
    try:
        from langfuse import observe  # type: ignore

        return observe
    except Exception as exc_primary:  # pragma: no cover - 可选依赖
        try:
            from langfuse.decorators import observe  # type: ignore

            return observe
        except Exception as exc_fallback:  # pragma: no cover - 可选依赖
            LANGFUSE_IMPORT_ERRORS["observe"] = exc_primary
            LANGFUSE_IMPORT_ERRORS.setdefault("observe_fallback", exc_fallback)
            return None


def _import_propagate():
    try:
        from langfuse import propagate_attributes  # type: ignore

        return propagate_attributes
    except Exception as exc:  # pragma: no cover - 可选依赖
        LANGFUSE_IMPORT_ERRORS["propagate_attributes"] = exc

        @contextmanager
        def _noop_propagate(**_kwargs):
            yield

        return _noop_propagate


observe = _import_observe()
propagate_attributes = _import_propagate()
LANGFUSE_AVAILABLE = LangfuseOpenAI is not None and observe is not None

Message = Dict[str, Any]


class UnifiedLLMClient:
    """读取配置、组织提示词、应用重试并调用 Provider。"""

    def __init__(self, config_path: str = "config/llm.yaml", env_file: str | None = "config/.env"):
        if OpenAI is None:
            raise ConfigurationError(f"openai 库未安装: {_OPENAI_IMPORT_ERROR}")

        self.logger = get_logger(__name__)
        self.config_loader = ConfigLoader(config_path, env_file=env_file)
        self.settings = self.config_loader.load()
        self._apply_langfuse_env(self.settings.get("langfuse", {}))
        self.retry_manager = RetryManager(self.settings)
        self.prompt_loader = PromptLoader()
        self.json_handler = JSONHandler()
        self._client_cache: Dict[str, Any] = {}

    def call(self, task_name: str, user_prompt: Union[str, List[Message]], **overrides: Any) -> Any:
        """同步调用统一入口。"""
        task_config = self.get_task_config(task_name)
        task_config.update(overrides)
        response_handler: Callable[[str], Any] | None = task_config.pop("response_handler", None)

        messages = self._build_messages(task_config, user_prompt)
        provider_type = task_config.get("provider_type")
        if not provider_type:
            raise ConfigurationError(f"任务 {task_name} 缺少 provider_type")

        def _request(provider):
            raw_text = self._execute_request(provider, task_config, messages)
            processed = self._post_process(raw_text, task_config)
            if response_handler:
                return response_handler(processed)
            return processed

        request_fn = self._wrap_with_observer(
            task_name,
            task_config,
            _request,
        )

        response = self.retry_manager.call_with_retry(
            task_name=task_name,
            provider_type=provider_type,
            request_fn=request_fn,
            retry_config=task_config.get("retry", {}),
        )
        return response

    def get_task_config(self, task_name: str) -> Dict[str, Any]:
        tasks = self.settings.get("tasks", {})
        if task_name not in tasks:
            raise ConfigurationError(f"任务 {task_name} 未配置")
        return copy.deepcopy(tasks[task_name])

    def list_tasks(self) -> List[str]:
        return list(self.settings.get("tasks", {}).keys())

    def reload_config(self) -> None:
        self.settings = self.config_loader.reload()
        self._apply_langfuse_env(self.settings.get("langfuse", {}))

    def _apply_langfuse_env(self, langfuse_cfg: Dict[str, Any]) -> None:
        """将 Langfuse 配置写入环境变量，便于 SDK 自动读取。"""
        if not langfuse_cfg:
            return
        env_map = {
            "host": "LANGFUSE_HOST",
            "public_key": "LANGFUSE_PUBLIC_KEY",
            "secret_key": "LANGFUSE_SECRET_KEY",
            "debug": "LANGFUSE_DEBUG",
        }
        for key, env_key in env_map.items():
            value = langfuse_cfg.get(key)
            if value is not None and os.getenv(env_key) in (None, ""):
                os.environ[env_key] = str(value)

    def _build_messages(self, task_config: Dict[str, Any], user_prompt: Union[str, List[Message]]) -> List[Message]:
        messages: List[Message] = []
        prompt_cfg = task_config.get("prompt")
        if prompt_cfg:
            system_prompt = self.prompt_loader.load(prompt_cfg)
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

        if isinstance(user_prompt, str):
            messages.append({"role": "user", "content": user_prompt})
        elif isinstance(user_prompt, list):
            messages.extend(user_prompt)
        else:
            raise ValueError("user_prompt 必须是字符串或消息列表")

        return messages

    def _wrap_with_observer(self, task_name: str, task_config: Dict[str, Any], fn):
        langfuse_cfg = task_config.get("langfuse", {})
        enabled = langfuse_cfg.get("enabled", False)
        if not enabled:
            return fn
        if not LANGFUSE_AVAILABLE:
            self.logger.warning(
                "已启用 Langfuse 但缺少依赖，跳过观测。(错误: %s)",
                self._format_langfuse_errors(),
            )
            return fn

        observe_kwargs: Dict[str, Any] = {"name": langfuse_cfg.get("name", task_name)}

        # observe 目前不直接支持 metadata/tags，使用 propagate_attributes 传递
        def wrapped(provider):
            with self._propagate_context(langfuse_cfg):
                return fn(provider)

        return self._observe_with_fallback(observe_kwargs, wrapped)

    def _observe_with_fallback(self, kwargs: Dict[str, Any], fn):
        if observe is None:  # pragma: no cover - 保护性分支
            return fn
        while True:
            try:
                return observe(**kwargs)(fn)
            except TypeError as exc:
                unexpected = self._parse_unexpected_keyword(str(exc))
                if unexpected and unexpected in kwargs:
                    removed = kwargs.pop(unexpected)
                    self.logger.warning(
                        "Langfuse observe 不支持参数 %s，已忽略 (值 %s)。错误: %s",
                        unexpected,
                        removed,
                        exc,
                    )
                    continue
                raise

    @staticmethod
    def _parse_unexpected_keyword(message: str) -> str | None:
        match = re.search(r"unexpected keyword argument '([^']+)'", message)
        if match:
            return match.group(1)
        return None

    def _is_error_response(self, text: str) -> bool:
        """检测响应是否包含错误信息"""
        if not text:
            return False
        # 常见的错误模式
        error_patterns = [
            r"\[.*Error\]:",  # [GoogleGenerativeAI Error]:
            r"Error:",
            r"\d{3}\s+(Service Unavailable|Bad Gateway|Gateway Timeout|Internal Server Error)",
            r"The model is overloaded",
            r"Rate limit",
            r"quota exceeded",
            r"authentication failed",
            r"invalid.*key",
        ]
        text_lower = text.lower()
        for pattern in error_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        # 检查是否只有错误消息，没有有效的JSON结构
        if ("error" in text_lower or "fail" in text_lower) and len(text) < 500:
            if not text.strip().startswith("{") and not text.strip().startswith("["):
                return True
        return False

    def _execute_request(self, provider_info: Dict[str, Any], task_config: Dict[str, Any], messages: List[Message]) -> str:
        client = self._get_client(provider_info, task_config)
        model = provider_info.get("model")
        if not model:
            raise ConfigurationError("模型参数缺失")

        langfuse_cfg = task_config.get("langfuse", {})
        is_langfuse_enabled = langfuse_cfg.get("enabled") and LANGFUSE_AVAILABLE

        req_kwargs = {
            "model": model,
            "messages": messages,
            "temperature": task_config.get("temperature"),
            "top_p": task_config.get("top_p"),
        }

        if is_langfuse_enabled:
            # 注意：tags/metadata/name 通过 _propagate_context 传递，不传给 API 调用
            # 只设置 langfuse_prompt 对象（这是 Langfuse SDK 支持的参数）
            prompt_cfg = task_config.get("prompt")
            if prompt_cfg:
                langfuse_prompt = self.prompt_loader.get_langfuse_prompt_object(prompt_cfg)
                if langfuse_prompt is not None:
                    req_kwargs["langfuse_prompt"] = langfuse_prompt

        # 去掉 None，避免客户端拒绝
        req_kwargs = {k: v for k, v in req_kwargs.items() if v is not None}

        response = client.chat.completions.create(**req_kwargs)
        choice = response.choices[0]
        content = getattr(choice.message, "content", None)
        if isinstance(content, list):
            text = "".join(self._resolve_content_chunk(chunk) for chunk in content)
        else:
            text = str(content or "")

        text = text.strip()

        # 检查响应是否包含错误信息（某些API提供商会将错误作为正常响应返回）
        # 这样可以触发重试逻辑
        if self._is_error_response(text):
            from .exceptions import ProviderError
            provider_name = provider_info.get("name", "unknown")
            raise ProviderError(provider_name, message=text[:200])

        return text

    def _resolve_content_chunk(self, chunk: Any) -> str:
        if isinstance(chunk, dict):
            if "text" in chunk:
                return str(chunk["text"])
            return ""
        return str(chunk or "")

    def _get_client(self, provider_info: Dict[str, Any], task_config: Dict[str, Any]):
        use_langfuse_client = (
            task_config.get("langfuse", {}).get("enabled", False)
            and LANGFUSE_AVAILABLE
            and LangfuseOpenAI is not None
        )
        cache_key = (
            provider_info.get("name"),
            provider_info.get("base_url"),
            provider_info.get("api_key"),
            use_langfuse_client,
        )
        if cache_key in self._client_cache:
            return self._client_cache[cache_key]

        client_cls = LangfuseOpenAI if use_langfuse_client else OpenAI
        init_kwargs = {
            "api_key": provider_info.get("api_key"),
            "base_url": provider_info.get("base_url"),
            "organization": provider_info.get("organization"),
            "timeout": provider_info.get("timeout_seconds"),
        }
        init_kwargs = {k: v for k, v in init_kwargs.items() if v}
        client = client_cls(**init_kwargs)
        self._client_cache[cache_key] = client
        return client

    def _post_process(self, text: str, task_config: Dict[str, Any]) -> str:
        json_cfg = task_config.get("json_repair", {})
        if not json_cfg.get("enabled"):
            return text
        parsed = self.json_handler.parse_response(
            text,
            enable_repair=True,
            strict_mode=json_cfg.get("strict_mode", False),
        )
        if parsed is None:
            return text
        return self.json_handler.format_output(parsed, json_cfg.get("output_format", "json"))

    def _propagate_context(self, langfuse_cfg: Dict[str, Any]):
        if not callable(propagate_attributes):
            return nullcontext()

        propagate_kwargs: Dict[str, Any] = {}
        if "tags" in langfuse_cfg:
            propagate_kwargs["tags"] = langfuse_cfg.get("tags")
        if "metadata" in langfuse_cfg:
            propagate_kwargs["metadata"] = langfuse_cfg.get("metadata")

        if not propagate_kwargs:
            return nullcontext()

        try:
            return propagate_attributes(**propagate_kwargs)
        except TypeError as exc:  # pragma: no cover - 参数不兼容
            self.logger.warning("Langfuse propagate_attributes 调用失败，已跳过。错误: %s", exc)
            return nullcontext()

    def _format_langfuse_errors(self) -> str:
        if not LANGFUSE_IMPORT_ERRORS:
            return "未知原因"
        parts = [f"{k}: {v}" for k, v in LANGFUSE_IMPORT_ERRORS.items()]
        return "; ".join(parts)
