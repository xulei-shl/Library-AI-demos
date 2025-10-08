# -*- coding: utf-8 -*-
"""
从实体 JSON 提取字段并构造用户提示词
- 基础字段：label、type、context_hint（仅保留一个代表值）
- 补充资源（按实体级严格键名）：
  wikipedia-description, wikidata-description, shl_data-description,
  related_events-label, related_events-description,
  l3_web_search-content, l3_enhanced_web_retrieval-content,
  l3_rag_entity_label_retrieval-content, l3_rag_enhanced_rag_retrieval-content
"""
import json
from typing import Dict, Any, List

def build_prompt_from_entity_json(entity_json_path: str) -> str:
    """
    读取实体 JSON，提取必要信息，生成用户提示文本（中文）

    Args:
        entity_json_path: 实体 JSON 文件路径

    Returns:
        str: 提示文本（供规划 LLM 使用）
    """
    with open(entity_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    entities = data.get("entities") or data.get("data") or []
    lines: List[str] = []
    context_hint_sample = None

    for idx, ent in enumerate(entities):
        label = ent.get("label")
        etype = ent.get("type")
        ch = ent.get("context_hint")
        if context_hint_sample is None and ch:
            context_hint_sample = ch

        lines.append(f"实体{idx+1}：label={label}，type={etype}")
        # 严格提取补充资源（若存在）
        def add(k: str, title: str):
            val = ent.get(k)
            if val:
                lines.append(f"{title}：{val}")

        add("wikipedia-description", "Wikipedia描述")
        add("wikidata-description", "Wikidata描述")
        add("shl_data-description", "SHL数据描述")
        add("related_events-label", "相关事件-标签")
        add("related_events-description", "相关事件-描述")
        add("l3_web_search-content", "L3 Web检索内容")
        add("l3_enhanced_web_retrieval-content", "L3 增强Web检索内容")
        add("l3_rag_entity_label_retrieval-content", "L3 RAG实体标签检索内容")
        add("l3_rag_enhanced_rag_retrieval-content", "L3 增强RAG检索内容")

    if context_hint_sample:
        lines.insert(0, f"语境线索（context_hint）：{context_hint_sample}")

    prompt = "\n".join(lines) if lines else "未找到实体信息。"
    return prompt