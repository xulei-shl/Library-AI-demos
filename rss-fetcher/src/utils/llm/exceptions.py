"""LLM 调用相关异常定义。"""

from __future__ import annotations


class LLMError(Exception):
    """基础异常。"""


class ConfigurationError(LLMError):
    """配置错误。"""


class PromptError(LLMError):
    """提示词错误。"""

    def __init__(self, prompt_source: str, prompt_type: str | None = None, error_message: str | None = None):
        self.prompt_source = prompt_source
        self.prompt_type = prompt_type
        self.error_message = error_message or ""
        message = f"提示词错误: {prompt_source}"
        if prompt_type:
            message += f" (类型: {prompt_type})"
        if error_message:
            message += f" - {error_message}"
        super().__init__(message)


class ProviderError(LLMError):
    """模型提供方错误。"""

    def __init__(self, provider_name: str, status_code: int | None = None, message: str | None = None):
        self.provider_name = provider_name
        self.status_code = status_code
        self.message = message or ""
        text = f"Provider错误: {provider_name}"
        if status_code:
            text += f" (HTTP {status_code})"
        if message:
            text += f" - {message}"
        super().__init__(text)


class NetworkError(LLMError):
    """网络错误。"""


class TimeoutError(LLMError):
    """超时错误。"""

    def __init__(self, timeout_seconds: float, operation: str | None = None):
        self.timeout_seconds = timeout_seconds
        self.operation = operation
        text = f"超时: {timeout_seconds}s"
        if operation:
            text += f" @ {operation}"
        super().__init__(text)


class RateLimitError(LLMError):
    """限速错误。"""


class AuthenticationError(LLMError):
    """认证错误。"""


class ModelError(LLMError):
    """模型不可用。"""


class JSONParseError(LLMError):
    """JSON 解析错误。"""

    def __init__(self, raw_text: str, message: str | None = None):
        self.raw_text = raw_text
        text = "JSON解析失败"
        if message:
            text += f": {message}"
        super().__init__(text)


class LLMCallError(LLMError):
    """多次尝试后依旧失败。"""

    def __init__(self, task_name: str, error_history: list[dict], last_error: str):
        self.task_name = task_name
        self.error_history = error_history
        self.last_error = last_error
        super().__init__(f"任务 {task_name} 调用失败: {last_error}")
