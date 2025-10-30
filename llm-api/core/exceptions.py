"""
统一异常系统

定义LLM调用过程中可能出现的各种异常类型，便于错误处理和调试。
"""


class LLMError(Exception):
    """LLM调用基类异常

    所有LLM相关异常的父类。
    """
    pass


class LLMCallError(LLMError):
    """LLM调用失败异常

    当所有重试策略都失败时抛出此异常。

    Attributes:
        task_name: 任务名称
        error_history: 错误历史列表，每个元素包含尝试次数、Provider、错误类型和错误信息
        last_error: 最后一次尝试的错误信息
        provider_type: 提供商类型（text/vision）
        use_secondary: 是否使用了备用提供商
    """

    def __init__(
        self,
        task_name: str,
        error_history: list,
        last_error: str,
        provider_type: str = None,
        use_secondary: bool = False
    ):
        self.task_name = task_name
        self.error_history = error_history
        self.last_error = last_error
        self.provider_type = provider_type
        self.use_secondary = use_secondary

        error_count = len(error_history)
        super().__init__(
            f"任务 {task_name} 调用失败 (尝试{error_count}次): {last_error}"
        )

    def __str__(self) -> str:
        """格式化错误信息"""
        result = [super().__str__()]

        # 添加错误历史摘要
        if self.error_history:
            result.append("\n错误历史:")
            for i, error in enumerate(self.error_history, 1):
                result.append(
                    f"  {i}. Provider: {error.get('provider', 'N/A')}, "
                    f"尝试: {error.get('attempt', 'N/A')}, "
                    f"类型: {error.get('error_type', 'N/A')}, "
                    f"信息: {error.get('error_msg', 'N/A')[:100]}"
                )

        return "\n".join(result)

    def to_dict(self) -> dict:
        """转换为字典格式，便于日志记录和调试"""
        return {
            "task_name": self.task_name,
            "error_count": len(self.error_history),
            "last_error": self.last_error,
            "error_history": self.error_history,
            "provider_type": self.provider_type,
            "use_secondary": self.use_secondary,
        }


class ConfigurationError(LLMError):
    """配置错误

    当配置文件缺失、格式错误或配置项无效时抛出。
    """
    pass


class ProviderError(LLMError):
    """Provider错误

    当API提供商返回错误时抛出。

    Attributes:
        provider_name: 提供商名称
        status_code: HTTP状态码
        error_message: 错误消息
    """

    def __init__(self, provider_name: str, status_code: int = None, error_message: str = None):
        self.provider_name = provider_name
        self.status_code = status_code
        self.error_message = error_message

        msg = f"Provider错误: {provider_name}"
        if status_code:
            msg += f", HTTP {status_code}"
        if error_message:
            msg += f", {error_message}"

        super().__init__(msg)


class NetworkError(LLMError):
    """网络错误

    当网络连接失败、超时或DNS解析失败时抛出。

    Attributes:
        host: 目标主机
        error_type: 错误类型（connection, timeout, dns等）
        error_message: 错误消息
    """

    def __init__(self, host: str, error_type: str = None, error_message: str = None):
        self.host = host
        self.error_type = error_type
        self.error_message = error_message

        msg = f"网络错误: {host}"
        if error_type:
            msg += f", 类型: {error_type}"
        if error_message:
            msg += f", {error_message}"

        super().__init__(msg)


class RateLimitError(LLMError):
    """速率限制错误

    当API调用频率超过限制时抛出。

    Attributes:
        provider_name: 提供商名称
        retry_after: 重试等待时间（秒）
        limit_info: 速率限制信息
    """

    def __init__(
        self,
        provider_name: str,
        retry_after: int = None,
        limit_info: str = None
    ):
        self.provider_name = provider_name
        self.retry_after = retry_after
        self.limit_info = limit_info

        msg = f"速率限制: {provider_name}"
        if retry_after:
            msg += f", 请等待 {retry_after} 秒后重试"
        if limit_info:
            msg += f", {limit_info}"

        super().__init__(msg)


class AuthenticationError(LLMError):
    """认证错误

    当API密钥无效、权限不足或认证失败时抛出。

    Attributes:
        provider_name: 提供商名称
        auth_type: 认证类型（api_key, token等）
        error_message: 错误消息
    """

    def __init__(self, provider_name: str, auth_type: str = None, error_message: str = None):
        self.provider_name = provider_name
        self.auth_type = auth_type
        self.error_message = error_message

        msg = f"认证错误: {provider_name}"
        if auth_type:
            msg += f", 类型: {auth_type}"
        if error_message:
            msg += f", {error_message}"

        super().__init__(msg)


class ModelError(LLMError):
    """模型错误

    当模型不存在、参数无效或模型返回错误时抛出。

    Attributes:
        model_name: 模型名称
        error_message: 错误消息
    """

    def __init__(self, model_name: str, error_message: str = None):
        self.model_name = model_name
        self.error_message = error_message

        msg = f"模型错误: {model_name}"
        if error_message:
            msg += f", {error_message}"

        super().__init__(msg)


class PromptError(LLMError):
    """提示词错误

    当提示词加载失败、格式错误或不存在时抛出。

    Attributes:
        prompt_source: 提示词来源（文件路径、Langfuse名称等）
        prompt_type: 提示词类型（md, langfuse, dict）
        error_message: 错误消息
    """

    def __init__(self, prompt_source: str, prompt_type: str = None, error_message: str = None):
        self.prompt_source = prompt_source
        self.prompt_type = prompt_type
        self.error_message = error_message

        msg = f"提示词错误: {prompt_source}"
        if prompt_type:
            msg += f", 类型: {prompt_type}"
        if error_message:
            msg += f", {error_message}"

        super().__init__(msg)


class TimeoutError(LLMError):
    """超时错误

    当请求超时或响应时间超过限制时抛出。

    Attributes:
        timeout_seconds: 超时时间（秒）
        operation: 操作名称
        error_message: 错误消息
    """

    def __init__(self, timeout_seconds: int, operation: str = None, error_message: str = None):
        self.timeout_seconds = timeout_seconds
        self.operation = operation
        self.error_message = error_message

        msg = f"超时错误: {timeout_seconds}秒"
        if operation:
            msg += f", 操作: {operation}"
        if error_message:
            msg += f", {error_message}"

        super().__init__(msg)


class JSONParseError(LLMError):
    """JSON解析错误

    当JSON解析失败时抛出。

    Attributes:
        raw_text: 原始文本
        error_message: 错误消息
    """

    def __init__(self, raw_text: str, error_message: str = None):
        self.raw_text = raw_text
        self.error_message = error_message

        msg = "JSON解析失败"
        if error_message:
            msg += f": {error_message}"

        super().__init__(msg)