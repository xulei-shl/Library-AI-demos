import base64
import json
import os
import time
from typing import Any, Dict, Optional, Tuple, List

import yaml
from openai import OpenAI

from .logger import get_logger

logger = get_logger(__name__)


def _resolve_env(value: str) -> str:
    if isinstance(value, str) and value.startswith("env:"):
        var = value.split(":", 1)[1]
        v = os.getenv(var, "")
        if not v:
            logger.warning(f"missing_env_key key={var}")
        return v
    return value


def load_settings(path: str = "config/settings.yaml") -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _choose_provider(settings: Dict[str, Any], provider_type: str, use_secondary: bool) -> Tuple[str, str, str]:
    """
    选择API提供商配置，返回base_url、api_key和model。
    
    Args:
        settings: 全局配置
        provider_type: 提供商类型（如"text", "vision"）
        use_secondary: 是否使用备用提供商
    
    Returns:
        (base_url, api_key, model) 元组
    """
    prov = settings["api_providers"][provider_type]["secondary" if use_secondary else "primary"]
    base_url = prov["base_url"].rstrip("/") + "/"
    api_key = _resolve_env(prov["api_key"])
    model = prov["model"]
    return base_url, api_key, model


def _sleep_delay(seconds: int) -> None:
    try:
        time.sleep(seconds)
    except Exception:
        pass


def _apply_rate_limit(ms: int) -> None:
    if ms and ms > 0:
        time.sleep(ms / 1000.0)


def _truncate(s: str, max_len: int = 800) -> str:
    if s is None:
        return ""
    return s if len(s) <= max_len else s[:max_len] + "...(truncated)"


def _extract_user_preview(messages: List[Dict[str, Any]]) -> str:
    """
    提取用户提示词的文本预览。
    - 若 user.content 为字符串，直接返回其文本。
    - 若为列表（视觉消息），提取其中 type=="text" 的片段并拼接。
    - 若不存在文本，返回空字符串。
    """
    try:
        for m in messages or []:
            if m.get("role") != "user":
                continue
            content = m.get("content")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                texts: List[str] = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        t = item.get("text") or ""
                        if t:
                            texts.append(str(t))
                return (" ".join(texts)).strip()
            # 其他类型不处理
        return ""
    except Exception:
        return ""

def _extract_system_text(messages: List[Dict[str, Any]]) -> str:
    """
    提取系统提示词（可能存在多个 system 消息，按顺序拼接为一个文本）。
    """
    try:
        parts: List[str] = []
        for m in messages or []:
            if m.get("role") != "system":
                continue
            content = m.get("content")
            if isinstance(content, str):
                parts.append(content.strip())
            elif isinstance(content, list):
                # 兼容列表形式，取其中的 text 片段
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        t = item.get("text") or ""
                        if t:
                            parts.append(str(t))
        return "".join([p for p in parts if p]).strip()
    except Exception:
        return ""

def _extract_user_text(messages: List[Dict[str, Any]]) -> str:
    """
    提取用户提示词的完整文本（聚合多个 text 片段）。
    """
    try:
        parts: List[str] = []
        for m in messages or []:
            if m.get("role") != "user":
                continue
            content = m.get("content")
            if isinstance(content, str):
                parts.append(content.strip())
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        t = item.get("text") or ""
                        if t:
                            parts.append(str(t))
        return "".join([p for p in parts if p]).strip()
    except Exception:
        return ""


def _as_chat_payload(model: str, messages: List[Dict[str, Any]], temperature: float, top_p: float) -> Dict[str, Any]:
    return {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
    }


def _build_openai_client(base_url: str, api_key: str, timeout: int = 90, max_retries: int = 0) -> OpenAI:
    """
    创建 OpenAI SDK 客户端。
    说明：
      - base_url 需以 / 结尾（上游已处理）
      - 出于与外层自定义重试/主备切换配合，client 层 max_retries 默认为 0
      - timeout: 请求超时时间（秒）
    """
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
    )


