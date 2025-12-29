#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SiliconFlow Reranker 调用封装。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Sequence

import requests

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RerankResult:
    """单条重排序结果。"""

    index: int
    score: float


class RerankerClient:
    """封装 SiliconFlow rerank API 的轻量客户端。"""

    def __init__(self, config: Dict):
        self.enabled = config.get("enabled", False)
        self.model = config.get("model")
        self.base_url = (config.get("base_url") or "").rstrip("/")
        self.timeout = config.get("timeout", 15)
        self.default_top_n = config.get("top_n", 30)
        self.api_key = self._resolve_env(config.get("api_key", ""))
        self.session = requests.Session()

    def rerank(self, query: str, documents: Sequence[str], top_n: int | None = None) -> List[RerankResult]:
        """调用 rerank 接口并返回排序结果。"""

        if not self.enabled:
            logger.debug("Reranker 未启用，直接返回空结果。")
            return []
        if not documents:
            return []
        limit = min(top_n or self.default_top_n, len(documents))
        url = f"{self.base_url}/rerank"
        payload = {
            "model": self.model,
            "query": query,
            "documents": list(documents),
            "top_n": limit,
        }
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            response = self.session.post(url, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            logger.error("Rerank 请求失败: %s", exc)
            return []
        except ValueError as exc:  # JSON 解析失败
            logger.error("Rerank 响应解析失败: %s", exc)
            return []
        items = _extract_items(data)
        results: List[RerankResult] = []
        for item in items:
            index = item.get("index")
            if index is None and isinstance(item.get("document"), dict):
                index = item["document"].get("index")
            if index is None:
                continue
            score = float(item.get("score") or item.get("relevance_score") or 0.0)
            results.append(RerankResult(index=int(index), score=score))
        results.sort(key=lambda entry: entry.score, reverse=True)
        return results

    def rerank_candidates(self, query: str, candidates: List[Dict], text_fields: Sequence[str] | None = None) -> List[Dict]:
        """对候选书籍执行 rerank，并返回更新后的列表。"""

        if not self.enabled or not candidates:
            return candidates
        documents = [self._build_document_text(item, text_fields) for item in candidates]
        rerank_results = self.rerank(query, documents)
        score_map = {item.index: item.score for item in rerank_results}
        for idx, candidate in enumerate(candidates):
            candidate["reranker_score"] = score_map.get(idx)
        candidates.sort(
            key=lambda item: (
                item.get("reranker_score", 0.0),
                item.get("fused_score", item.get("similarity_score", 0.0)),
            ),
            reverse=True,
        )
        return candidates

    @staticmethod
    def _build_document_text(candidate: Dict, text_fields: Sequence[str] | None) -> str:
        fields = text_fields or ("title", "summary")
        parts = [str(candidate.get(field, "")) for field in fields if candidate.get(field)]
        return "\n".join(parts) or str(candidate)

    @staticmethod
    def _resolve_env(value: str) -> str:
        if value and value.startswith("env:"):
            env_var = value[4:]
            env_value = os.getenv(env_var, "")
            if not env_value:
                logger.warning("环境变量 %s 未设置，Reranker 将无法调用", env_var)
            return env_value
        return value


def _extract_items(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    if isinstance(data.get("data"), list):
        return data["data"]
    if isinstance(data.get("results"), list):
        return data["results"]
    return []
