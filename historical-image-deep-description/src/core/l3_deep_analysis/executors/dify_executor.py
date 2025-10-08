# -*- coding: utf-8 -*-
"""
Dify 执行器
- 复用 l3_context_interpretation 的增强客户端与超时恢复策略
- 查询粒度：逐题 question
- 输入映射：label = question；entity_type = subtopic_name；context_hint = "summary: ...\nreport_theme: ..."
"""
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from src.core.l3_context_interpretation.dify_enhanced_client import DifyEnhancedClient
from src.core.l3_context_interpretation.dify_timeout_recovery import RecoveryConfig
from src.core.l3_context_interpretation.dify_client import DifyResponse

def _resolve_env(ref: str) -> Optional[str]:
    """解析 env:KEY 形式"""
    if not ref:
        return None
    if ref.startswith("env:"):
        return os.getenv(ref.split(":", 1)[1])
    return ref

def _now_iso() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat()

def _build_context_hint(summary: Any, report_theme: Any) -> str:
    """将 summary、report_theme 规范化并拼装为上下文提示"""
    def norm(v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, (dict, list)):
            # 简单截断，避免过长
            text = str(v)
            return text[:1200]
        return str(v)
    return f"summary: {norm(summary)}\nreport_theme: {norm(report_theme)}"

def _is_success(status: str) -> bool:
    return status == "success" or status == "timeout_recovered"

def call_dify(question: str,
              subtopic_name: str,
              summary: Any,
              report_theme: Any,
              settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    调用 Dify（增强客户端 + 超时恢复），按单个问题检索

    Args:
        question: 本次检索的单个问题
        subtopic_name: 所属子主题名称
        summary: 整体摘要
        report_theme: 报告主题
        settings: 全局配置

    Returns:
        Dict[str, Any]: 统一返回 {"content": str, "meta": {...}}
                        其中 meta.status 可能为 success / not_found / not_relevant / error / timeout_recovered
    """
    conf = (settings.get("deep_analysis", {}) or {}).get("dify", {}) or {}
    api_key = _resolve_env(conf.get("api_key", "env:DIFY_DEEP_INTERPRETATION_KEY"))
    base_url = conf.get("base_url", "https://api.dify.ai/v1")
    rate_limit_ms = int(conf.get("rate_limit_ms", 1000) or 0)
    timeout_seconds = int(conf.get("timeout_seconds", 65))
    retry = (conf.get("retry_policy", {}) or {})
    max_retries = int(retry.get("max_retries", 3))
    delay_seconds = float(retry.get("delay_seconds", 2))
    backoff = float(retry.get("backoff_factor", 2.0))

    # 超时恢复配置
    trc = (conf.get("timeout_recovery", {}) or {})
    recovery_cfg = RecoveryConfig(
        enabled=bool(trc.get("enabled", True)),
        max_attempts=int(trc.get("max_attempts", 3)),
        delay_seconds=int(trc.get("delay_seconds", 10)),
        match_time_window=int(trc.get("match_time_window", 120)),
    )

    client = DifyEnhancedClient(
        api_key=api_key,
        base_url=base_url,
        rate_limit_ms=rate_limit_ms,
        timeout_seconds=timeout_seconds,
        recovery_config=recovery_cfg
    )

    # 组装上下文
    context_hint = _build_context_hint(summary, report_theme)

    # 指数退避重试
    attempt = 0
    last_response: Optional[DifyResponse] = None
    while True:
        attempt += 1
        resp: DifyResponse = client.query_knowledge_base(
            label=question,
            entity_type=subtopic_name or "",
            context_hint=context_hint,
            conversation_id="",
            user_id=None
        )
        last_response = resp

        if _is_success(resp.status) or resp.status in ("not_found", "not_relevant"):
            # 对于 not_found/not_relevant 不继续重试
            break

        if attempt > max_retries:
            break

        # 退避等待
        time.sleep(delay_seconds * (backoff ** (attempt - 1)))

    # 统一整理输出，并在成功类状态下识别“知识库没有检索到相关信息”并重分类为 not_found
    content = (last_response.content if last_response else "")
    status = (last_response.status if last_response else "error")
    error = (last_response.error if last_response else "unknown error")

    def _is_kb_not_found(text: str) -> bool:
        """
        判断 Dify 固定回答是否为“知识库没有检索到相关信息”
        说明：这是 Dify 侧固定话术，无需配置，命中则视为未命中知识库。
        """
        if not text:
            return False
        return "知识库没有检索到相关信息" in text or "未检索到相关信息" in text

    if _is_success(status) and _is_kb_not_found(content):
        status = "not_found"
        # 将固定话术放入 error 字段，便于统一落到 metadata 聚合
        error = "知识库未检索到相关信息"

    executed_at = _now_iso()
    meta = {
        "executed_at": executed_at,
        "task_type": "deep_rag_interpretation",
        "status": status,
        "dify_response_id": (last_response.response_id if last_response else None),
        "error": error
    }

    return {"content": content, "meta": meta}