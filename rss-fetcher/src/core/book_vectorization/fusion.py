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
    """在相同 book_id 下保留时间更新的记录。"""

    # 尝试比较 embedding_date
    current_date = (current.get('embedding_date') or '').strip()
    candidate_date = (candidate.get('embedding_date') or '').strip()
    
    if current_date and candidate_date:
        # 如果两个记录都有时间字段，比较时间
        if candidate_date > current_date:
            return dict(candidate)
        return current
    
    # 如果只有一个记录有时间字段，有时间字段的记录更新
    if candidate_date and not current_date:
        return dict(candidate)
    
    if not candidate_date and current_date:
        return current
    
    # 如果都没有时间字段，比较 book_id
    current_id = int(current.get('id', 0))
    candidate_id = int(candidate.get('id', 0))
    
    if candidate_id > current_id:
        return dict(candidate)
    return current


def merge_exact_matches(
    vector_results: List[Dict],
    exact_matches: List[Dict],
    exact_match_weight: float = 1.1,
) -> List[Dict]:
    """将精确匹配结果与向量检索结果融合，双重去重并调整排序。"""
    if not exact_matches:
        return vector_results

    # 第一步：以 book_id 为键聚合
    book_merged: Dict[str, Dict] = {}
    for item in vector_results:
        book_id = _resolve_book_id(item)
        if book_id:
            book_merged[book_id] = item

    for item in exact_matches:
        book_id = _resolve_book_id(item)
        if not book_id:
            continue
        
        # 为精确匹配的条目构造基础结果
        exact_item = {
            "book_id": int(book_id),
            "id": int(book_id),
            "title": item.get("douban_title", "未知"),
            "author": item.get("douban_author", "未知"),
            "rating": item.get("douban_rating"),
            "summary": item.get("douban_summary"),
            "call_no": item.get("call_no"),
            "similarity_score": None,
            "fused_score": None,
            "match_count": 0,
            "query_types": [],
            "exact_match_score": item.get("exact_match_score"),
            "match_source": item.get("match_source"),
            "embedding_date": item.get("embedding_date", ""),  # 添加时间字段
        }
        
        # 如果该 book_id 已存在，需要判断是否应该替换
        if book_id in book_merged:
            existing = book_merged[book_id]
            if _is_record_newer(exact_item, existing):
                book_merged[book_id] = exact_item
        else:
            book_merged[book_id] = exact_item

    # 第二步：基于 call_no 去重，处理数据库中的重复脏数据
    call_no_merged: Dict[str, Dict] = {}
    for item in book_merged.values():
        call_no = str(item.get('call_no') or '').strip()
        if not call_no:
            # 如果没有索书号，直接保留
            call_no_merged[f"no_call_no_{item.get('book_id')}"] = item
            continue
        
        # 判断是否应该保留当前记录
        should_keep = False
        if call_no not in call_no_merged:
            should_keep = True
        else:
            existing = call_no_merged[call_no]
            should_keep = _is_record_newer(item, existing)
        
        if should_keep:
            call_no_merged[call_no] = item

    # 重算最终得分，并确保精确匹配不被压过
    final: List[Dict] = []
    for item in call_no_merged.values():
        exact_score = float(item.get("exact_match_score", 0))
        current_final = float(item.get("fused_score") or 0)
        if exact_score > 0:
            item["final_score"] = max(current_final, exact_match_weight * exact_score)
        else:
            item["final_score"] = current_final
        final.append(item)

    final.sort(key=lambda x: x["final_score"], reverse=True)
    return final


def _is_record_newer(current: Dict, existing: Dict) -> bool:
    """
    判断当前记录是否比已有记录更新
    
    优先级规则：
    1. 如果有 embedding_date 时间字段，比较时间
    2. 如果没有时间字段，比较 book_id
    
    Args:
        current: 当前记录
        existing: 已有记录
        
    Returns:
        True 如果当前记录更新，False 否则
    """
    # 尝试比较 embedding_date
    current_date = (current.get('embedding_date') or '').strip()
    existing_date = (existing.get('embedding_date') or '').strip()
    
    if current_date and existing_date:
        # 如果两个记录都有时间字段，比较时间
        return current_date > existing_date
    
    # 如果只有一个记录有时间字段，有时间字段的记录更新
    if current_date and not existing_date:
        return True
    
    if not current_date and existing_date:
        return False
    
    # 如果都没有时间字段，比较 book_id
    current_id = int(current.get('id', 0))
    existing_id = int(existing.get('id', 0))
    
    return current_id > existing_id

