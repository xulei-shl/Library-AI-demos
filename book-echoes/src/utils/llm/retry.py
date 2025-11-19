"""统一重试策略。"""

from __future__ import annotations

import random
import time
from typing import Any, Callable, Dict, Optional

from src.utils.logger import get_logger

from .exceptions import ConfigurationError, LLMCallError

logger = get_logger(__name__)


class RetryManager:
    """封装 Provider 内重试与主备切换。"""

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings

    def call_with_retry(
        self,
        task_name: str,
        provider_type: str,
        request_fn: Callable[[Dict[str, Any]], str],
        retry_config: Dict[str, Any],
    ) -> str:
        error_history = []
        enable_switch = retry_config.get("enable_provider_switch", True)
        attempts = retry_config.get("max_retries", 3)
        base_delay = retry_config.get("base_delay", 1.0)
        max_delay = retry_config.get("max_delay", 30.0)
        jitter = retry_config.get("jitter", True)

        provider_plan = [False]
        if enable_switch:
            provider_plan.append(True)

        for use_secondary in provider_plan:
            provider = self._get_provider(provider_type, use_secondary)
            if not provider:
                continue

            provider_name = provider.get("name") or provider.get("base_url") or "unknown"
            for attempt in range(1, attempts + 1):
                try:
                    logger.info(
                        "调用LLM | 任务=%s | Provider=%s | 尝试=%s/%s",
                        task_name,
                        provider_name,
                        attempt,
                        attempts,
                    )
                    return request_fn(provider)
                except Exception as exc:  # pragma: no cover - 调用失败时才进入
                    error_history.append(
                        {
                            "provider": provider_name,
                            "attempt": attempt,
                            "use_secondary": use_secondary,
                            "error": str(exc),
                        }
                    )
                    if attempt == attempts:
                        logger.warning("Provider %s 已用尽重试机会", provider_name)
                        break
                    delay = self._calculate_delay(attempt, base_delay, max_delay, jitter)
                    logger.warning(
                        "调用失败，将在 %.1fs 后重试 | 任务=%s | Provider=%s | 错误=%s",
                        delay,
                        task_name,
                        provider_name,
                        str(exc)[:200],
                    )
                    time.sleep(delay)

        last_error = error_history[-1]["error"] if error_history else "unknown error"
        raise LLMCallError(task_name, error_history, last_error)

    def _get_provider(self, provider_type: str, use_secondary: bool) -> Optional[Dict[str, Any]]:
        providers = self.settings.get("api_providers", {}).get(provider_type)
        if not providers:
            raise ConfigurationError(f"未配置 provider: {provider_type}")
        key = "secondary" if use_secondary else "primary"
        return providers.get(key)

    def _calculate_delay(self, attempt: int, base: float, max_delay: float, jitter: bool) -> float:
        delay = min(base * (2 ** (attempt - 1)), max_delay)
        if jitter:
            offset = delay * 0.1
            delay += random.uniform(-offset, offset)
        return max(delay, 0.1)
