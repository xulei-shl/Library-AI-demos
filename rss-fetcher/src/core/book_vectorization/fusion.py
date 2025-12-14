#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""多子查询结果融合工具。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence, Tuple

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FusionWeights:
    """控制融合得分的权重。"""

    max_similarity: float = 0.6
    avg_similarity: float = 0.2
    match_count: float = 0.2


@dataclass
class FusionConfig:
    """融合阶段的行为配置。"""

    weights: FusionWeights = field(default_factory=FusionWeights)
    final_top_k: int | None = 15


def build_fusion_config(config_dict: Dict | None) -> FusionConfig:
    """根据配置字典构建 `FusionConfig`。"""

    if not config_dict:
        return FusionConfig()

    weights_dict = (config_dict or {}).get("weights", {})
    weights = FusionWeights(
        max_similarity=weights_dict.get("max_similarity", 0.6),
        avg_similarity=weights_dict.get("avg_similarity", 0.2),
        match_count=weights_dict.get("match_count", 0.2),
    )
    return FusionConfig(
        weights=weights,
        final_top_k=config_dict.get("final_top_k"),
    )


def fuse_query_results(
    query_results: Sequence[Tuple[str, List[Dict]]],
    fusion_config: FusionConfig,
) -> List[Dict]:
    """将多轮检索结果合并为单一候选列表。"""

    if not query_results:
        return []

    aggregated: Dict[str, Dict] = {}
    for group_name, results in query_results:
        for item in results:
            book_id = _resolve_book_id(item)
            if not book_id:
                logger.debug("跳过缺少 book_id 的结果: %s", item)
                continue
            entry = aggregated.setdefault(book_id, {
                "scores": [],
                "match_count": 0,
                "base": dict(item),
                "query_types": set(),
            })
            score = float(item.get("similarity_score") or 0.0)
            entry["scores"].append(score)
            entry["match_count"] += 1
            entry["query_types"].add(group_name)
            entry["base"] = _prefer_higher_similarity(entry["base"], item)

    fused: List[Dict] = []
    weights = fusion_config.weights
    for entry in aggregated.values():
        scores = entry["scores"]
        if not scores:
            continue
        max_score = max(scores)
        avg_score = sum(scores) / len(scores)
        fused_score = (
            weights.max_similarity * max_score
            + weights.avg_similarity * avg_score
            + weights.match_count * entry["match_count"]
        )
        record = dict(entry["base"])
        record["similarity_score"] = max_score
        record["fused_score"] = fused_score
        record["match_count"] = entry["match_count"]
        record["query_types"] = sorted(entry["query_types"])
        fused.append(record)

    fused.sort(key=lambda item: item.get("fused_score", 0.0), reverse=True)
    if fusion_config.final_top_k:
        fused = fused[:fusion_config.final_top_k]
    return fused


def _resolve_book_id(item: Dict) -> str:
    book_id = item.get("book_id") or item.get("id")
    return str(book_id) if book_id is not None else ""


def _prefer_higher_similarity(current: Dict, candidate: Dict) -> Dict:
    """在相同 book_id 下保留相似度更高的记录。"""

    current_score = float(current.get("similarity_score") or 0.0)
    candidate_score = float(candidate.get("similarity_score") or 0.0)
    if candidate_score > current_score:
        return dict(candidate)
    return current
