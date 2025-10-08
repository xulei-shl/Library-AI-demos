# -*- coding: utf-8 -*-
"""
Jina DeepSearch 执行器
- 对每个子问题进行检索，写入 content 与独立 meta
"""
import os
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

def call_jina(query: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    调用 Jina DeepSearch API（带指数退避重试）

    Args:
        query: 检索查询文本
        settings: 配置字典

    Returns:
        Dict[str, Any]: { "content": "...", "meta": {...} } 或抛出异常
    """
    conf = settings.get("deep_analysis", {}).get("jina", {}) or {}
    base_url = conf.get("base_url", "https://deepsearch.jina.ai/v1")
    endpoint = conf.get("endpoint", "/chat/completions")
    url = f"{base_url}{endpoint}"
    api_key_ref = conf.get("api_key", "env:JINA_DEEPSEARCH_KEY")
    if api_key_ref.startswith("env:"):
        env_key = api_key_ref.split(":", 1)[1]
        api_key = os.getenv(env_key)
    else:
        api_key = api_key_ref

    timeout = int(conf.get("timeout_seconds", 65))
    retry = (conf.get("retry_policy", {}) or {})
    max_retries = int(retry.get("max_retries", 3))
    delay_seconds = float(retry.get("delay_seconds", 2))
    backoff = float(retry.get("backoff_factor", 2.0))

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}" if api_key else ""
    }
    data = {
        "model": "jina-deepsearch-v1",
        "messages": [
            {"role": "user", "content": query}
        ],
        "stream": False
    }

    last_err = None
    attempt = 0
    while attempt <= max_retries:
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=timeout)
            resp.raise_for_status()
            payload = resp.json()
            # 尝试解析 OpenAI 兼容响应
            content = None
            try:
                choices = payload.get("choices") if isinstance(payload, dict) else None
                if isinstance(choices, list) and choices:
                    msg = choices[0].get("message", {})
                    content = msg.get("content")
            except Exception:
                content = None
            if not content:
                # 回退：原样序列化
                content = str(payload)
            now = datetime.now(timezone(timedelta(hours=8))).isoformat()
            meta = {
                "status": "success",
                "executed_at": now,
                "task_type": "web_search",
                "search_query": query,
                "llm_model": "jina-deepsearch-v1",
                "error": None
            }
            return {"content": content, "meta": meta}
        except Exception as e:
            last_err = e
            attempt += 1
            if attempt > max_retries:
                break
            # 指数退避
            import time as _t
            _t.sleep(delay_seconds * (backoff ** (attempt - 1)))

    # 重试后仍失败，抛出异常交由上层写入 metadata.jina
    raise RuntimeError(f"Jina request failed after retries: {last_err}")