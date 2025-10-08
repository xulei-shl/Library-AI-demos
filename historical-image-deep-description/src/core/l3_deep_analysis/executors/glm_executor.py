# -*- coding: utf-8 -*-
"""
Zhipu GLM 执行器
- 对每个子问题进行检索，写入 content 与独立 meta
- 使用 Zhipu 助手模型 glm-4-assistant，强制 stream=True，API Key 从环境变量 ZHIPUAI_API_KEY 读取
"""
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from src.utils.logger import get_logger
import time

logger = get_logger(__name__)

def call_glm(query: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    调用 Zhipu GLM Assistant API（流式聚合 + 指数退避重试）

    Args:
        query: 检索查询文本
        settings: 配置字典，读取 settings.deep_analysis.glm.retry_policy 等

    Returns:
        Dict[str, Any]: { "content": "...", "meta": {...} }
    Raises:
        RuntimeError: 重试后仍失败
    """
    # 立即迁移：仅读取 deep_analysis.glm 配置
    conf = (settings.get("deep_analysis", {}).get("glm", {}) or {})
    # 若配置关闭，则直接跳过，不调用外部API
    enabled = bool(conf.get("enabled", True))
    if not enabled:
        now = datetime.now(timezone(timedelta(hours=8))).isoformat()
        logger.info('phase=deep_glm action=skip_disabled')
        return {
            "content": None,
            "meta": {
                "status": "skipped",
                "executed_at": now,
                "task_type": "deep_glm",
                "search_query": query,
                "llm_model": None,
                "error": None,
                "reason": "disabled"
            }
        }
    timeout = int(conf.get("timeout_seconds", 65))
    retry = (conf.get("retry_policy", {}) or {})
    max_retries = int(retry.get("max_retries", 3))
    delay_seconds = float(retry.get("delay_seconds", 2))
    backoff = float(retry.get("backoff_factor", 2.0))

    api_key = os.getenv("ZHIPUAI_API_KEY")
    if not api_key:
        raise RuntimeError("缺少环境变量 ZHIPUAI_API_KEY")

    # 惰性导入，避免环境未安装时报错时污染模块加载
    try:
        from zai import ZhipuAiClient  # type: ignore
    except Exception as e:
        raise RuntimeError("未安装 'zai' SDK 或版本不兼容，请安装后重试：pip install zai") from e

    assistant_id = (conf.get("assistant_id") or os.getenv("ZHIPU_ASSISTANT_ID") or "659e54b1b8006379b4b2abd6")

    last_err: Exception | None = None
    attempt = 0
    t0 = time.perf_counter()
    # 日志：开始执行
    qp = (query or "")[:80].replace("", " ")
    logger.info(f'phase=deep_glm action=exec_start model=glm-4-assistant timeout={timeout}s retry_max={max_retries} retry_delay={delay_seconds}s backoff={backoff} question_preview="{qp}"')
    while attempt <= max_retries:
        try:
            client = ZhipuAiClient(api_key=api_key)
            # 固定参数：glm-4-assistant + stream=True
            gen = client.assistant.conversation(
                assistant_id=assistant_id,
                conversation_id=None,
                model="glm-4-assistant",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": query
                            }
                        ]
                    }
                ],
                stream=True,
                attachments=None,
                metadata=None,
                timeout=timeout
            )

            # 流式聚合：仅收集助手文本增量，忽略工具/浏览器等事件
            content_chunks: list[str] = []
            for resp in gen:
                try:
                    # 仅在解析到“文本”时追加，严格过滤非文本事件
                    delta_text = None

                    # 优先解析 choices[0].delta
                    chs = getattr(resp, "choices", None)
                    if isinstance(chs, list) and chs:
                        delta = getattr(chs[0], "delta", None)
                        # 过滤工具/浏览器等非文本类型
                        dtype = getattr(delta, "type", None)
                        if dtype and str(dtype) in ("tool_calls", "tool", "web_browser", "tool_result"):
                            continue
                        if delta is not None and hasattr(delta, "content"):
                            c = getattr(delta, "content")
                            # c 可能是 TextContentBlock 或 str
                            if hasattr(c, "content"):
                                delta_text = getattr(c, "content", None)
                            elif isinstance(c, str):
                                delta_text = c

                    # 次选：resp.delta.content
                    if not delta_text and hasattr(resp, "delta"):
                        d = getattr(resp, "delta")
                        dtype = getattr(d, "type", None)
                        if dtype and str(dtype) in ("tool_calls", "tool", "web_browser", "tool_result"):
                            continue
                        if hasattr(d, "content"):
                            dc = getattr(d, "content")
                            if isinstance(dc, str):
                                delta_text = dc
                            elif hasattr(dc, "content"):
                                delta_text = getattr(dc, "content", None)

                    # 仅当解析到明确的文本增量时追加
                    if isinstance(delta_text, str) and delta_text:
                        content_chunks.append(delta_text)
                except Exception:
                    # 出错时不追加任意对象字符串，忽略本片段
                    continue

            content = "".join(content_chunks).strip()
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            if not content:
                # 无内容也视为 not_found
                now = datetime.now(timezone(timedelta(hours=8))).isoformat()
                logger.info(f'phase=deep_glm action=exec_not_found elapsed_ms={elapsed_ms}')
                return {
                    "content": None,
                    "meta": {
                        "status": "not_found",
                        "executed_at": now,
                        "task_type": "deep_glm",
                        "search_query": query,
                        "llm_model": "glm-4-assistant",
                        "error": None
                    }
                }

            now = datetime.now(timezone(timedelta(hours=8))).isoformat()
            meta = {
                "status": "success",
                "executed_at": now,
                "task_type": "deep_glm",
                "search_query": query,
                "llm_model": "glm-4-assistant",
                "error": None
            }
            logger.info(f'phase=deep_glm action=exec_success elapsed_ms={elapsed_ms} content_len={len(content)}')
            return {"content": content, "meta": meta}
        except Exception as e:
            last_err = e
            attempt += 1
            if attempt > max_retries:
                break
            # 指数退避
            next_delay = delay_seconds * (backoff ** (attempt - 1))
            logger.warning(f'phase=deep_glm action=retry attempt={attempt} next_delay_s={next_delay:.2f} error={str(e)!r}')
            import time as _t
            _t.sleep(next_delay)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    logger.error(f'phase=deep_glm action=exec_failed attempts={attempt} elapsed_ms={elapsed_ms} error={str(last_err)!r}')
    raise RuntimeError(f"GLM request failed after retries: {last_err}")