def invoke_model(
    task_name: str,
    messages: list,
    settings: Dict[str, Any],
    *,
    provider_type: Optional[str] = None,
    model: Optional[str] = None,
    endpoint: Optional[str] = None,  # 与 SDK 模式无关，保留参数兼容
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    request_timeout_seconds: Optional[int] = None,
) -> str:
    """
    调用 OpenAI 兼容 chat/completions（通过 OpenAI SDK），带主备切换与重试，并输出审计日志（无敏感内容）。
    返回：字符串形式的模型输出（content 聚合）。
    """
    t0 = time.time()
    task_cfg = settings["tasks"][task_name]
    # 确保provider_type不为None
    provider_type = provider_type or task_cfg["provider_type"]
    if not provider_type:
        raise ValueError(f"task={task_name} missing provider_type")
    
    # 注意：模型名现在从 provider 配置中获取，不再从 task 配置中获取
    # endpoint 在 SDK 模式下不使用，保留读取以兼容现有配置结构
    _ = endpoint or task_cfg.get("endpoint", "/chat/completions")

    # 使用配置参数（不强行改默认值，尊重 settings.yaml）
    temperature = task_cfg.get("temperature", 0.7) if temperature is None else temperature
    top_p = task_cfg.get("top_p", 1.0) if top_p is None else top_p
    # 确保temperature和top_p不为None
    if temperature is None:
        temperature = 0.7
    if top_p is None:
        top_p = 1.0

    rate_limit_ms = settings.get("rate_limit_ms", 0)
    retry_policy = settings.get("retry_policy", {"max_retries": 3, "delay_seconds": 5})
    max_retries = int(retry_policy.get("max_retries", 3))
    delay_seconds = int(retry_policy.get("delay_seconds", 5))

    last_err: Optional[str] = None

    for use_secondary in (False, True):
        base_url, api_key, actual_model = _choose_provider(settings, provider_type, use_secondary)

        # 读取 provider 级的 timeout_seconds（支持 primary/secondary 独立配置）；调用层传入则优先
        provider_cfg = settings.get("api_providers", {}).get(provider_type, {}).get("secondary" if use_secondary else "primary", {}) or {}
        provider_timeout = int(provider_cfg.get("timeout_seconds", 60) or 60)
        timeout_seconds = int(request_timeout_seconds) if request_timeout_seconds is not None else provider_timeout

        headers_hint = (
            f"base_url={base_url} provider_type={provider_type} use_secondary={use_secondary} "
            f"model={actual_model} timeout={timeout_seconds}s"
        )

        # 使用实际模型名构建请求载荷
        payload = _as_chat_payload(actual_model, messages, float(temperature), float(top_p))
        payload_str = _truncate(json.dumps(payload, ensure_ascii=False))

        # 构建 SDK 客户端（内部 max_retries=0，外层负责重试与切换）
        client = _build_openai_client(base_url=base_url, api_key=api_key, timeout=timeout_seconds, max_retries=0)

        # 读取日志截断配置（提供默认值，避免配置缺失）
        log_cfg = settings.get("logging", {}) or {}
        sys_max = int(log_cfg.get("system_preview_max_len", 1000))
        usr_max = int(log_cfg.get("user_preview_max_len", 300))
        rsp_max = int(log_cfg.get("response_preview_max_len", 2000))

        # 提取 system/user 文本与预览
        system_full = _extract_system_text(messages)
        user_full = _extract_user_text(messages)
        system_preview = _truncate(system_full, sys_max)
        user_preview = _truncate(user_full, usr_max)

        logger.info(
            f"llm_call_start task={task_name} {headers_hint} "
            f"system_prompt_len={len(system_full)} system_prompt_preview={system_preview} "
            f"user_prompt_len={len(user_full)} user_prompt_preview={user_preview}"
        )

        for attempt in range(1, max_retries + 1):
            _apply_rate_limit(rate_limit_ms)
            try:
                r0 = time.time()
                completion = client.chat.completions.create(
                    model=actual_model,
                    messages=messages,
                    temperature=temperature,
                    top_p=top_p,
                )
                duration_ms = int((time.time() - r0) * 1000)

                # 审计日志（截断）
                user_preview_max_len = int(settings.get("logging", {}).get("user_preview_max_len", 300))
                user_prompt_preview = _truncate(_extract_user_preview(messages), user_preview_max_len)
                logger.info(
                    f"audit request task={task_name} {headers_hint} attempt={attempt}/{max_retries} "
                    f"duration_ms={duration_ms} payload={payload_str} user_prompt_preview={user_prompt_preview}"
                )

                # 解析标准 OpenAI 返回
                choices = getattr(completion, "choices", []) or []
                contents: List[str] = []
                for c in choices:
                    msg = getattr(c, "message", None) or {}
                    content = getattr(msg, "content", "") if hasattr(msg, "content") else msg.get("content", "")
                    if isinstance(content, list):
                        # 兜底：某些实现可能返回分片列表
                        joined = "".join([x.get("text", "") if isinstance(x, dict) else str(x) for x in content])
                        contents.append(joined)
                    else:
                        contents.append(content or "")
                result = "\n".join([x for x in contents if x])

                # 响应日志（含预览与长度），避免过长
                resp_preview = _truncate(result, rsp_max)
                logger.info(
                    f"llm_call_success task={task_name} {headers_hint} "
                    f"duration_ms={duration_ms} response_len={len(result)} response_preview={resp_preview}"
                )

                # 保留原有精简审计（兼容老日志检索）
                logger.info(
                    f"audit response task={task_name} {headers_hint} ok=true len={len(result)}"
                )
                return result
            except Exception as e:
                last_err = str(e)
                logger.warning(
                    f"invoke_exception task={task_name} attempt={attempt}/{max_retries} {headers_hint} err={_truncate(last_err)}"
                )
            if attempt < max_retries:
                _sleep_delay(delay_seconds)

        # 切换到备用提供商继续
        logger.warning(
            f"switch_provider task={task_name} reason=primary_failed last_err={_truncate(last_err or '')}"
        )

    elapsed_ms = int((time.time() - t0) * 1000)
    logger.error(f"invoke_failed task={task_name} elapsed_ms={elapsed_ms} last_err={_truncate(last_err or '')}")
    raise RuntimeError(f"invoke_model failed for task={task_name}: {last_err}")


def image_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")